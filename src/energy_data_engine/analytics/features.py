# from typing import Dict, Any, Tuple
# import pandas as pd
# import numpy as np

# class AdditionalAnalyticsFeatures:
#     """
#     Modular analytics calculator for energy market KPIs, 
#     price metrics, and visualization structures.
#     """

#     @staticmethod
#     def calculate_total_solar_generation(df: pd.DataFrame) -> float:
#         """Calculates total solar generation (MWh) across the selected timeframe."""
#         if "solar_mw" in df.columns:
#             # Assuming hourly granularity (1 MW over 1h = 1 MWh)
#             return float(df["solar_mw"].fillna(0).sum())
#         return 0.0

#     @staticmethod
#     def calculate_total_wind_generation(df: pd.DataFrame) -> Tuple[float, float, float]:
#         """
#         Calculates total wind generation (MWh).
#         Returns: (total_wind, wind_onshore, wind_offshore)
#         """
#         wind_on = df["wind_onshore_mw"].fillna(0).sum() if "wind_onshore_mw" in df.columns else 0.0
#         wind_off = df["wind_offshore_mw"].fillna(0).sum() if "wind_offshore_mw" in df.columns else 0.0
#         total_wind = float(wind_on + wind_off)
#         return total_wind, float(wind_on), float(wind_off)

#     @staticmethod
#     def calculate_renewable_share(df: pd.DataFrame) -> float:
#         """Calculates overall share of renewable generation (%)."""
#         renewable_cols = [
#             c for c in ["solar_mw", "wind_onshore_mw", "wind_offshore_mw", "hydro_mw", "biomass_mw", "geothermal_mw"]
#             if c in df.columns
#         ]
        
#         # If total generation columns or load exist
#         if renewable_cols:
#             total_renewable = df[renewable_cols].fillna(0).sum().sum()
            
#             # Find total generation across all available fuel columns
#             gen_cols = [c for c in df.columns if c.endswith("_mw") and c not in ["load_mw", "residual_load_mw"]]
#             total_gen = df[gen_cols].fillna(0).sum().sum() if gen_cols else 0.0

#             if total_gen > 0:
#                 return float((total_renewable / total_gen) * 100.0)
#         return 0.0

#     @staticmethod
#     def calculate_total_volume(df: pd.DataFrame) -> float:
#         """Calculates total energy volume (MWh) recorded in the selected period."""
#         if "load_mw" in df.columns:
#             return float(df["load_mw"].fillna(0).sum())
#         elif "volume_mwh" in df.columns:
#             return float(df["volume_mwh"].fillna(0).sum())
#         return 0.0

#     @staticmethod
#     def calculate_base_and_peak_prices(df: pd.DataFrame, price_col: str = "price_eur_mwh", time_col: str = "timestamp") -> Tuple[float, float]:
#         """
#         Calculates Base Average Price (00:00-24:00) and Peak Average Price (08:00-20:00).
#         """
#         if price_col not in df.columns:
#             return 0.0, 0.0

#         base_price = float(df[price_col].mean()) if not df.empty else 0.0

#         # Peak hours calculation (08:00 to 20:00 local/UTC)
#         if time_col in df.columns:
#             df_temp = df.copy()
#             df_temp[time_col] = pd.to_datetime(df_temp[time_col])
#             peak_mask = (df_temp[time_col].dt.hour >= 8) & (df_temp[time_col].dt.hour < 20)
#             peak_price = float(df_temp.loc[peak_mask, price_col].mean()) if peak_mask.any() else 0.0
#         else:
#             peak_price = 0.0

#         return base_price, peak_price

#     @staticmethod
#     def calculate_price_volatility_metrics(df: pd.DataFrame, price_col: str = "price_eur_mwh") -> Dict[str, float]:
#         """Calculates price volatility metrics (Standard Deviation, Min-Max Spread)."""
#         if price_col not in df.columns or df[price_col].dropna().empty:
#             return {"std_dev": 0.0, "price_spread": 0.0, "iqr": 0.0}

#         prices = df[price_col].dropna()
#         std_dev = float(prices.std())
#         price_spread = float(prices.max() - prices.min())
#         iqr = float(prices.quantile(0.75) - prices.quantile(0.25))

#         return {
#             "std_dev": std_dev,
#             "price_spread": price_spread,
#             "iqr": iqr
#         }

from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np


