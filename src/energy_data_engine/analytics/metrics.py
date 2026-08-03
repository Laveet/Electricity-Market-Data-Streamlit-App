
import pandas as pd
import numpy as np


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
    ########Adding further features+#####
    @staticmethod
    def calculate_renewable_penetration(df: pd.DataFrame) -> pd.DataFrame:
        """Calculates total renewables, residual load, and penetration percentage."""
        df_calc = df.copy()

        expected_cols = ["solar_mw", "wind_onshore_mw", "wind_offshore_mw", "load_mw"]
        for col in expected_cols:
            if col not in df_calc.columns:
                df_calc[col] = 0.0

        df_calc["renewable_total_mw"] = (
            df_calc["solar_mw"] + 
            df_calc["wind_onshore_mw"] + 
            df_calc["wind_offshore_mw"]
        )
        df_calc["residual_load_mw"] = df_calc["load_mw"] - df_calc["renewable_total_mw"]

        df_calc["renewable_penetration_pct"] = 0.0
        mask = df_calc["load_mw"] > 0
        df_calc.loc[mask, "renewable_penetration_pct"] = (
            (df_calc.loc[mask, "renewable_total_mw"] / df_calc.loc[mask, "load_mw"]) * 100
        )

        return df_calc

    @staticmethod
    def calculate_negative_price_stats(df: pd.DataFrame, price_col: str = "price_eur_mwh"): 
        """Calculates count and percentage frequency of negative market prices."""
        if df.empty or price_col not in df.columns:
            return {"neg_hours": 0, "total_hours": 0, "neg_frequency_pct": 0.0}

        total_hours = len(df)
        neg_hours = int((df[price_col] < 0).sum())
        freq_pct = (neg_hours / total_hours * 100) if total_hours > 0 else 0.0

        return {
            "neg_hours": neg_hours,
            "total_hours": total_hours,
            "neg_frequency_pct": round(freq_pct, 2)
        }

    @staticmethod
    def calculate_capture_prices(df: pd.DataFrame, price_col: str = "price_eur_mwh"):
        """
        Calculates Baseload Price, Renewable Volume-Weighted Capture Prices (VWAP),
        and Capture Factors per renewable asset class.
        """
        if df.empty or price_col not in df.columns:
            return {}

        baseload = df[price_col].mean()
        metrics = {"baseload_price_eur": round(baseload, 2)}

        tech_mapping = {
            "solar": "solar_mw",
            "wind_onshore": "wind_onshore_mw",
            "wind_offshore": "wind_offshore_mw"
        }

        for tech, col in tech_mapping.items():
            if col in df.columns and df[col].sum() > 0:
                total_gen = df[col].sum()
                vwap = (df[col] * df[price_col]).sum() / total_gen
                capture_factor = (vwap / baseload) if baseload != 0 else 0.0

                metrics[f"{tech}_capture_price"] = round(vwap, 2)
                metrics[f"{tech}_capture_factor"] = round(capture_factor, 3)
            else:
                metrics[f"{tech}_capture_price"] = 0.0
                metrics[f"{tech}_capture_factor"] = 0.0

        return metrics

    @staticmethod
    def calculate_residual_load_price_correlation(
        df: pd.DataFrame, 
        price_col: str = "price_eur_mwh", 
        residual_col: str = "residual_load_mw"
    ) -> float:
        """Calculates Pearson correlation between Residual Net Load and Day-Ahead Price."""
        if df.empty or price_col not in df.columns or residual_col not in df.columns:
            return 0.0
        
        corr = df[residual_col].corr(df[price_col])
        return round(corr, 3) if not np.isnan(corr) else 0.0