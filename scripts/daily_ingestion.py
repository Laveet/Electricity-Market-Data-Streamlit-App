"""
Automated Daily Ingestion Script for energy-data-engine.

Fetches the latest market data for DE_LU, FR, and NL asynchronously and writes 
directly to partitioned Parquet lakehouse storage:
  - data/lakehouse/day_ahead_prices
  - data/lakehouse/total_load
  - data/lakehouse/generation
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

# Fix module import paths for direct execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings
from src.energy_data_engine.clients.entsoe import AsyncEntsoeClient
from src.energy_data_engine.storage.parquet_store import ParquetLakehouseWriter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("daily_ingestion")


async def process_zone_dataset(client: AsyncEntsoeClient, writer: ParquetLakehouseWriter, zone: str, dataset_name: str, start_date: datetime, end_date: datetime):
    """Fetches and saves a specific dataset for a given bidding zone."""
    try:
        logger.info(f"Fetching {dataset_name} for zone {zone}...")
        
        if dataset_name == "day_ahead_prices":
            records = await client.fetch_day_ahead_prices(zone, start_date, end_date)
        elif dataset_name == "total_load":
            records = await client.fetch_total_load(zone, start_date, end_date)
        elif dataset_name == "generation":
            records = await client.fetch_generation(zone, start_date, end_date)
        else:
            logger.error(f"Unknown dataset name: {dataset_name}")
            return

        if records:
            writer.write_records(records=records, dataset_name=dataset_name)
            logger.info(f"✅ Saved {len(records)} records to '{dataset_name}' for {zone}")
        else:
            logger.warning(f"⚠️ No records returned for {dataset_name} in zone {zone}")

    except Exception as e:
        logger.error(f"❌ Failed to process {dataset_name} for {zone}: {e}")


async def run_daily_ingestion(days_back: int = 2):
    """
    Fetches market data for the past `days_back` days up to current UTC time
    and writes directly to Parquet lakehouse datasets.
    """
    end_date = datetime.now(timezone.utc)
    start_date = (end_date - timedelta(days=days_back)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    zones = getattr(settings, "TARGET_ZONES", ["DE_LU", "FR", "NL"])
    datasets = ["day_ahead_prices", "total_load", "generation"]

    logger.info(f"🚀 Starting daily ingestion from {start_date.strftime('%Y-%m-%d %H:%M UTC')} to {end_date.strftime('%Y-%m-%d %H:%M UTC')}")
    logger.info(f"🌐 Target Zones: {zones}")

    client = AsyncEntsoeClient()
    writer = ParquetLakehouseWriter()

    # Execute zone fetches asynchronously across all target zones
    tasks = []
    for zone in zones:
        for dataset in datasets:
            tasks.append(process_zone_dataset(client, writer, zone, dataset, start_date, end_date))

    # Run tasks concurrently
    await asyncio.gather(*tasks)

    logger.info("🎉 Daily ingestion pipeline completed successfully!")


if __name__ == "__main__":
    # Allow passing custom days_back as a command line argument (e.g., `python scripts/daily_ingestion.py 7`)
    days = 2
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            logger.warning(f"Invalid days argument '{sys.argv[1]}', defaulting to 2 days.")

    asyncio.run(run_daily_ingestion(days_back=days))