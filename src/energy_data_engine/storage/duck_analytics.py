# # from pathlib import Path
# # import duckdb
# # import pandas as pd
# # from src.energy_data_engine.utils.logger import logger


# # class DuckDBAnalyticsEngine:
# #     """In-memory zero-copy OLAP query engine using DuckDB over Parquet Lakehouse files."""

# #     def __init__(self, data_dir: Path | str = "data/lakehouse"):
# #         self.data_dir = Path(data_dir)
# #         self.conn = duckdb.connect(database=":memory:")

# #     def query_dataset_by_zone(self, dataset_name: str, zone: str) -> pd.DataFrame:
# #         """Executes zero-copy DuckDB SQL query over partitioned Parquet files filtered by bidding zone."""
# #         dataset_path = self.data_dir / dataset_name

# #         # Check if dataset directory exists and contains any .parquet files
# #         parquet_files = list(dataset_path.glob("**/*.parquet")) if dataset_path.exists() else []
# #         if not parquet_files:
# #             logger.info("No Parquet files found for dataset", dataset=dataset_name, zone=zone)
# #             return pd.DataFrame()

# #         # Construct path pattern for DuckDB read_parquet
# #         query_path = str(dataset_path / "**" / "*.parquet")
# #         query = f"""
# #             SELECT * FROM read_parquet('{query_path}')
# #             WHERE zone = '{zone}'
# #             ORDER BY timestamp ASC
# #         """
# #         try:
# #             logger.info("Executing DuckDB SQL query", query=query)
# #             df = self.conn.execute(query).df()
# #             logger.info("DuckDB Query Executed Successfully", rows_returned=len(df))
# #             return df
# #         except Exception as e:
# #             logger.error("DuckDB Query Execution Error", error=str(e), query=query)
# #             return pd.DataFrame()

# #     @staticmethod
# #     def export_to_excel(df: pd.DataFrame, output_path: Path | str, sheet_name: str = "Market Data") -> Path:
# #         """Exports query results directly to Excel (.xlsx) format using openpyxl, handling timezone awareness."""
# #         path = Path(output_path)
# #         path.parent.mkdir(parents=True, exist_ok=True)

# #         export_df = df.copy()

# #         # Remove timezone info for Excel compatibility
# #         for col in export_df.select_dtypes(include=["datetime64[ns, UTC]", "datetimetz"]).columns:
# #             export_df[col] = export_df[col].dt.tz_localize(None)

# #         with pd.ExcelWriter(path, engine="openpyxl") as writer:
# #             export_df.to_excel(writer, sheet_name=sheet_name, index=False)

# #         logger.info("Exported query results to Excel", path=str(path))
# #         return path

# #     @staticmethod
# #     def export_to_csv(df: pd.DataFrame, output_path: Path | str) -> Path:
# #         """Exports query results to standard CSV format."""
# #         path = Path(output_path)
# #         path.parent.mkdir(parents=True, exist_ok=True)
# #         df.to_csv(path, index=False)
# #         logger.info("Exported query results to CSV", path=str(path))
# #         return path
# import io
# from pathlib import Path
# import duckdb
# import pandas as pd
# from src.energy_data_engine.utils.logger import logger


# class DuckDBAnalyticsEngine:
#     """In-memory zero-copy OLAP query engine using DuckDB over Parquet Lakehouse files."""

#     def __init__(self, data_dir: Path | str = "data/lakehouse"):
#         self.data_dir = Path(data_dir)
#         self.conn = duckdb.connect(database=":memory:")

#     def query_dataset_by_zone(self, dataset_name: str, zone: str) -> pd.DataFrame:
#         """Executes zero-copy DuckDB SQL query over partitioned Parquet files filtered by bidding zone."""
#         dataset_path = self.data_dir / dataset_name

#         parquet_files = (
#             list(dataset_path.glob("**/*.parquet"))
#             if dataset_path.exists()
#             else []
#         )
#         if not parquet_files:
#             logger.info(
#                 "No Parquet files found for dataset",
#                 dataset=dataset_name,
#                 zone=zone,
#             )
#             return pd.DataFrame()

