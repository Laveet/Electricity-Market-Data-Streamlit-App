"""Baseline 'own forecast' model: a transparent seasonal-naive forecaster.

This is a deliberately simple, explainable benchmark model -- the same kind of
naive/seasonal baseline forecasting practitioners use to judge whether a "real"
model (or a published reference such as ENTSO-E's own day-ahead load forecast)
is actually adding value. It works for any hourly quantity (load, price, ...)
via `value_col`. It never looks at data on or after the target date, so a
backtest for a past date reflects only what the model could plausibly have
known at the time.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd


@dataclass
class SeasonalNaiveForecaster:
    """Forecasts an hourly quantity using a same-hour / same-weekday historical average.

    For each target hour, the forecast is the mean of `value_col` observed at the
    same hour-of-day and day-of-week over the trailing `lookback_weeks` weeks of
    history strictly before the target date. Falls back to an hour-of-day-only
    average (ignoring weekday) when there isn't enough same-weekday history, and
    to an overall mean as a last resort.
    """

    lookback_weeks: int = 8

    def forecast(
        self,
        history_df: pd.DataFrame,
        target_date: date,
        zone_timezone: str = "UTC",
        value_col: str = "load_mw",
        timestamp_col: str = "timestamp",
    ) -> pd.DataFrame:
        """Builds an hourly forecast for `target_date` (a calendar day in `zone_timezone`).

        Args:
            history_df: Historical actual records (must include `timestamp_col` and
                `value_col`) -- e.g. actual load, or the settled day-ahead price. Rows
                on or after the target day's local start are ignored, so passing in
                extra recent data is safe -- no leakage.
            target_date: The calendar date to forecast, interpreted in `zone_timezone`.
            zone_timezone: IANA timezone name the bidding zone's calendar day is defined in.
            value_col: Column holding the historical actual values to learn the profile from.
            timestamp_col: Column holding UTC timestamps.

        Returns:
            DataFrame with columns [timestamp (UTC), own_forecast] covering the
            24 local hours of `target_date`.
        """
        day_start_local = pd.Timestamp(target_date, tz=zone_timezone)
        day_start_utc = day_start_local.tz_convert("UTC")
        day_end_utc = (day_start_local + pd.Timedelta(days=1)).tz_convert("UTC")

        target_hours = pd.date_range(start=day_start_utc, end=day_end_utc, freq="1h", inclusive="left")

        if history_df is None or history_df.empty:
            return pd.DataFrame({"timestamp": target_hours, "own_forecast": np.nan})

        hist = history_df.copy()
        hist[timestamp_col] = pd.to_datetime(hist[timestamp_col], utc=True)

        # Strictly exclude anything on/after the target day to avoid leakage, and
        # cap how far back we look so old regime shifts don't dilute the profile.
        lookback_start = day_start_utc - pd.Timedelta(weeks=self.lookback_weeks)
        hist = hist[(hist[timestamp_col] < day_start_utc) & (hist[timestamp_col] >= lookback_start)]

        if hist.empty:
            return pd.DataFrame({"timestamp": target_hours, "own_forecast": np.nan})

        hist_local = hist[timestamp_col].dt.tz_convert(zone_timezone)
        hist = hist.assign(_hour=hist_local.dt.hour, _weekday=hist_local.dt.weekday)

        by_hour_weekday = hist.groupby(["_weekday", "_hour"])[value_col].mean()
        by_hour = hist.groupby("_hour")[value_col].mean()
        overall_mean = hist[value_col].mean()

        forecasts = []
        for ts_utc in target_hours:
            ts_local = ts_utc.tz_convert(zone_timezone)
            hour, weekday = ts_local.hour, ts_local.weekday()

            if (weekday, hour) in by_hour_weekday.index:
                value = by_hour_weekday.loc[(weekday, hour)]
            elif hour in by_hour.index:
                value = by_hour.loc[hour]
            else:
                value = overall_mean
            forecasts.append(value)

        return pd.DataFrame({"timestamp": target_hours, "own_forecast": forecasts})
