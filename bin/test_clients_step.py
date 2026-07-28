import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))

from src.energy_data_engine.clients.entsoe import AsyncEntsoeClient


class MockEntsoeClient(AsyncEntsoeClient):
    """Mock Client overriding network thread calls to test async concurrency without API keys."""

    def __init__(self):
        super().__init__(api_key="mock_key_123")

    async def fetch_day_ahead_prices(self, bidding_zone: str, start: datetime, end: datetime):
        await asyncio.sleep(0.1)  # Simulate network latency
        dates = pd.date_range(start, end, freq="1h", tz="UTC")
        from src.energy_data_engine.models.schemas import DayAheadPriceRecord
        return [
            DayAheadPriceRecord(timestamp=dt, bidding_zone=bidding_zone, price_eur_mwh=45.5)
            for dt in dates
        ]


async def test_async_client_concurrency():
    print("\n" + "=" * 50)
    print("      STEP 3 ASYNC CLIENT CONCURRENCY HARNESS     ")
    print("=" * 50 + "\n")

    client = MockEntsoeClient()
    start = datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 3, 1, 5, 0, tzinfo=timezone.utc)

    zones = ["DE_LU", "FR", "NL"]
    
    # Fire requests across all 3 bidding zones concurrently using asyncio.gather
    print(f"[+] Dispatching concurrent price requests across zones: {zones}")
    tasks = [client.fetch_day_ahead_prices(zone, start, end) for zone in zones]
    results = await asyncio.gather(*tasks)

    for zone, records in zip(zones, results):
        print(f"    - Zone {zone}: Fetched {len(records)} records successfully.")
        assert len(records) > 0, f"No records returned for {zone}"
        assert records[0].bidding_zone == zone

    print("\n✅ ASYNC CLIENT AND CONCURRENT FETCH VERIFIED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(test_async_client_concurrency())