#         query_path = str(dataset_path / "**" / "*.parquet")
#         query = f"""
#             SELECT * FROM read_parquet('{query_path}')
#             WHERE zone = '{zone}'
#             ORDER BY timestamp ASC
#         """
#         try:
#             logger.info("Executing DuckDB SQL query", query=query)
#             df = self.conn.execute(query).df()
#             logger.info(
#                 "DuckDB Query Executed Successfully", rows_returned=len(df)
#             )
#             return df
#         except Exception as e:
#             logger.error(
#                 "DuckDB Query Execution Error", error=str(e), query=query
#             )
#             return pd.DataFrame()

#     def generate_clean_excel_bytes(
#         self, zone: str, start_date: str, end_date: str
#     ) -> bytes:
#         """Queries, deduplicates, and generates a multi-sheet Excel file in memory for Streamlit downloads."""
#         output = io.BytesIO()

#         def fetch_deduped(dataset_name: str, partition_cols: str) -> pd.DataFrame:
#             dataset_path = self.data_dir / dataset_name
#             if not dataset_path.exists() or not list(dataset_path.glob("**/*.parquet")):
#                 return pd.DataFrame()

#             query_path = str(dataset_path / "**" / "*.parquet")
#             query = f"""
#                 SELECT * FROM read_parquet('{query_path}')
#                 WHERE zone = '{zone}'
#                   AND timestamp >= '{start_date}'
#                   AND timestamp <= '{end_date}'
#                 QUALIFY ROW_NUMBER() OVER (PARTITION BY {partition_cols} ORDER BY timestamp DESC) = 1
#                 ORDER BY timestamp ASC
#             """
#             try:
#                 return self.conn.execute(query).df()
#             except Exception as e:
#                 logger.error(f"Error querying {dataset_name} for Excel export", error=str(e))
#                 return pd.DataFrame()

#         # Fetch clean datasets
#         df_prices = fetch_deduped("day_ahead_prices", "timestamp")
#         df_load = fetch_deduped("total_load", "timestamp")
#         df_gen = fetch_deduped("generation", "timestamp, production_type")

#         # Strip timezones for Excel compatibility
#         for df in [df_prices, df_load, df_gen]:
#             if not df.empty and "timestamp" in df.columns:
#                 df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)

#         # Write to in-memory Excel buffer
#         with pd.ExcelWriter(output, engine="openpyxl") as writer:
#             if not df_prices.empty:
#                 df_prices.to_excel(writer, sheet_name="Day Ahead Prices", index=False)
#             if not df_load.empty:
#                 df_load.to_excel(writer, sheet_name="Total Load", index=False)
#             if not df_gen.empty:
#                 df_gen.to_excel(writer, sheet_name="Generation Mix", index=False)

#         output.seek(0)
#         return output.getvalue()

#     @staticmethod
#     def export_to_excel(
#         df: pd.DataFrame,
#         output_path: Path | str,
#         sheet_name: str = "Market Data",
#     ) -> Path:
#         """Exports query results directly to Excel (.xlsx) format using openpyxl, handling timezone awareness."""
#         path = Path(output_path)
#         path.parent.mkdir(parents=True, exist_ok=True)

#         export_df = df.copy()
#         for col in export_df.select_dtypes(
#             include=["datetime64[ns, UTC]", "datetimetz"]
#         ).columns:
#             export_df[col] = export_df[col].dt.tz_localize(None)

#         with pd.ExcelWriter(path, engine="openpyxl") as writer:
#             export_df.to_excel(writer, sheet_name=sheet_name, index=False)

#         logger.info("Exported query results to Excel", path=str(path))
#         return path

#     @staticmethod
#     def export_to_csv(df: pd.DataFrame, output_path: Path | str) -> Path:
#         """Exports query results to standard CSV format."""
#         path = Path(output_path)
#         path.parent.mkdir(parents=True, exist_ok=True)
#         df.to_csv(path, index=False)
#         logger.info("Exported query results to CSV", path=str(path))
#         return path

import io
from pathlib import Path
import duckdb
import pandas as pd
from src.energy_data_engine.utils.logger import logger


