import asyncio
from datetime import datetime, timezone
from typing import List, Optional

from src.energy_data_engine.clients.entsoe import AsyncEntsoeClient
from src.energy_data_engine.storage.parquet_store import ParquetLakehouseWriter
from src.energy_data_engine.storage.duck_analytics import DuckDBAnalyticsEngine
from src.energy_data_engine.analytics.metrics import FundamentalMetrics
from src.energy_data_engine.analytics.spreads import SpreadCalculators
from src.energy_data_engine.utils.logger import logger


class EnergyDataPipeline:
    """Orchestrates async data ingestion, Pydantic validation, Parquet lakehouse storage, and DuckDB feature analytics."""

    def __init__(self, client: Optional[AsyncEntsoeClient] = None):
        self.client = client or AsyncEntsoeClient()
        self.writer = ParquetLakehouseWriter()
        self.analytics = DuckDBAnalyticsEngine()

    async def run_ingestion_pipeline(
        self,
        bidding_zones: List[str],
        start: datetime,
        end: datetime,
    ):
        """Executes full ingestion across Day-Ahead Prices, Total Load, and Generation for target zones."""
        logger.info("Starting End-to-End Ingestion Pipeline", zones=bidding_zones, start=start, end=end)

        for zone in bidding_zones:
            # 1. Fetch & Store Day-Ahead Prices
            try:
                price_records = await self.client.fetch_day_ahead_prices(zone, start, end)
                if price_records:
                    self.writer.write_records(price_records, dataset_name="day_ahead_prices")
            except Exception as e:
                logger.error("Failed fetching day-ahead prices", zone=zone, error=str(e))

            # 2. Fetch & Store Total Load
            try:
                load_records = await self.client.fetch_total_load(zone, start, end)
                if load_records:
                    self.writer.write_records(load_records, dataset_name="total_load")
            except Exception as e:
                logger.error("Failed fetching total load", zone=zone, error=str(e))

            # 3. Fetch & Store Generation Mix
            try:
                gen_records = await self.client.fetch_generation(zone, start, end)
                if gen_records:
                    self.writer.write_records(gen_records, dataset_name="generation")
            except Exception as e:
                logger.error("Failed fetching generation mix", zone=zone, error=str(e))

        logger.info("End-to-End Ingestion Pipeline Execution Finished!")

    def compute_zone_metrics(self, zone: str):
        """Loads partitioned data via DuckDB and calculates fundamental metrics (Residual Load, Renewables %)." """
        gen_df = self.analytics.query_dataset_by_zone("generation", zone=zone)
        load_df = self.analytics.query_dataset_by_zone("total_load", zone=zone)

        if gen_df.empty or load_df.empty:
            logger.warning("Insufficient data to compute zone metrics", zone=zone)
            return None

        # Merge on timestamp
        merged = gen_df.merge(load_df[["timestamp", "load_mw"]], on="timestamp", how="inner")
        
        # Calculate Fundamental Metrics
        metrics_df = FundamentalMetrics.calculate_renewable_penetration(merged)
        metrics_df = FundamentalMetrics.calculate_ramp_rate(metrics_df, target_col="load_mw")
        
        return metrics_df

    def compute_cross_border_spread(self, zone_a: str, zone_b: str):
        """Computes price spread between two bidding zones."""
        prices_a = self.analytics.query_dataset_by_zone("day_ahead_prices", zone=zone_a)
        prices_b = self.analytics.query_dataset_by_zone("day_ahead_prices", zone=zone_b)

        if prices_a.empty or prices_b.empty:
            logger.warning("Missing price data for spread calculation", zone_a=zone_a, zone_b=zone_b)
            return None

        return SpreadCalculators.calculate_cross_border_spread(prices_a, prices_b, zone_a, zone_b)