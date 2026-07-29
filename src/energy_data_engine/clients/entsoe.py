


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
    GenerationRecord,IntradayPriceRecord,
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
    @async_retry(retries=3, backoff_factor=1.5)
    async def fetch_intraday_prices(
        self, bidding_zone: str, start: datetime, end: datetime
    ) -> List[IntradayPriceRecord]:
        """Fetches Intraday Continuous Market VWAP (€/MWh) and Traded Volume (MW)."""
        logger.info(
            "Fetching Intraday Continuous Data",
            zone=bidding_zone,
            start=start.isoformat(),
            end=end.isoformat(),
        )

        def _fetch():
            # entsoe-py returns a DataFrame with price / volume data
            return self._sync_client.query_intraday_prices(
                country_code=bidding_zone.upper(),
                start=self._format_timestamp(start),
                end=self._format_timestamp(end),
            )

        try:
            df = await asyncio.to_thread(_fetch)
        except Exception as e:
            logger.error(
                "Error fetching intraday data",
                error=str(e),
                zone=bidding_zone,
            )
            return []

        if df is None or (
            isinstance(df, (pd.Series, pd.DataFrame)) and df.empty
        ):
            return []

        records = []

        # If entsoe-py returns a Series (Price only)
        if isinstance(df, pd.Series):
            for timestamp, price in df.items():
                if pd.isna(price):
                    continue
                records.append(
                    IntradayPriceRecord(
                        timestamp=pd.to_datetime(timestamp).tz_convert("UTC"),
                        bidding_zone=bidding_zone,
                        vwap_eur_mwh=float(price),
                        volume_mw=0.0,
                    )
                )

        # If entsoe-py returns a DataFrame (Price + Volume columns)
        elif isinstance(df, pd.DataFrame):
            # Resolve column names dynamically
            price_col = next(
                (
                    c
                    for c in df.columns
                    if "price" in str(c).lower() or "vwap" in str(c).lower()
                ),
                df.columns[0],
            )
            vol_col = next(
                (c for c in df.columns if "volume" in str(c).lower()), None
            )

            for timestamp, row in df.iterrows():
                price_val = row[price_col]
                vol_val = row[vol_col] if vol_col else 0.0

                if pd.isna(price_val):
                    continue

                records.append(
                    IntradayPriceRecord(
                        timestamp=pd.to_datetime(timestamp).tz_convert("UTC"),
                        bidding_zone=bidding_zone,
                        vwap_eur_mwh=float(price_val),
                        volume_mw=vol_val,  # Your validator handles NaN / string defaults automatically
                    )
                )

        logger.info(
            "Successfully fetched Intraday Records",
            zone=bidding_zone,
            count=len(records),
        )
        return records