class AdditionalAnalyticsFeatures:
    """
    Modular analytics calculator for energy market KPIs, 
    price metrics, daily price trends, and visualization structures.
    """

    @staticmethod
    def calculate_total_solar_generation(df: pd.DataFrame) -> float:
        """Calculates total solar generation (MWh) across the selected timeframe."""
        if "solar_mw" in df.columns:
            return float(df["solar_mw"].fillna(0).sum())
        return 0.0

    @staticmethod
    def calculate_total_wind_generation(df: pd.DataFrame) -> Tuple[float, float, float]:
        """
        Calculates total wind generation (MWh).
        Returns: (total_wind, wind_onshore, wind_offshore)
        """
        wind_on = df["wind_onshore_mw"].fillna(0).sum() if "wind_onshore_mw" in df.columns else 0.0
        wind_off = df["wind_offshore_mw"].fillna(0).sum() if "wind_offshore_mw" in df.columns else 0.0
        total_wind = float(wind_on + wind_off)
        return total_wind, float(wind_on), float(wind_off)

    @staticmethod
    def calculate_renewable_share(df: pd.DataFrame) -> float:
        """Calculates overall share of renewable generation (%)."""
        renewable_cols = [
            c for c in ["solar_mw", "wind_onshore_mw", "wind_offshore_mw", "hydro_mw", "biomass_mw", "geothermal_mw"]
            if c in df.columns
        ]
        
        if renewable_cols:
            total_renewable = df[renewable_cols].fillna(0).sum().sum()
            gen_cols = [c for c in df.columns if c.endswith("_mw") and c not in ["load_mw", "residual_load_mw"]]
            total_gen = df[gen_cols].fillna(0).sum().sum() if gen_cols else 0.0

            if total_gen > 0:
                return float((total_renewable / total_gen) * 100.0)
        return 0.0

    @staticmethod
    def calculate_total_volume(df: pd.DataFrame) -> float:
        """Calculates total energy volume (MWh) recorded in the selected period."""
        if "load_mw" in df.columns:
            return float(df["load_mw"].fillna(0).sum())
        elif "volume_mwh" in df.columns:
            return float(df["volume_mwh"].fillna(0).sum())
        return 0.0

    @staticmethod
    def calculate_base_and_peak_prices(df: pd.DataFrame, price_col: str = "price_eur_mwh", time_col: str = "timestamp") -> Tuple[float, float]:
        """
        Calculates Overall Base Average Price (00:00-24:00) and Peak Average Price (08:00-20:00).
        """
        if price_col not in df.columns or df.empty:
            return 0.0, 0.0

        base_price = float(df[price_col].mean())

        if time_col in df.columns:
            df_temp = df.copy()
            df_temp[time_col] = pd.to_datetime(df_temp[time_col])
            peak_mask = (df_temp[time_col].dt.hour >= 8) & (df_temp[time_col].dt.hour < 20)
            peak_price = float(df_temp.loc[peak_mask, price_col].mean()) if peak_mask.any() else 0.0
        else:
            peak_price = 0.0

        return base_price, peak_price

    @staticmethod
    def calculate_daily_base_peak_prices(df: pd.DataFrame, price_col: str = "price_eur_mwh", time_col: str = "timestamp") -> pd.DataFrame:
        """
        Groups price data by day and computes Daily Base Price and Daily Peak Price for line charting.
        """
        if df.empty or price_col not in df.columns or time_col not in df.columns:
            return pd.DataFrame(columns=["date", "base_price", "peak_price"])

        df_temp = df.copy()
        df_temp[time_col] = pd.to_datetime(df_temp[time_col])
        df_temp["date"] = df_temp[time_col].dt.date
        df_temp["is_peak"] = (df_temp[time_col].dt.hour >= 8) & (df_temp[time_col].dt.hour < 20)

        # Calculate daily base price (all hours)
        daily_base = df_temp.groupby("date")[price_col].mean().rename("base_price")

        # Calculate daily peak price (hours 08:00 - 20:00)
        daily_peak = df_temp[df_temp["is_peak"]].groupby("date")[price_col].mean().rename("peak_price")

        daily_df = pd.concat([daily_base, daily_peak], axis=1).reset_index()
        daily_df["date"] = pd.to_datetime(daily_df["date"])
        return daily_df

    @staticmethod
    def calculate_price_volatility_metrics(df: pd.DataFrame, price_col: str = "price_eur_mwh") -> Dict[str, float]:
        """Calculates price volatility metrics (Standard Deviation, Min-Max Spread)."""
        if price_col not in df.columns or df[price_col].dropna().empty:
            return {"std_dev": 0.0, "price_spread": 0.0, "iqr": 0.0}

        prices = df[price_col].dropna()
        std_dev = float(prices.std())
        price_spread = float(prices.max() - prices.min())
        iqr = float(prices.quantile(0.75) - prices.quantile(0.25))

        return {
            "std_dev": std_dev,
            "price_spread": price_spread,
            "iqr": iqr
        }