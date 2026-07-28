# import asyncio
# import pandas as pd
# from datetime import datetime
# from typing import List, Optional
# from entsoe import EntsoePandasClient

# from config.settings import settings
# from src.energy_data_engine.utils.logger import logger
# from src.energy_data_engine.utils.retry import async_retry
# from src.energy_data_engine.models.schemas import (
#     DayAheadPriceRecord,
#     IntradayPriceRecord,
#     TotalLoadRecord,
#     GenerationRecord,
# )


# class AsyncEntsoeClient:
#     """Asynchronous client wrapper for ENTSO-E Transparency API using entsoe-py."""

#     def __init__(self, api_key: Optional[str] = None):
#         self.api_key = api_key or settings.ENTSOE_API_KEY
#         if not self.api_key:
#             logger.warning("ENTSOE_API_KEY is not set. API requests will fail if unmocked.")
#         self._sync_client = EntsoePandasClient(api_key=self.api_key)
#         self.zone_config = settings.load_zone_config()

#     def _get_eic(self, zone_code: str) -> str:
#         """Helper to fetch EIC code for a bidding zone."""
#         zone_info = self.zone_config.get("bidding_zones", {}).get(zone_code.upper())
#         if not zone_info:
#             raise ValueError(f"Unknown bidding zone: {zone_code}. Defined zones: {list(self.zone_config.get('bidding_zones', {}).keys())}")
#         return zone_info["eic"]

#     # =======================================================
#     # 1. Day-Ahead Prices (DocumentType: A44)
#     # =======================================================
#     @async_retry(retries=3, backoff_factor=1.5)
#     async def fetch_day_ahead_prices(
#         self, bidding_zone: str, start: datetime, end: datetime
#     ) -> List[DayAheadPriceRecord]:
#         """Fetches Day-Ahead Electricity Prices (€/MWh) for a specified zone."""
#         eic_code = self._get_eic(bidding_zone)
#         logger.info("Fetching Day-Ahead Prices", zone=bidding_zone, start=start.isoformat(), end=end.isoformat())

#         # Offload blocking synchronous call to a threadpool worker
#         df: pd.Series = await asyncio.to_thread(
#             self._sync_client.query_day_ahead_prices,
#             country_code=bidding_zone.upper(),
#             start=pd.Timestamp(start),
#             end=pd.Timestamp(end),
#         )

#         records = []
#         for timestamp, price in df.items():
#             if pd.isna(price):
#                 continue
#             record = DayAheadPriceRecord(
#                 timestamp=timestamp,
#                 bidding_zone=bidding_zone,
#                 price_eur_mwh=float(price),
#             )
#             records.append(record)

#         logger.info("Successfully fetched Day-Ahead Prices", zone=bidding_zone, count=len(records))
#         return records

#     # =======================================================
#     # 2. Total Load / Grid Demand (DocumentType: A65)
#     # =======================================================
#     @async_retry(retries=3, backoff_factor=1.5)
#     async def fetch_total_load(
#         self, bidding_zone: str, start: datetime, end: datetime
#     ) -> List[TotalLoadRecord]:
#         """Fetches Actual Grid Demand / Load (MW) for a specified zone."""
#         logger.info("Fetching Total Load", zone=bidding_zone, start=start.isoformat(), end=end.isoformat())

#         df: pd.DataFrame | pd.Series = await asyncio.to_thread(
#             self._sync_client.query_load,
#             country_code=bidding_zone.upper(),
#             start=pd.Timestamp(start),
#             end=pd.Timestamp(end),
#         )

#         # Handle Series or DataFrame responses from entsoe-py
#         series = df["Actual Load"] if isinstance(df, pd.DataFrame) and "Actual Load" in df.columns else df

#         records = []
#         for timestamp, load in series.items():
#             if pd.isna(load):
#                 continue
#             records.append(
#                 TotalLoadRecord(
#                     timestamp=timestamp,
#                     bidding_zone=bidding_zone,
#                     load_mw=float(load),
#                 )
#             )

#         logger.info("Successfully fetched Total Load", zone=bidding_zone, count=len(records))
#         return records

