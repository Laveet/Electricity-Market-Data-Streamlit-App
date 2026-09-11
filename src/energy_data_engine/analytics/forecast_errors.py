"""Forecast accuracy metrics, following standard load/price-forecasting industry practice.

MSE / RMSE / MAPE are the most commonly reported metrics; WAPE (a.k.a. weighted
MAPE) is generally preferred by TSOs and utilities for load forecasting because it
doesn't blow up on near-zero hours the way plain MAPE can (this matters for price
too, since day-ahead prices can be very close to zero, or even negative). Accuracy %
is conventionally reported as `100 - WAPE` (or `100 - MAPE`).
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


# Short, plain-language definitions shown in the app's "What do these metrics mean?"
# expander. Keep these to 1-2 sentences each -- this is a tooltip, not a textbook.
METRIC_GLOSSARY: List[Tuple[str, str, str]] = [
    (
        "MSE",
        "Mean Squared Error",
        "Average of the squared differences between forecast and actual. Squaring "
        "punishes big misses much more than small ones. Same units as the value "
        "squared (e.g. MW²), so it's mostly useful for comparing models, not for "
        "reading on its own.",
    ),
    (
        "RMSE",
        "Root Mean Squared Error",
        "Square root of MSE, brought back into the original units (MW, €/MWh). "
        "Like MSE, it penalizes large errors heavily -- a couple of very bad hours "
        "can dominate the score even if most hours were forecast well.",
    ),
    (
        "MAE",
        "Mean Absolute Error",
        "Average of the absolute (unsigned) differences between forecast and "
        "actual, in the original units. Easier to interpret than RMSE and treats "
        "every hour's error equally, regardless of size.",
    ),
    (
        "MAPE",
        "Mean Absolute Percentage Error",
        "Average absolute error as a percentage of the actual value. Intuitive "
        "(\"we were off by X% on average\"), but can blow up or become misleading "
        "in hours where the actual value is close to zero.",
    ),
    (
        "WAPE",
        "Weighted Absolute Percentage Error",
        "Total absolute error divided by the total actual value across all hours, "
        "as a percentage. More robust than MAPE for series with near-zero or "
        "negative values (common in electricity prices), so it's generally "
        "preferred by TSOs/utilities as the headline number.",
    ),
    (
        "Accuracy %",
        "100 − WAPE (or 100 − MAPE)",
        "A single, intuitive headline number: 100% means a perfect forecast. "
        "Reported here as 100 minus whichever error percentage you select above.",
    ),
]


def _align(actual: pd.Series, forecast: pd.Series) -> Tuple[np.ndarray, np.ndarray]:
    """Aligns two series by index and drops any row missing in either."""
    df = pd.DataFrame({"actual": actual, "forecast": forecast}).dropna()
    return df["actual"].to_numpy(dtype=float), df["forecast"].to_numpy(dtype=float)


def mean_squared_error(actual: pd.Series, forecast: pd.Series) -> float:
    a, f = _align(actual, forecast)
    if len(a) == 0:
        return float("nan")
    return float(np.mean((a - f) ** 2))


def mean_absolute_error(actual: pd.Series, forecast: pd.Series) -> float:
    a, f = _align(actual, forecast)
    if len(a) == 0:
        return float("nan")
    return float(np.mean(np.abs(a - f)))


def root_mean_squared_error(actual: pd.Series, forecast: pd.Series) -> float:
    a, f = _align(actual, forecast)
    if len(a) == 0:
        return float("nan")
    return float(np.sqrt(np.mean((a - f) ** 2)))


def mean_absolute_percentage_error(actual: pd.Series, forecast: pd.Series) -> float:
    """MAPE (%). Hours where actual == 0 are excluded to avoid division by zero."""
    a, f = _align(actual, forecast)
    mask = a != 0
    if mask.sum() == 0:
        return float("nan")
    return float(np.mean(np.abs((a[mask] - f[mask]) / a[mask])) * 100)


def weighted_absolute_percentage_error(actual: pd.Series, forecast: pd.Series) -> float:
    """WAPE (%): sum of absolute errors over sum of |actuals|. Robust to near-zero hours."""
    a, f = _align(actual, forecast)
    if len(a) == 0 or np.sum(np.abs(a)) == 0:
        return float("nan")
    return float(np.sum(np.abs(a - f)) / np.sum(np.abs(a)) * 100)


def forecast_accuracy_pct(actual: pd.Series, forecast: pd.Series, method: str = "wape") -> float:
    """Headline accuracy %, conventionally reported as 100 - WAPE (or 100 - MAPE)."""
    error_pct = (
        weighted_absolute_percentage_error(actual, forecast)
        if method == "wape"
        else mean_absolute_percentage_error(actual, forecast)
    )
    if np.isnan(error_pct):
        return float("nan")
    return max(0.0, 100.0 - error_pct)


def compute_all_metrics(actual: pd.Series, forecast: pd.Series, method: str = "wape") -> Dict[str, float]:
    """Convenience wrapper returning every metric used in the Forecast Accuracy tab.

    `method` ("wape" or "mape") controls which error percentage the headline
    `accuracy_pct` is derived from; both MAPE and WAPE are always included too.
    """
    return {
        "mse": mean_squared_error(actual, forecast),
        "mae": mean_absolute_error(actual, forecast),
        "rmse": root_mean_squared_error(actual, forecast),
        "mape_pct": mean_absolute_percentage_error(actual, forecast),
        "wape_pct": weighted_absolute_percentage_error(actual, forecast),
        "accuracy_pct": forecast_accuracy_pct(actual, forecast, method=method),
    }


def find_worst_error_periods(
    combined: pd.DataFrame,
    actual_col: str,
    forecast_col: str,
    timestamp_col: str = "timestamp",
    top_n: int = 3,
) -> pd.DataFrame:
    """Returns the `top_n` timestamps with the largest absolute forecast error.

    Args:
        combined: DataFrame containing at least `timestamp_col`, `actual_col`,
            and `forecast_col`. Rows where either value is missing are ignored.
        actual_col: Column holding the actual/realized values.
        forecast_col: Column holding the forecast values to score.
        timestamp_col: Column holding timestamps.
        top_n: How many worst hours to return, sorted worst-first.

    Returns:
        DataFrame with columns [timestamp, actual, forecast, abs_error, pct_error],
        sorted by abs_error descending. Empty if there's nothing to score.
    """
    df = combined[[timestamp_col, actual_col, forecast_col]].dropna().copy()
    if df.empty:
        return pd.DataFrame(columns=[timestamp_col, "actual", "forecast", "abs_error", "pct_error"])

    df = df.rename(columns={actual_col: "actual", forecast_col: "forecast"})
    df["abs_error"] = (df["forecast"] - df["actual"]).abs()
    with np.errstate(divide="ignore", invalid="ignore"):
        df["pct_error"] = np.where(
            df["actual"] != 0, (df["forecast"] - df["actual"]).abs() / df["actual"].abs() * 100, np.nan
        )

    return df.sort_values("abs_error", ascending=False).head(top_n).reset_index(drop=True)
