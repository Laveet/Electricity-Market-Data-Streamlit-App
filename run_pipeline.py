import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add src/ to path so package modules are discoverable
sys.path.append(str(Path(__file__).resolve().parent / "src"))

from src.energy_data_engine.pipeline import EnergyDataPipeline
from src.energy_data_engine.utils.logger import logger


async def main():
    print("\n" + "=" * 60)
    print(" 🚀 STARTING ENERGY DATA ENGINE - ASYNC INGESTION PIPELINE")
    print("=" * 60 + "\n")

    # Define target bidding zones and date range (default: last 3 days)
    target_zones = ["DE_LU", "FR", "NL"]
    end_time = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(days=3)

    logger.info("Pipeline Execution Window", start=start_time.isoformat(), end=end_time.isoformat())

    # Initialize and execute pipeline
    pipeline = EnergyDataPipeline()
    await pipeline.run_ingestion_pipeline(
        bidding_zones=target_zones,
        start=start_time,
        end=end_time,
    )

    print("\n" + "=" * 60)
    print(" ✅ INGESTION & LAKEHOUSE WRITES COMPLETE!")
    print("=" * 60 + "\n")

    # Compute & Print Summary Analytics for DE_LU
    logger.info("Calculating post-ingestion fundamental metrics for DE_LU...")
    metrics_df = pipeline.compute_zone_metrics("DE_LU")

    if metrics_df is not None and not metrics_df.empty:
        print("📊 DE_LU Fundamental Metrics Summary (Latest 3 Rows):")
        display_cols = [c for c in ["timestamp", "load_mw", "residual_load_mw", "renewable_penetration_pct"] if c in metrics_df.columns]
        print(metrics_df[display_cols].tail(3).to_string(index=False))
        print("\n")
    else:
        print("ℹ️ Note: Fundamental metrics require complete load and generation data in Lakehouse.\n")

    # Compute Cross-Border Spread: DE_LU vs FR
    spread_df = pipeline.compute_cross_border_spread("DE_LU", "FR")
    if spread_df is not None and not spread_df.empty:
        print("🔄 Cross-Border Price Spread: DE_LU - FR (Latest 3 Rows):")
        print(spread_df.tail(3).to_string(index=False))
        print("\n")


if __name__ == "__main__":
    asyncio.run(main())