import sys
from pathlib import Path
from datetime import datetime, timezone
import tempfile

sys.path.append(str(Path(__file__).resolve().parent))

from src.energy_data_engine.models.schemas import DayAheadPriceRecord
from src.energy_data_engine.storage.parquet_store import ParquetLakehouseWriter
from src.energy_data_engine.storage.duck_analytics import DuckDBAnalyticsEngine


def test_storage_and_duckdb_pipeline():
    print("\n" + "=" * 50)
    print("      STEP 4 LAKEHOUSE STORAGE & DUCKDB HARNESS     ")
    print("=" * 50 + "\n")

    # Create temporary directory for isolated test lakehouse
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # 1. Create Mock Day-Ahead Price Records
        records = [
            DayAheadPriceRecord(
                timestamp=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
                bidding_zone="DE_LU",
                price_eur_mwh=52.40,
            ),
            DayAheadPriceRecord(
                timestamp=datetime(2026, 3, 1, 11, 0, tzinfo=timezone.utc),
                bidding_zone="DE_LU",
                price_eur_mwh=-12.50,  # Negative price event
            ),
            DayAheadPriceRecord(
                timestamp=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
                bidding_zone="FR",
                price_eur_mwh=68.10,
            ),
        ]

        # 2. Write to Partitioned Lakehouse
        writer = ParquetLakehouseWriter(base_dir=tmp_path)
        writer.write_records(records, dataset_name="day_ahead_prices")

        # Verify Partition Directory Structure
        expected_partition = tmp_path / "day_ahead_prices" / "zone=DE_LU" / "year=2026" / "month=03"
        assert expected_partition.exists(), f"Partition folder missing: {expected_partition}"
        print(f"[+] Hive Partition Created : {expected_partition}")

        # 3. Query with Zero-Copy DuckDB Engine
        analytics = DuckDBAnalyticsEngine(data_dir=tmp_path)
        de_df = analytics.query_dataset_by_zone(dataset_name="day_ahead_prices", zone="DE_LU")

        assert len(de_df) == 2, f"Expected 2 records for DE_LU, got {len(de_df)}"
        assert de_df.iloc[1]["price_eur_mwh"] == -12.50
        print(f"[+] DuckDB SQL Result     : Query returned {len(de_df)} DE_LU records perfectly.")

        # 4. Test Export Helpers
        csv_out = tmp_path / "exports" / "prices.csv"
        xlsx_out = tmp_path / "exports" / "prices.xlsx"

        analytics.export_to_csv(de_df, csv_out)
        analytics.export_to_excel(de_df, xlsx_out)

        assert csv_out.exists(), "CSV export failed!"
        assert xlsx_out.exists(), "Excel export failed!"
        print(f"[+] CSV & Excel Exporters  : Files generated successfully.")

    print("\n✅ LAKEHOUSE STORAGE AND DUCKDB ENGINE VERIFIED SUCCESSFULLY!")


if __name__ == "__main__":
    test_storage_and_duckdb_pipeline()