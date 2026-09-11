import sys
from pathlib import Path
from datetime import date

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.energy_data_engine.forecasting.baseline_forecaster import SeasonalNaiveForecaster
from src.energy_data_engine.analytics.forecast_errors import (
    compute_all_metrics,
    forecast_accuracy_pct,
    find_worst_error_periods,
    METRIC_GLOSSARY,
)


def test_forecast_accuracy_step():
    print("\n" + "=" * 50)
    print("      FORECAST ACCURACY FEATURE TEST HARNESS       ")
    print("=" * 50 + "\n")

    # 1. Build 4 weeks of synthetic hourly "actual load" history with a clean
    #    day-of-week x hour-of-day seasonal pattern (so the baseline forecaster
    #    has something predictable to learn).
    hist_start = pd.Timestamp("2026-08-01", tz="UTC")
    hist_end = pd.Timestamp("2026-08-29", tz="UTC")  # 4 weeks, ends the day before target
    timestamps = pd.date_range(start=hist_start, end=hist_end, freq="1h", inclusive="left")

    def synthetic_load(ts: pd.Timestamp) -> float:
        base = 50000.0
        weekday_effect = -5000.0 if ts.weekday() >= 5 else 0.0  # lower on weekends
        hourly = 8000 * np.sin(2 * np.pi * (ts.hour - 6) / 24)
        return base + weekday_effect + hourly  # noise-free on purpose, for a clean assertion

    history_df = pd.DataFrame({
        "timestamp": timestamps,
        "load_mw": [synthetic_load(ts) for ts in timestamps],
    })

    # 2. Forecast a target date (the day right after the history window) and
    #    confirm the seasonal-naive model reconstructs the known pattern closely.
    target_date = date(2026, 8, 29)
    forecaster = SeasonalNaiveForecaster(lookback_weeks=4)
    forecast_df = forecaster.forecast(history_df, target_date, zone_timezone="Europe/Berlin", value_col="load_mw")

    assert len(forecast_df) == 24, f"Expected 24 hourly rows, got {len(forecast_df)}"
    assert forecast_df["own_forecast"].notna().all(), "Forecast produced NaNs despite sufficient history"

    actual_df = pd.DataFrame({
        "timestamp": pd.date_range(pd.Timestamp(target_date, tz="Europe/Berlin").tz_convert("UTC"), periods=24, freq="1h"),
    })
    actual_df["actual_mw"] = [synthetic_load(ts) for ts in actual_df["timestamp"]]

    merged = forecast_df.merge(actual_df, on="timestamp", how="inner")
    assert len(merged) == 24, "Forecast and actual timestamps did not align"

    max_abs_error = (merged["own_forecast"] - merged["actual_mw"]).abs().max()
    print(f"[+] Max abs error vs noise-free synthetic pattern: {max_abs_error:.2f} MW")
    assert max_abs_error < 1.0, "Seasonal-naive forecast should near-perfectly reconstruct a noise-free seasonal pattern"

    # 3. No-leakage check: history on/after the target date must never influence the forecast.
    poisoned_history = history_df.copy()
    future_row = pd.DataFrame({
        "timestamp": [pd.Timestamp(target_date, tz="Europe/Berlin").tz_convert("UTC")],
        "load_mw": [999999.0],
    })
    poisoned_history = pd.concat([poisoned_history, future_row], ignore_index=True)
    forecast_with_poison = forecaster.forecast(poisoned_history, target_date, zone_timezone="Europe/Berlin", value_col="load_mw")
    pd.testing.assert_frame_equal(forecast_df, forecast_with_poison)
    print("[+] No-leakage check passed: data on/after target date is ignored")

    # 4. Empty-history fallback: must return NaNs, not crash.
    empty_forecast = forecaster.forecast(pd.DataFrame(columns=["timestamp", "load_mw"]), target_date, "Europe/Berlin", value_col="load_mw")
    assert empty_forecast["own_forecast"].isna().all()
    print("[+] Empty-history fallback returns NaNs as expected")

    # 5. Reusability check: the same forecaster works for a price-like series (different
    #    value_col, can go negative) -- this is what the new Price Forecast section relies on.
    price_history_df = pd.DataFrame({
        "timestamp": timestamps,
        "price_eur_mwh": [20 * np.sin(2 * np.pi * (ts.hour - 6) / 24) for ts in timestamps],
    })
    price_forecast_df = forecaster.forecast(
        price_history_df, target_date, zone_timezone="Europe/Berlin", value_col="price_eur_mwh"
    )
    assert len(price_forecast_df) == 24 and price_forecast_df["own_forecast"].notna().all()
    print("[+] Forecaster reused successfully for a price-shaped (negative-capable) series")

    # 5b. Regression test: ENTSO-E publishes load (and increasingly price) at 15-minute
    #     resolution for many zones, not hourly. The forecaster must detect that and
    #     produce a matching 96-point grid, not silently fall back to 24 hourly points
    #     (which would leave 75% of a 15-min actual series with nothing to compare against).
    quarter_hourly_ts = pd.date_range(start=hist_start, end=hist_end, freq="15min", inclusive="left")

    def synthetic_load_15min(ts: pd.Timestamp) -> float:
        base = 50000.0
        weekday_effect = -5000.0 if ts.weekday() >= 5 else 0.0
        hourly = 8000 * np.sin(2 * np.pi * (ts.hour + ts.minute / 60 - 6) / 24)
        return base + weekday_effect + hourly

    quarter_hourly_history = pd.DataFrame({
        "timestamp": quarter_hourly_ts,
        "load_mw": [synthetic_load_15min(ts) for ts in quarter_hourly_ts],
    })
    quarter_hourly_forecast = forecaster.forecast(
        quarter_hourly_history, target_date, zone_timezone="Europe/Berlin", value_col="load_mw"
    )
    assert len(quarter_hourly_forecast) == 96, (
        f"Expected 96 quarter-hourly rows for 15-min-resolution history, got {len(quarter_hourly_forecast)}"
    )
    assert quarter_hourly_forecast["own_forecast"].notna().all()
    # Every 15-minute point should merge cleanly against 96 real actual points -- the
    # exact bug this test guards against is a 24-point forecast leaving 72 of them as NaN.
    quarter_hourly_actual = pd.DataFrame({
        "timestamp": pd.date_range(
            pd.Timestamp(target_date, tz="Europe/Berlin").tz_convert("UTC"), periods=96, freq="15min"
        ),
    })
    quarter_hourly_actual["actual_mw"] = [synthetic_load_15min(ts) for ts in quarter_hourly_actual["timestamp"]]
    merged_15min = quarter_hourly_forecast.merge(quarter_hourly_actual, on="timestamp", how="inner")
    assert len(merged_15min) == 96, "15-minute forecast and actual timestamps did not fully align"
    assert (merged_15min["own_forecast"] - merged_15min["actual_mw"]).abs().max() < 1.0
    print("[+] 15-minute-resolution history correctly produces a matching 96-point forecast (no NaN gaps)")

    # 6. Error metrics sanity checks against a hand-computed example.
    actual = pd.Series([100.0, 200.0, 0.0, 400.0])
    forecast = pd.Series([110.0, 190.0, 5.0, 380.0])
    metrics = compute_all_metrics(actual, forecast, method="wape")

    # MAE = mean(|100-110|, |200-190|, |0-5|, |400-380|) = mean(10,10,5,20) = 11.25
    assert abs(metrics["mae"] - 11.25) < 1e-6, metrics
    # MSE = mean(100, 100, 25, 400) = 156.25 ; RMSE = sqrt(156.25) = 12.5
    assert abs(metrics["mse"] - 156.25) < 1e-6, metrics
    assert abs(metrics["rmse"] - 12.5) < 1e-6, metrics
    # WAPE = sum(|err|) / sum(|actual|) = 45 / 700 * 100 = 6.42857...%
    assert abs(metrics["wape_pct"] - (45 / 700 * 100)) < 1e-6, metrics
    # Accuracy% = 100 - WAPE (method="wape")
    assert abs(metrics["accuracy_pct"] - (100 - 45 / 700 * 100)) < 1e-6, metrics
    # Accuracy% should instead track MAPE when method="mape"
    mape_metrics = compute_all_metrics(actual, forecast, method="mape")
    assert abs(mape_metrics["accuracy_pct"] - (100 - mape_metrics["mape_pct"])) < 1e-6, mape_metrics
    print(f"[+] MSE={metrics['mse']:.2f}, MAE={metrics['mae']:.2f}, RMSE={metrics['rmse']:.2f}, "
          f"MAPE={metrics['mape_pct']:.2f}%, WAPE={metrics['wape_pct']:.2f}%, "
          f"Accuracy(WAPE)={metrics['accuracy_pct']:.2f}%, Accuracy(MAPE)={mape_metrics['accuracy_pct']:.2f}%")

    # 7. A perfect forecast must score 100% accuracy.
    perfect_acc = forecast_accuracy_pct(actual, actual)
    assert abs(perfect_acc - 100.0) < 1e-9
    print("[+] Perfect forecast correctly scores 100% accuracy")

    # 8. All-zero-actual edge case must not raise (division by zero guarded).
    zeros = pd.Series([0.0, 0.0])
    nan_metrics = compute_all_metrics(zeros, pd.Series([1.0, 2.0]))
    assert np.isnan(nan_metrics["wape_pct"]) and np.isnan(nan_metrics["mape_pct"])
    print("[+] All-zero-actual edge case handled without raising")

    # 9. Worst-error-period finder: the largest miss must be ranked first.
    combined = pd.DataFrame({
        "timestamp": pd.date_range("2026-08-29", periods=4, freq="1h", tz="UTC"),
        "actual_value": [100.0, 200.0, 300.0, 400.0],
        "forecast_value": [110.0, 150.0, 305.0, 300.0],  # errors: 10, 50, 5, 100
    })
    worst = find_worst_error_periods(combined, "actual_value", "forecast_value", top_n=2)
    assert len(worst) == 2
    assert worst.iloc[0]["abs_error"] == 100.0, worst
    assert worst.iloc[1]["abs_error"] == 50.0, worst
    print(f"[+] Worst-error finder correctly ranked the hour with abs_error={worst.iloc[0]['abs_error']:.0f} first")

    # 10. Glossary sanity: every metric shown in the UI has a definition, and vice versa.
    glossary_names = {name for name, _, _ in METRIC_GLOSSARY}
    assert {"MSE", "RMSE", "MAE", "MAPE", "WAPE", "Accuracy %"} <= glossary_names
    print(f"[+] Metric glossary covers: {sorted(glossary_names)}")

    print("\n✅ ALL FORECAST ACCURACY FEATURE CHECKS PASSED!")


if __name__ == "__main__":
    test_forecast_accuracy_step()
