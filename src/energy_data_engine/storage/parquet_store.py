from pathlib import Path
from typing import List, Sequence
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel

from config.settings import settings
from src.energy_data_engine.utils.logger import logger


class ParquetLakehouseWriter:
    """Manages Hive-partitioned Parquet storage using PyArrow (zone=XX/year=YYYY/month=MM)."""

    def __init__(self, base_dir: Path | str | None = None):
        self.base_dir = Path(base_dir) if base_dir else settings.DATA_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def write_records(
        self,
        records: Sequence[BaseModel],
        dataset_name: str,
    ) -> Path:
        """Converts Pydantic records into PyArrow tables and writes them to Hive-partitioned Parquet files."""
        if not records:
            logger.warning("No records provided to Parquet lakehouse writer.", dataset=dataset_name)
            return self.base_dir

        # Convert Pydantic records to pandas DataFrame
        data_dicts = [r.model_dump() for r in records]
        df = pd.DataFrame(data_dicts)

        if "timestamp" not in df.columns:
            raise ValueError("Records must contain a 'timestamp' field for time partitioning.")

        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df["year"] = df["timestamp"].dt.year.astype(str)
        df["month"] = df["timestamp"].dt.strftime("%m")

        if "bidding_zone" in df.columns:
            df["zone"] = df["bidding_zone"]

        # -------------------------------------------------------------
        # 🛠️ FIX: DEDUPLICATION BEFORE SAVING TO DISK
        # -------------------------------------------------------------
        # Deduplicate based on primary key columns
        dedup_cols = ["timestamp", "zone"]
        if "production_type" in df.columns:
            dedup_cols.append("production_type")  # Keep distinct production types for generation

        df = df.drop_duplicates(subset=dedup_cols, keep="last")
        # -------------------------------------------------------------

        arrow_table = pa.Table.from_pandas(df)
        dataset_dir = self.base_dir / dataset_name

        pq.write_to_dataset(
            arrow_table,
            root_path=str(dataset_dir),
            partition_cols=["zone", "year", "month"],
            use_dictionary=True,
            compression="SNAPPY",
            existing_data_behavior="overwrite_or_ignore",
        )

        logger.info(
            "Successfully written partitioned Parquet dataset",
            dataset=dataset_name,
            records_count=len(df),
            storage_path=str(dataset_dir),
        )
        return dataset_dir

    # 