#     # =======================================================
#     # 3. Actual Generation per Production Type (DocumentType: A75)
#     # =======================================================
#     @async_retry(retries=3, backoff_factor=1.5)
#     async def fetch_generation(
#         self, bidding_zone: str, start: datetime, end: datetime
#     ) -> List[GenerationRecord]:
#         """Fetches Generation per Production Type (MW) for a specified zone."""
#         logger.info("Fetching Generation Mix", zone=bidding_zone, start=start.isoformat(), end=end.isoformat())

#         df: pd.DataFrame = await asyncio.to_thread(
#             self._sync_client.query_generation,
#             country_code=bidding_zone.upper(),
#             start=pd.Timestamp(start),
#             end=pd.Timestamp(end),
#         )

#         records = []
#         for timestamp, row in df.iterrows():
#             # Map standard ENTSO-E columns to schema fields with default 0.0
#             solar = row.get("Solar", 0.0)
#             wind_onshore = row.get("Wind Onshore", 0.0)
#             wind_offshore = row.get("Wind Offshore", 0.0)
#             gas = row.get("Fossil Gas", 0.0)
#             coal = row.get("Fossil Hard coal", 0.0)
#             nuclear = row.get("Nuclear", 0.0)

#             records.append(
#                 GenerationRecord(
#                     timestamp=timestamp,
#                     bidding_zone=bidding_zone,
#                     solar_mw=float(solar) if pd.notna(solar) else 0.0,
#                     wind_onshore_mw=float(wind_onshore) if pd.notna(wind_onshore) else 0.0,
#                     wind_offshore_mw=float(wind_offshore) if pd.notna(wind_offshore) else 0.0,
#                     gas_mw=float(gas) if pd.notna(gas) else 0.0,
#                     hard_coal_mw=float(coal) if pd.notna(coal) else 0.0,
#                     nuclear_mw=float(nuclear) if pd.notna(nuclear) else 0.0,
#                 )
#             )

#         logger.info("Successfully fetched Generation Mix", zone=bidding_zone, count=len(records))
#         return records


import asyncio
import pandas as pd
from datetime import datetime
from typing import List, Optional
from entsoe import EntsoePandasClient

from config.settings import settings
from src.energy_data_engine.utils.logger import logger
from src.energy_data_engine.utils.retry import async_retry
from src.energy_data_engine.models.schemas import (
    DayAheadPriceRecord,
    TotalLoadRecord,
    GenerationRecord,
)