class DuckDBAnalyticsEngine:
    """In-memory zero-copy OLAP query engine using DuckDB over Parquet Lakehouse files."""

    def __init__(self, data_dir: Path | str = "data/lakehouse"):
        self.data_dir = Path(data_dir)
        self.conn = duckdb.connect(database=":memory:")

    def query_dataset_by_zone(self, dataset_name: str, zone: str) -> pd.DataFrame:
        """Executes zero-copy DuckDB SQL query over partitioned Parquet files filtered by bidding zone."""
        dataset_path = self.data_dir / dataset_name

        parquet_files = (
            list(dataset_path.glob("**/*.parquet"))
            if dataset_path.exists()
            else []
        )
        if not parquet_files:
            logger.info(
                "No Parquet files found for dataset",
                dataset=dataset_name,
                zone=zone,
            )
            return pd.DataFrame()

        query_path = str(dataset_path / "**" / "*.parquet")
        query = f"""
            SELECT * FROM read_parquet('{query_path}')
            WHERE zone = '{zone}'
            ORDER BY timestamp ASC
        """
        try:
            logger.info("Executing DuckDB SQL query", query=query)
            df = self.conn.execute(query).df()
            logger.info(
                "DuckDB Query Executed Successfully", rows_returned=len(df)
            )
            return df
        except Exception as e:
            logger.error(
                "DuckDB Query Execution Error", error=str(e), query=query
            )
            return pd.DataFrame()

    def generate_clean_excel_bytes(
        self, zone: str, start_date: str, end_date: str
    ) -> bytes:
        """Queries, deduplicates, and generates a multi-sheet Excel file in memory for Streamlit downloads."""
        output = io.BytesIO()

        def fetch_deduped(dataset_name: str, partition_cols: str) -> pd.DataFrame:
            dataset_path = self.data_dir / dataset_name
            if not dataset_path.exists() or not list(dataset_path.glob("**/*.parquet")):
                return pd.DataFrame()

            query_path = str(dataset_path / "**" / "*.parquet")
            query = f"""
                SELECT * FROM read_parquet('{query_path}')
                WHERE zone = '{zone}'
                  AND timestamp >= '{start_date}'
                  AND timestamp <= '{end_date}'
                QUALIFY ROW_NUMBER() OVER (PARTITION BY {partition_cols} ORDER BY timestamp DESC) = 1
                ORDER BY timestamp ASC
            """
            try:
                return self.conn.execute(query).df()
            except Exception as e:
                logger.error(f"Error querying {dataset_name} for Excel export", error=str(e))
                return pd.DataFrame()

        # Fetch clean datasets (including intraday_prices)
        df_prices = fetch_deduped("day_ahead_prices", "timestamp")
        df_intraday = fetch_deduped("intraday_prices", "timestamp")
        df_load = fetch_deduped("total_load", "timestamp")
        df_gen = fetch_deduped("generation", "timestamp, production_type")

        # Strip timezones for Excel compatibility
        for df in [df_prices, df_intraday, df_load, df_gen]:
            if not df.empty and "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)

        # Write to in-memory Excel buffer
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            if not df_prices.empty:
                df_prices.to_excel(writer, sheet_name="Day Ahead Prices", index=False)
            if not df_intraday.empty:
                df_intraday.to_excel(writer, sheet_name="Intraday Prices", index=False)
            if not df_load.empty:
                df_load.to_excel(writer, sheet_name="Total Load", index=False)
            if not df_gen.empty:
                df_gen.to_excel(writer, sheet_name="Generation Mix", index=False)

        output.seek(0)
        return output.getvalue()

    @staticmethod
    def export_to_excel(
        df: pd.DataFrame,
        output_path: Path | str,
        sheet_name: str = "Market Data",
    ) -> Path:
        """Exports query results directly to Excel (.xlsx) format using openpyxl, handling timezone awareness."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        export_df = df.copy()
        for col in export_df.select_dtypes(
            include=["datetime64[ns, UTC]", "datetimetz"]
        ).columns:
            export_df[col] = export_df[col].dt.tz_localize(None)

        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            export_df.to_excel(writer, sheet_name=sheet_name, index=False)

        logger.info("Exported query results to Excel", path=str(path))
        return path

    @staticmethod
    def export_to_csv(df: pd.DataFrame, output_path: Path | str) -> Path:
        """Exports query results to standard CSV format."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
        logger.info("Exported query results to CSV", path=str(path))
        return path