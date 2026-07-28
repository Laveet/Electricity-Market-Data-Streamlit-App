# import asyncio
# import os
# import sys
# from datetime import datetime, timezone

# # Ensure project root is in python path
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# from src.energy_data_engine.clients.entsoe import AsyncEntsoeClient
# from src.energy_data_engine.storage.parquet_store import ParquetLakehouseWriter
# from src.energy_data_engine.utils.logger import logger


# async def backfill_germany_fast():
#     """Fast historical backfill for Germany (DE_LU) using ParquetLakehouseWriter."""
#     ZONE = "DE_LU"
#     START_YEAR = 2023
#     CURRENT_YEAR = datetime.now().year
#     now = datetime.now(timezone.utc)

#     client = AsyncEntsoeClient()
#     writer = ParquetLakehouseWriter()

#     logger.info(f"🚀 STARTING FAST GERMANY ({ZONE}) BACKFILL")

#     for year in range(START_YEAR, CURRENT_YEAR + 1):
#         start = datetime(year, 1, 1, 0, 0, tzinfo=timezone.utc)

#         # Cap current year to right now
#         if year == CURRENT_YEAR:
#             end = now
#         else:
#             end = datetime(year + 1, 1, 1, 0, 0, tzinfo=timezone.utc)

#         logger.info("=" * 55)
#         logger.info(f"   Fetching Germany ({ZONE}) for Year {year}")
#         logger.info("=" * 55)

#         # 1. Day-Ahead Prices
#         try:
#             logger.info(f"[{year}] Fetching Day-Ahead Prices...")
#             prices = await client.fetch_day_ahead_prices(ZONE, start, end)
#             if prices:
#                 # Pass Pydantic record list directly to write_records
#                 writer.write_records(prices, dataset_name="day_ahead_prices")
#                 logger.info(f"[{year}] Successfully saved {len(prices)} price records.")
#             else:
#                 logger.warning(f"[{year}] No price records returned.")
#         except Exception as e:
#             logger.error(f"[{year}] Failed to fetch prices: {e}")

#         # 2. Total Load
#         try:
#             logger.info(f"[{year}] Fetching Total Load...")
#             load = await client.fetch_total_load(ZONE, start, end)
#             if load:
#                 writer.write_records(load, dataset_name="total_load")
#                 logger.info(f"[{year}] Successfully saved {len(load)} load records.")
#             else:
#                 logger.warning(f"[{year}] No load records returned.")
#         except Exception as e:
#             logger.error(f"[{year}] Failed to fetch load: {e}")

#         # 3. Generation Mix
#         try:
#             logger.info(f"[{year}] Fetching Generation Mix...")
#             gen = await client.fetch_generation(ZONE, start, end)
#             if gen:
#                 writer.write_records(gen, dataset_name="actual_generation")
#                 logger.info(f"[{year}] Successfully saved {len(gen)} generation records.")
#             else:
#                 logger.warning(f"[{year}] No generation records returned.")
#         except Exception as e:
#             logger.error(f"[{year}] Failed to fetch generation: {e}")

#         # Small pause between years to be polite to the ENTSO-E API
#         await asyncio.sleep(2)

#     logger.info("\n✅ GERMANY BACKFILL COMPLETE! Data partition written to local Parquet Lakehouse.")


# if __name__ == "__main__":
#     asyncio.run(backfill_germany_fast())


import asyncio
import os
import sys
from datetime import datetime, timezone

# Ensure project root is in python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.energy_data_engine.clients.entsoe import AsyncEntsoeClient
from src.energy_data_engine.storage.parquet_store import ParquetLakehouseWriter
from src.energy_data_engine.utils.logger import logger


async def finish_2026_generation():
    ZONE = "DE_LU"
    YEAR = 2026
    now = datetime.now(timezone.utc)

    client = AsyncEntsoeClient()
    writer = ParquetLakehouseWriter()

    logger.info(f"🚀 FINISHING 2026 GENERATION MIX FOR GERMANY ({ZONE}) MONTH-BY-MONTH")

    # Iterate through months 1 to current month in 2026
    for month in range(1, now.month + 1):
        start = datetime(YEAR, month, 1, 0, 0, tzinfo=timezone.utc)

        if start > now:
            break

        # Calculate end of month or current moment
        if month == 12:
            end = datetime(YEAR + 1, 1, 1, 0, 0, tzinfo=timezone.utc)
        else:
            end = datetime(YEAR, month + 1, 1, 0, 0, tzinfo=timezone.utc)

        if end > now:
            end = now

        month_str = start.strftime("%Y-%m")
        logger.info(f"Fetching Generation Mix for [{month_str}]...")

        try:
            gen = await client.fetch_generation(ZONE, start, end)
            if gen:
                writer.write_records(gen, dataset_name="actual_generation")
                logger.info(f"✅ [{month_str}] Successfully saved {len(gen)} generation records.")
            else:
                logger.warning(f"⚠️ [{month_str}] No generation records returned.")
        except Exception as e:
            logger.error(f"❌ [{month_str}] Failed to fetch generation mix: {e}")

        # Short pause between months
        await asyncio.sleep(1)

    logger.info("\n🎉 2026 GENERATION MIX BACKFILL COMPLETE!")


if __name__ == "__main__":
    asyncio.run(finish_2026_generation())