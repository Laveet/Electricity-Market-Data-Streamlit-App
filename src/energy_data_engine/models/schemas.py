from datetime import datetime, timezone
from typing import Optional, Dict
from pydantic import BaseModel, Field, field_validator, model_validator


# ==========================================
# Base Schema with UTC & Null Field Parsing
# ==========================================
class BaseEnergyRecord(BaseModel):
    """Base model enforcing UTC timezone conversion and standard validation rules."""

    timestamp: datetime = Field(..., description="Observation timestamp in UTC")
    bidding_zone: str = Field(..., description="Bidding Zone EIC or Code (e.g., DE_LU, FR, NL)")

    @field_validator("timestamp", mode="before")
    @classmethod
    def enforce_utc_timestamp(cls, value: datetime) -> datetime:
        """Converts any datetime (including DST-aware strings/objects) to normalized UTC."""
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        if value.tzinfo is None:
            # Assume naive datetime is already UTC
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @field_validator("bidding_zone", mode="before")
    @classmethod
    def uppercase_zone(cls, value: str) -> str:
        """Ensures bidding zone string is normalized to uppercase."""
        return value.strip().upper()


# ==========================================
# 1. Day-Ahead Price Schema ($A44$)
# ==========================================
class DayAheadPriceRecord(BaseEnergyRecord):
    """Schema for Day-Ahead Wholesale Electricity Prices (€/MWh)."""

    price_eur_mwh: float = Field(
        ...,
        ge=-500.0,
        le=4000.0,
        description="Day-ahead market price in EUR/MWh (allows negative prices)"
    )

    @field_validator("price_eur_mwh", mode="before")
    @classmethod
    def parse_missing_price(cls, value: str | float | None) -> float:
        """Handles NaN or None values in price streams."""
        if value is None or str(value).lower() in ("nan", "null", "none", ""):
            raise ValueError("Price cannot be None or NaN")
        return float(value)


# ==========================================
# 2. Intraday Price & Volume Schema ($A44$/$A07$/VWAP)
# ==========================================
class IntradayPriceRecord(BaseEnergyRecord):
    """Schema for Intraday Continuous Market Prices & Volume Weighted Average Price (VWAP)."""

    vwap_eur_mwh: float = Field(
        ...,
        ge=-500.0,
        le=4000.0,
        description="Volume Weighted Average Price in EUR/MWh"
    )
    volume_mw: float = Field(
        ...,
        ge=0.0,
        description="Total traded volume in MW (must be non-negative)"
    )

    @field_validator("volume_mw", mode="before")
    @classmethod
    def parse_missing_volume(cls, value: str | float | None) -> float:
        """Parses missing volume data defaulting to 0.0 if omitted."""
        if value is None or str(value).lower() in ("nan", "null", "none", ""):
            return 0.0
        return float(value)


# ==========================================
# 3. Total Load Schema ($A65$)
# ==========================================
class TotalLoadRecord(BaseEnergyRecord):
    """Schema for Grid Demand / Total Electricity Load (MW)."""

    load_mw: float = Field(
        ...,
        ge=0.0,
        description="Actual total load in MW"
    )


# ==========================================
# 4. Actual Generation per Production Type Schema ($A75$)
# ==========================================
class GenerationRecord(BaseEnergyRecord):
    """Schema for Actual Generation per Production Type (MW)."""

    solar_mw: float = Field(default=0.0, ge=0.0, description="Solar PV Generation in MW")
    wind_onshore_mw: float = Field(default=0.0, ge=0.0, description="Wind Onshore Generation in MW")
    wind_offshore_mw: float = Field(default=0.0, ge=0.0, description="Wind Offshore Generation in MW")
    gas_mw: float = Field(default=0.0, ge=0.0, description="Natural Gas Thermal Generation in MW")
    hard_coal_mw: float = Field(default=0.0, ge=0.0, description="Hard Coal Generation in MW")
    nuclear_mw: float = Field(default=0.0, ge=0.0, description="Nuclear Power Generation in MW")

    @property
    def total_renewable_mw(self) -> float:
        """Calculates total variable renewable power generation (Solar + Wind)."""
        return self.solar_mw + self.wind_onshore_mw + self.wind_offshore_mw


# ==========================================
# 5. Combined Consolidated Market Record
# ==========================================
class ConsolidatedMarketRecord(BaseEnergyRecord):
    """Unified schema representing a clean hourly snapshot across all ingested metrics."""

    day_ahead_price: Optional[float] = None
    intraday_vwap: Optional[float] = None
    total_load: Optional[float] = None
    solar: float = 0.0
    wind_onshore: float = 0.0
    wind_offshore: float = 0.0
    gas: float = 0.0
    coal: float = 0.0