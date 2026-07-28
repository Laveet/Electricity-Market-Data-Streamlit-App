# # src/energy_data_engine/features/metrics.py

# import pandas as pd
# import numpy as np
# from typing import Dict, List, Optional


# class FundamentalMetrics:
#     """
#     Calculates quantitative metrics for European wholesale electricity markets.
#     Designed to process merged DataFrames containing price, load, and generation data.
#     """

#     RENEWABLE_COLUMNS = [
#         "Solar",
#         "Wind Onshore",
#         "Wind Offshore",
#         "Hydro Run-of-river and poundage",
#     ]

#     @staticmethod
#     def calculate_residual_load(
#         df: pd.DataFrame,
#         load_col: str = "load_mw",
#         renewable_cols: Optional[List[str]] = None,
#     ) -> pd.DataFrame:
#         """
#         Calculates Residual Load = Total Load - Variable Renewable Energy (Solar + Wind Onshore + Wind Offshore)
#         """
#         result_df = df.copy()

#         if renewable_cols is None:
#             renewable_cols = ["Solar", "Wind Onshore", "Wind Offshore"]

#         # Filter cols present in DataFrame
#         existing_ren_cols = [c for c in renewable_cols if c in result_df.columns]

#         if existing_ren_cols and load_col in result_df.columns:
#             total_vre = result_df[existing_ren_cols].sum(axis=1)
#             result_df["total_vre_mw"] = total_vre
#             result_df["residual_load_mw"] = result_df[load_col] - total_vre
#         elif load_col in result_df.columns:
#             result_df["total_vre_mw"] = 0.0
#             result_df["residual_load_mw"] = result_df[load_col]
#         else:
#             result_df["total_vre_mw"] = np.nan
#             result_df["residual_load_mw"] = np.nan

#         return result_df

#     @staticmethod
#     def calculate_capture_prices(
#         df: pd.DataFrame,
#         price_col: str = "price_eur_mwh",
#         gen_cols: Optional[List[str]] = None,
#     ) -> Dict[str, float]:
#         """
#         Calculates Volume-Weighted Capture Price (€/MWh) per generation technology.
#         Capture Price = Sum(Price * Generation_tech) / Sum(Generation_tech)
#         """
#         if price_col not in df.columns:
#             return {}

#         if gen_cols is None:
#             gen_cols = [
#                 "Solar",
#                 "Wind Onshore",
#                 "Wind Offshore",
#                 "Nuclear",
#                 "Fossil Hard coal",
#                 "Fossil Gas",
#             ]

#         capture_prices = {}
#         for tech in gen_cols:
#             if tech in df.columns:
#                 valid_mask = df[price_col].notna() & df[tech].notna()
#                 total_gen = df.loc[valid_mask, tech].sum()

#                 if total_gen > 0:
#                     weighted_rev = (
#                         df.loc[valid_mask, price_col] * df.loc[valid_mask, tech]
#                     ).sum()
#                     capture_prices[tech] = round(weighted_rev / total_gen, 2)
#                 else:
#                     capture_prices[tech] = np.nan

#         return capture_prices

#     @staticmethod
#     def calculate_renewable_penetration(
#         df: pd.DataFrame, load_col: str = "load_mw"
#     ) -> pd.Series:
#         """
#         Calculates Renewable Penetration (%) relative to total load.
#         """
#         existing_ren_cols = [
#             c for c in FundamentalMetrics.RENEWABLE_COLUMNS if c in df.columns
#         ]

#         if existing_ren_cols and load_col in df.columns:
#             ren_total = df[existing_ren_cols].sum(axis=1)
#             penetration = (ren_total / df[load_col].replace(0, np.nan)) * 100
#             return penetration.round(2)
#         return pd.Series(np.nan, index=df.index)

#     @staticmethod
#     def calculate_ramp_rates(
#         df: pd.DataFrame, target_col: str = "residual_load_mw"
#     ) -> pd.Series:
#         """
#         Calculates hourly ramp rate (MW/h change).
#         """
#         if target_col in df.columns:
#             return df[target_col].diff()
#         return pd.Series(np.nan, index=df.index)
import pandas as pd


class FundamentalMetrics:
    """Quantitative feature transformations for grid load, renewables, and ramping."""

    @staticmethod
    def calculate_residual_load(df: pd.DataFrame) -> pd.DataFrame:
        """Calculates Residual Load = Total Load - Total Renewable Generation (Solar + Wind Onshore + Wind Offshore).
        
        Residual load represents the demand that must be covered by dispatchable/thermal generation assets.
        """
        result = df.copy()
        
        # Calculate variable renewables sum
        renewable_cols = [col for col in ["solar_mw", "wind_onshore_mw", "wind_offshore_mw"] if col in result.columns]
        result["total_renewable_mw"] = result[renewable_cols].sum(axis=1) if renewable_cols else 0.0

        if "load_mw" in result.columns:
            result["residual_load_mw"] = result["load_mw"] - result["total_renewable_mw"]
        else:
            result["residual_load_mw"] = None

        return result

    @staticmethod
    def calculate_renewable_penetration(df: pd.DataFrame) -> pd.DataFrame:
        """Calculates Renewable Penetration Rate (%) = (Total Renewable MW / Total Load MW) * 100."""
        result = FundamentalMetrics.calculate_residual_load(df)
        
        if "load_mw" in result.columns and "total_renewable_mw" in result.columns:
            result["renewable_penetration_pct"] = (
                (result["total_renewable_mw"] / result["load_mw"].replace(0, pd.NA)) * 100
            ).fillna(0.0)
        else:
            result["renewable_penetration_pct"] = 0.0

        return result

    @staticmethod
    def calculate_ramp_rate(df: pd.DataFrame, target_col: str = "load_mw") -> pd.DataFrame:
        """Calculates hourly ramp rate (MW/h acceleration/deceleration) for a target metric."""
        result = df.copy()
        if target_col in result.columns:
            result[f"{target_col}_ramp_mw_h"] = result[target_col].diff().fillna(0.0)
        return result