import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))

from src.energy_data_engine.analytics.metrics import FundamentalMetrics
from src.energy_data_engine.analytics.spreads import SpreadCalculators


def test_analytics_features():
    print("\n" + "=" * 50)
    print("      STEP 5 FEATURE ENGINEERING HARNESS           ")
    print("=" * 50 + "\n")

    # 1. Test Fundamental Metrics (Residual Load & Penetration)
    mock_grid_data = pd.DataFrame({
        "timestamp": pd.date_range("2026-03-01", periods=3, freq="1h", tz="UTC"),
        "load_mw": [10000.0, 12000.0, 11000.0],
        "solar_mw": [2000.0, 4000.0, 1000.0],
        "wind_onshore_mw": [3000.0, 3000.0, 4000.0],
        "wind_offshore_mw": [1000.0, 1000.0, 1000.0],
    })

    metrics_df = FundamentalMetrics.calculate_renewable_penetration(mock_grid_data)
    
    # Check hour 2: Total Renewables = 4000+3000+1000 = 8000 MW. Residual Load = 12000 - 8000 = 4000 MW
    assert metrics_df.iloc[1]["residual_load_mw"] == 4000.0, "Residual Load calculation failed!"
    # Penetration hour 2: (8000 / 12000) * 100 = 66.67%
    assert abs(metrics_df.iloc[1]["renewable_penetration_pct"] - 66.666) < 0.01, "Penetration % failed!"
    
    print(f"[+] Residual Load (Hour 2)       : {metrics_df.iloc[1]['residual_load_mw']} MW")
    print(f"[+] Renewable Penetration (Hour 2): {metrics_df.iloc[1]['renewable_penetration_pct']:.2f}%")

    # 2. Test Cross-Border Spread Calculation
    zone_de = pd.DataFrame({
        "timestamp": pd.date_range("2026-03-01", periods=2, freq="1h", tz="UTC"),
        "price_eur_mwh": [50.0, 70.0]
    })
    zone_fr = pd.DataFrame({
        "timestamp": pd.date_range("2026-03-01", periods=2, freq="1h", tz="UTC"),
        "price_eur_mwh": [40.0, 80.0]
    })

    spread_df = SpreadCalculators.calculate_cross_border_spread(
        df_zone_a=zone_de, df_zone_b=zone_fr, zone_a_name="DE", zone_b_name="FR"
    )
    
    # DE - FR spread hour 1 = 50 - 40 = +10 EUR/MWh
    assert spread_df.iloc[0]["spread_DE_FR_eur_mwh"] == 10.0
    print(f"[+] Cross-Border Spread (Hour 1) : {spread_df.iloc[0]['spread_DE_FR_eur_mwh']} EUR/MWh")

    # 3. Test Clean Spark Spread (CSS)
    css = SpreadCalculators.calculate_clean_spark_spread(
        power_price=80.0, gas_price=30.0, carbon_price=70.0, efficiency=0.50, emission_factor=0.202
    )
    # CSS = 80 - (30 / 0.50) - (70 * 0.202) = 80 - 60 - 14.14 = 5.86 EUR/MWh
    assert abs(css - 5.86) < 0.01
    print(f"[+] Clean Spark Spread (Gas)    : {css:.2f} EUR/MWh")

    print("\n✅ ALL FEATURE ENGINEERING METRICS VERIFIED SUCCESSFULLY!")


if __name__ == "__main__":
    test_analytics_features()