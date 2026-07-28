import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.energy_data_engine.models.schemas import DayAheadPriceRecord, GenerationRecord, TotalLoadRecord
from src.energy_data_engine.storage.parquet_store import ParquetLakehouseWriter

def generate_mock_datasets():
    writer = ParquetLakehouseWriter()
    
    # Generate 14 days of hourly data ending today
    end_dt = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start_dt = end_dt - timedelta(days=14)
    timestamps = pd.date_range(start=start_dt, end=end_dt, freq="1h", tz="UTC")

    zones = ["DE_LU", "FR", "NL"]
    
    print(f"Generating mock records for zones {zones} from {start_dt.date()} to {end_dt.date()}...")

    for zone in zones:
        # 1. Day-Ahead Prices
        price_base = 80.0 if zone == "DE_LU" else (75.0 if zone == "FR" else 85.0)
        price_records = []
        for ts in timestamps:
            hourly_variation = 20 * np.sin(2 * np.pi * ts.hour / 24)
            noise = np.random.normal(0, 5)
            price = max(-10.0, price_base + hourly_variation + noise)
            
            price_records.append(
                DayAheadPriceRecord(
                    timestamp=ts,
                    bidding_zone=zone,
                    price_eur_mwh=round(price, 2)
                )
            )
        writer.write_records(price_records, dataset_name="day_ahead_prices")

        # 2. Total Load (Demand)
        load_base = 55000.0 if zone == "DE_LU" else (45000.0 if zone == "FR" else 15000.0)
        load_records = []
        for ts in timestamps:
            daily_pattern = 10000 * np.sin(2 * np.pi * (ts.hour - 6) / 24)
            noise = np.random.normal(0, 1000)
            load = max(1000.0, load_base + daily_pattern + noise)
            
            load_records.append(
                TotalLoadRecord(
                    timestamp=ts,
                    bidding_zone=zone,
                    load_mw=round(load, 2)
                )
            )
        writer.write_records(load_records, dataset_name="total_load")

        # 3. Generation Mix
        gen_records = []
        for ts in timestamps:
            solar = max(0.0, 15000 * np.sin(np.pi * (ts.hour - 6) / 12)) if 6 <= ts.hour <= 18 else 0.0
            wind_onshore = max(500.0, np.random.normal(12000, 3000))
            wind_offshore = max(200.0, np.random.normal(5000, 1000))
            gas = max(1000.0, np.random.normal(8000, 1500))
            hard_coal = max(500.0, np.random.normal(4000, 800))
            nuclear = 0.0 if zone == "DE_LU" else (max(5000.0, np.random.normal(35000, 2000)) if zone == "FR" else 400.0)

            gen_records.append(
                GenerationRecord(
                    timestamp=ts,
                    bidding_zone=zone,
                    solar_mw=round(solar, 2),
                    wind_onshore_mw=round(wind_onshore, 2),
                    wind_offshore_mw=round(wind_offshore, 2),
                    gas_mw=round(gas, 2),
                    hard_coal_mw=round(hard_coal, 2),
                    nuclear_mw=round(nuclear, 2)
                )
            )
        writer.write_records(gen_records, dataset_name="generation")

    print("✅ All sample datasets (prices, load, generation) successfully populated in Lakehouse!")

if __name__ == "__main__":
    generate_mock_datasets()