import pandas as pd


class SpreadCalculators:
    """Quantitative feature transformations for cross-border and thermal generator spreads."""

    @staticmethod
    def calculate_cross_border_spread(
        df_zone_a: pd.DataFrame,
        df_zone_b: pd.DataFrame,
        zone_a_name: str,
        zone_b_name: str,
        price_col: str = "price_eur_mwh",
    ) -> pd.DataFrame:
        """Calculates Cross-Border Price Spread = Price(Zone A) - Price(Zone B).
        
        Identifies spatial arbitrage opportunities and cross-border power flow directions.
        """
        # Ensure timestamp alignment
        a_df = df_zone_a[["timestamp", price_col]].rename(columns={price_col: f"price_{zone_a_name}"})
        b_df = df_zone_b[["timestamp", price_col]].rename(columns={price_col: f"price_{zone_b_name}"})

        merged = pd.merge(a_df, b_df, on="timestamp", how="inner")
        spread_col = f"spread_{zone_a_name}_{zone_b_name}_eur_mwh"
        merged[spread_col] = merged[f"price_{zone_a_name}"] - merged[f"price_{zone_b_name}"]

        return merged

    @staticmethod
    def calculate_clean_spark_spread(
        power_price: pd.Series | float,
        gas_price: pd.Series | float,
        carbon_price: pd.Series | float,
        efficiency: float = 0.50,
        emission_factor: float = 0.202,
    ) -> pd.Series | float:
        """Calculates Clean Spark Spread (CSS) for gas-fired power plant profitability.
        
        Formula:
            CSS = Power Price - (Gas Price / Efficiency) - (Carbon Price * Emission Factor)
        """
        fuel_cost = gas_price / efficiency
        carbon_cost = carbon_price * emission_factor
        return power_price - fuel_cost - carbon_cost

    @staticmethod
    def calculate_clean_dark_spread(
        power_price: pd.Series | float,
        coal_price: pd.Series | float,
        carbon_price: pd.Series | float,
        efficiency: float = 0.38,
        emission_factor: float = 0.340,
    ) -> pd.Series | float:
        """Calculates Clean Dark Spread (CDS) for coal-fired power plant profitability.
        
        Formula:
            CDS = Power Price - (Coal Price / Efficiency) - (Carbon Price * Emission Factor)
        """
        fuel_cost = coal_price / efficiency
        carbon_cost = carbon_price * emission_factor
        return power_price - fuel_cost - carbon_cost