class AsyncEntsoeClient:
    """Asynchronous client wrapper for ENTSO-E Transparency API using entsoe-py."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.ENTSOE_API_KEY
        if not self.api_key:
            logger.warning("ENTSOE_API_KEY is not set. API requests will fail if unmocked.")
        self._sync_client = EntsoePandasClient(api_key=self.api_key)
        self.zone_config = settings.load_zone_config()

    def _get_eic(self, zone_code: str) -> str:
        """Helper to fetch EIC code for a bidding zone."""
        zone_info = self.zone_config.get("bidding_zones", {}).get(zone_code.upper())
        if not zone_info:
            raise ValueError(f"Unknown bidding zone: {zone_code}. Defined zones: {list(self.zone_config.get('bidding_zones', {}).keys())}")
        return zone_info["eic"]

    def _format_timestamp(self, dt: datetime) -> pd.Timestamp:
        """Ensures timestamps are localized to Europe/Brussels for ENTSO-E API requirements."""
        ts = pd.Timestamp(dt)
        if ts.tz is None:
            return ts.tz_localize("Europe/Brussels")
        return ts.tz_convert("Europe/Brussels")

    # =======================================================
    # 1. Day-Ahead Prices (DocumentType: A44)
    # =======================================================
    @async_retry(retries=3, backoff_factor=1.5)
    async def fetch_day_ahead_prices(
        self, bidding_zone: str, start: datetime, end: datetime
    ) -> List[DayAheadPriceRecord]:
        """Fetches Day-Ahead Electricity Prices (€/MWh) for a specified zone."""
        logger.info("Fetching Day-Ahead Prices", zone=bidding_zone, start=start.isoformat(), end=end.isoformat())

        def _fetch():
            return self._sync_client.query_day_ahead_prices(
                country_code=bidding_zone.upper(),
                start=self._format_timestamp(start),
                end=self._format_timestamp(end),
            )

        df: pd.Series = await asyncio.to_thread(_fetch)

        if df is None or (isinstance(df, (pd.Series, pd.DataFrame)) and df.empty):
            return []

        records = []
        for timestamp, price in df.items():
            if pd.isna(price):
                continue
            ts_utc = pd.to_datetime(timestamp).tz_convert("UTC")
            record = DayAheadPriceRecord(
                timestamp=ts_utc,
                bidding_zone=bidding_zone,
                price_eur_mwh=float(price),
            )
            records.append(record)

        logger.info("Successfully fetched Day-Ahead Prices", zone=bidding_zone, count=len(records))
        return records

    # =======================================================
    # 2. Total Load / Grid Demand (DocumentType: A65)
    # =======================================================
    @async_retry(retries=3, backoff_factor=1.5)
    async def fetch_total_load(
        self, bidding_zone: str, start: datetime, end: datetime
    ) -> List[TotalLoadRecord]:
        """Fetches Actual Grid Demand / Load (MW) for a specified zone."""
        logger.info("Fetching Total Load", zone=bidding_zone, start=start.isoformat(), end=end.isoformat())

        def _fetch():
            return self._sync_client.query_load(
                country_code=bidding_zone.upper(),
                start=self._format_timestamp(start),
                end=self._format_timestamp(end),
            )

        df: pd.DataFrame | pd.Series = await asyncio.to_thread(_fetch)

        if df is None or (isinstance(df, (pd.Series, pd.DataFrame)) and df.empty):
            return []

        series = df["Actual Load"] if isinstance(df, pd.DataFrame) and "Actual Load" in df.columns else df

        records = []
        for timestamp, load in series.items():
            if pd.isna(load):
                continue
            ts_utc = pd.to_datetime(timestamp).tz_convert("UTC")
            records.append(
                TotalLoadRecord(
                    timestamp=ts_utc,
                    bidding_zone=bidding_zone,
                    load_mw=float(load),
                )
            )

        logger.info("Successfully fetched Total Load", zone=bidding_zone, count=len(records))
        return records

    # =======================================================
    # 3. Actual Generation per Production Type (DocumentType: A75)
    # =======================================================
    @async_retry(retries=3, backoff_factor=1.5)
    async def fetch_generation(
        self, bidding_zone: str, start: datetime, end: datetime
    ) -> List[GenerationRecord]:
        """Fetches Generation per Production Type (MW) for a specified zone."""
        logger.info("Fetching Generation Mix", zone=bidding_zone, start=start.isoformat(), end=end.isoformat())

        def _fetch():
            return self._sync_client.query_generation(
                country_code=bidding_zone.upper(),
                start=self._format_timestamp(start),
                end=self._format_timestamp(end),
                psr_type=None,
            )

        df: pd.DataFrame = await asyncio.to_thread(_fetch)

        if df is None or df.empty:
            return []

        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [
                c[0] if isinstance(c, tuple) else c for c in df.columns
            ]

        records = []
        for timestamp, row in df.iterrows():
            ts_utc = pd.to_datetime(timestamp).tz_convert("UTC")

            def get_val(col_key: str) -> float:
                """Search column names flexibly for fuel type matches."""
                matching_cols = [
                    col for col in df.columns if col_key.lower() in str(col).lower()
                ]
                if matching_cols:
                    val = row[matching_cols[0]]
                    if isinstance(val, pd.Series):
                        val = val.iloc[0]
                    return float(val) if pd.notna(val) else 0.0
                return 0.0

            records.append(
                GenerationRecord(
                    timestamp=ts_utc,
                    bidding_zone=bidding_zone,
                    solar_mw=get_val("solar"),
                    wind_onshore_mw=get_val("wind onshore"),
                    wind_offshore_mw=get_val("wind offshore"),
                    gas_mw=get_val("gas"),
                    hard_coal_mw=get_val("coal"),
                    nuclear_mw=get_val("nuclear"),
                )
            )

        logger.info("Successfully fetched Generation Mix", zone=bidding_zone, count=len(records))
        return records