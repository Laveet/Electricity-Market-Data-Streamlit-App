# import asyncio
# import io
# import sys
# from datetime import date, datetime, timedelta, timezone
# from pathlib import Path

# import pandas as pd
# import plotly.express as px
# import streamlit as st

# # Add src to system path for imports
# sys.path.append(str(Path(__file__).resolve().parent / "src"))

# from src.energy_data_engine.analytics.metrics import FundamentalMetrics
# from src.energy_data_engine.analytics.spreads import SpreadCalculators
# from src.energy_data_engine.analytics.features import AdditionalAnalyticsFeatures
# from src.energy_data_engine.pipeline import EnergyDataPipeline
# from src.energy_data_engine.storage.duck_analytics import DuckDBAnalyticsEngine

# # Page Configuration
# st.set_page_config(
#     page_title="European Energy Data & Analytics Engine",
#     page_icon="⚡",
#     layout="wide",
# )

# st.title("⚡ European Energy Market Data Engine")
# st.markdown("Real-time Power Market Analytics, Lakehouse Storage & Quantitative Feature Explorer")

# # Initialize DuckDB Analytics Engine
# analytics = DuckDBAnalyticsEngine()

# # --- HELPER FUNCTIONS FOR CLEAN DATA EXPORT ---
# def generate_clean_excel_bytes(zone: str, start_dt: pd.Timestamp, end_dt: pd.Timestamp) -> bytes:
#     """Queries, deduplicates, and compiles multi-sheet Excel data in memory for Streamlit export."""
#     output = io.BytesIO()
#     s_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
#     e_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")

#     # Helper function to query DuckDB and deduplicate rows by timestamp
#     def fetch_deduped(dataset_name: str) -> pd.DataFrame:
#         dataset_path = analytics.data_dir / dataset_name
#         if not dataset_path.exists() or not list(dataset_path.glob("**/*.parquet")):
#             return pd.DataFrame()

#         query_path = str(dataset_path / "**" / "*.parquet")
#         query = f"""
#             SELECT * FROM read_parquet('{query_path}')
#             WHERE zone = '{zone}'
#               AND timestamp >= '{s_str}'
#               AND timestamp < '{e_str}'
#             QUALIFY ROW_NUMBER() OVER (PARTITION BY timestamp ORDER BY timestamp DESC) = 1
#             ORDER BY timestamp ASC
#         """
#         try:
#             return analytics.conn.execute(query).df()
#         except Exception as e:
#             st.error(f"Error fetching dataset '{dataset_name}': {e}")
#             return pd.DataFrame()

#     # Query clean, deduplicated datasets
#     df_prices = fetch_deduped("day_ahead_prices")
#     df_load = fetch_deduped("total_load")
#     df_gen = fetch_deduped("generation")

#     # Strip timezone info for Excel compatibility
#     for df in [df_prices, df_load, df_gen]:
#         if not df.empty and "timestamp" in df.columns:
#             df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)

#     # Write sheets into Excel workbook
#     with pd.ExcelWriter(output, engine="openpyxl") as writer:
#         if not df_prices.empty:
#             df_prices.to_excel(writer, sheet_name="Day Ahead Prices", index=False)
#         if not df_load.empty:
#             df_load.to_excel(writer, sheet_name="Total Load", index=False)
#         if not df_gen.empty:
#             df_gen.to_excel(writer, sheet_name="Generation Mix", index=False)

#     output.seek(0)
#     return output.getvalue()


# # Helper function to filter DataFrame by selected dates for dashboard charts
# def filter_by_date(df: pd.DataFrame, timestamp_col: str = "timestamp") -> pd.DataFrame:
#     if df.empty or timestamp_col not in df.columns:
#         return df
#     df[timestamp_col] = pd.to_datetime(df[timestamp_col], utc=True)
#     return df[(df[timestamp_col] >= start_dt) & (df[timestamp_col] < end_dt)]


# # --- SIDEBAR CONTROLS ---
# st.sidebar.header("🕹️ Market Controls")
# bidding_zone = st.sidebar.selectbox("Select Primary Bidding Zone", ["DE_LU", "FR", "NL"], index=0)

# st.sidebar.markdown("---")
# st.sidebar.subheader("📅 Date Range Filter")
# today = date.today()
# start_date = st.sidebar.date_input("Start Date", today - timedelta(days=7))
# end_date = st.sidebar.date_input("End Date", today + timedelta(days=1))

# # Convert sidebar dates to UTC datetimes for filtering & ingestion
# start_dt = pd.to_datetime(start_date).tz_localize("UTC")
# end_dt = pd.to_datetime(end_date).tz_localize("UTC") + pd.Timedelta(days=1)

# st.sidebar.markdown("---")
# st.sidebar.subheader("📡 Data Pipeline Actions")

# # Ingestion trigger
# if st.sidebar.button("🚀 Fetch & Process Market Data"):
#     with st.spinner(f"Ingesting data for selected zones ({start_date} to {end_date})..."):
#         pipeline = EnergyDataPipeline()
#         start_time = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
#         end_time = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)

#         # Run async ingestion pipeline
#         asyncio.run(
#             pipeline.run_ingestion_pipeline(
#                 bidding_zones=["DE_LU", "FR", "NL"],
#                 start=start_time,
#                 end=end_time,
#             )
#         )
#         st.sidebar.success("✅ Ingestion & Lakehouse Store Updated!")
#         st.rerun()

# st.sidebar.markdown("---")
# st.sidebar.subheader("📥 Clean Data Exporter")

# # Multi-sheet Deduplicated Excel Download
# if st.sidebar.button("📦 Prepare Clean Excel Workbook"):
#     with st.spinner("Deduplicating & compiling Excel file..."):
#         excel_bytes = generate_clean_excel_bytes(bidding_zone, start_dt, end_dt)
#         if excel_bytes:
#             st.sidebar.download_button(
#                 label="💾 Download Clean Excel (.xlsx)",
#                 data=excel_bytes,
#                 file_name=f"{bidding_zone}_clean_market_data_{start_date}_to_{end_date}.xlsx",
#                 mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#             )
#             st.sidebar.success("✅ Excel workbook generated successfully!")
#         else:
#             st.sidebar.warning("No data found to export for these dates.")


# # --- MAIN DASHBOARD TABS ---
# tab1, tab2, tab3, tab4 = st.tabs([
#     "📊 Price & Load Analytics", 
#     "🌱 Generation Mix & Residual Load", 
#     "🔄 Cross-Border Spreads",
#     "📈 Detailed Analytics & Features"
# ])

# # --- TAB 1: Day-Ahead Prices & Load ---
# with tab1:
#     st.header(f"Day-Ahead Prices ({bidding_zone})")

#     try:
#         raw_prices_df = analytics.query_dataset_by_zone("day_ahead_prices", zone=bidding_zone)
#         prices_df = filter_by_date(raw_prices_df)

#         if not prices_df.empty:
#             col1, col2, col3 = st.columns(3)
#             with col1:
#                 st.metric("Avg Day-Ahead Price", f"{prices_df['price_eur_mwh'].mean():.2f} €/MWh")
#             with col2:
#                 st.metric("Min Day-Ahead Price", f"{prices_df['price_eur_mwh'].min():.2f} €/MWh")
#             with col3:
#                 st.metric("Max Day-Ahead Price", f"{prices_df['price_eur_mwh'].max():.2f} €/MWh")

#             fig_price = px.line(
#                 prices_df,
#                 x="timestamp",
#                 y="price_eur_mwh",
#                 title=f"Day-Ahead Price Time Series ({bidding_zone})",
#                 labels={"price_eur_mwh": "Price (€/MWh)", "timestamp": "UTC Time"},
#             )
#             st.plotly_chart(fig_price, use_container_width=True)

#         else:
#             st.info(
#                 f"No price data stored for '{bidding_zone}' between {start_date} and {end_date}.\n\n"
#                 "👉 Click **'🚀 Fetch & Process Market Data'** in the sidebar to fetch and save data for this date range!"
#             )
#     except Exception as e:
#         st.warning(f"Notice: {e}")


# # --- TAB 2: Generation Mix & Residual Load ---
# with tab2:
#     st.header(f"Generation Mix & Fundamental Metrics ({bidding_zone})")
#     try:
#         raw_gen_df = analytics.query_dataset_by_zone("generation", zone=bidding_zone)
#         raw_load_df = analytics.query_dataset_by_zone("total_load", zone=bidding_zone)

#         gen_df = filter_by_date(raw_gen_df)
#         load_df = filter_by_date(raw_load_df)

#         if not gen_df.empty and not load_df.empty:
#             # Normalize timestamps for exact matching
#             gen_df["timestamp"] = pd.to_datetime(gen_df["timestamp"], utc=True)
#             load_df["timestamp"] = pd.to_datetime(load_df["timestamp"], utc=True)

#             merged = gen_df.merge(load_df[["timestamp", "load_mw"]], on="timestamp", how="inner")
            
#             if not merged.empty:
#                 metrics_df = FundamentalMetrics.calculate_renewable_penetration(merged)

#                 # Fuel Breakdown Chart
#                 gen_cols = [
#                     c for c in ["solar_mw", "wind_onshore_mw", "wind_offshore_mw", "gas_mw", "hard_coal_mw", "nuclear_mw"]
#                     if c in metrics_df.columns
#                 ]
#                 fig_gen = px.area(
#                     metrics_df,
#                     x="timestamp",
#                     y=gen_cols,
#                     title=f"Generation Breakdown (MW) - {bidding_zone}",
#                     labels={"value": "Generation (MW)", "variable": "Fuel Type"},
#                 )
#                 st.plotly_chart(fig_gen, use_container_width=True)

#                 # Total Load vs Residual Load Chart
#                 fig_res = px.line(
#                     metrics_df,
#                     x="timestamp",
#                     y=["load_mw", "residual_load_mw"],
#                     title=f"Total Load vs. Residual Load ({bidding_zone})",
#                     labels={"value": "Power (MW)", "variable": "Metric"},
#                 )
#                 st.plotly_chart(fig_res, use_container_width=True)
#             else:
#                 st.warning("Generation and Load records exist but timestamps do not align.")
#         else:
#             st.info(
#                 "No generation or load data available in Lakehouse for this zone/date range.\n\n"
#                 "👉 Click **'🚀 Fetch & Process Market Data'** in the sidebar!"
#             )
#     except Exception as e:
#         st.warning(f"Notice: {e}")


# # --- TAB 3: Cross-Border Price Spreads ---
# with tab3:
#     st.header("Cross-Border Price Spread Analytics")
#     col_a, col_b = st.columns(2)
#     with col_a:
#         zone_a = st.selectbox("Zone A", ["DE_LU", "FR", "NL"], index=0)
#     with col_b:
#         zone_b = st.selectbox("Zone B", ["DE_LU", "FR", "NL"], index=1)

#     if zone_a != zone_b:
#         try:
#             df_a = filter_by_date(analytics.query_dataset_by_zone("day_ahead_prices", zone=zone_a))
#             df_b = filter_by_date(analytics.query_dataset_by_zone("day_ahead_prices", zone=zone_b))

#             if not df_a.empty and not df_b.empty:
#                 spread_df = SpreadCalculators.calculate_cross_border_spread(df_a, df_b, zone_a, zone_b)
#                 spread_col = f"spread_{zone_a}_{zone_b}_eur_mwh"

#                 fig_spread = px.line(
#                     spread_df,
#                     x="timestamp",
#                     y=spread_col,
#                     title=f"Price Spread: {zone_a} minus {zone_b} (€/MWh)",
#                     labels={spread_col: "Spread (€/MWh)"},
#                 )
#                 st.plotly_chart(fig_spread, use_container_width=True)
#             else:
#                 st.info(
#                     f"Missing price records for {zone_a} or {zone_b} in this range.\n\n"
#                     "👉 Click **'🚀 Fetch & Process Market Data'** in the sidebar to fetch prices."
#                 )
#         except Exception as e:
#             st.warning(f"Spread notice: {e}")


# # --- TAB 4: Detailed Analytics & Features ---
# with tab4:
#     st.header(f"📈 Advanced Feature & Volatility Analytics ({bidding_zone})")

#     try:
#         raw_prices_df = analytics.query_dataset_by_zone("day_ahead_prices", zone=bidding_zone)
#         raw_gen_df = analytics.query_dataset_by_zone("generation", zone=bidding_zone)
#         raw_load_df = analytics.query_dataset_by_zone("total_load", zone=bidding_zone)

#         prices_df = filter_by_date(raw_prices_df)
#         gen_df = filter_by_date(raw_gen_df)
#         load_df = filter_by_date(raw_load_df)

#         # 1. KPI Calculations
#         total_solar = AdditionalAnalyticsFeatures.calculate_total_solar_generation(gen_df)
#         total_wind, wind_on, wind_off = AdditionalAnalyticsFeatures.calculate_total_wind_generation(gen_df)
        
#         ren_share = 0.0
#         if not gen_df.empty:
#             ren_share = AdditionalAnalyticsFeatures.calculate_renewable_share(gen_df)

#         total_vol = AdditionalAnalyticsFeatures.calculate_total_volume(load_df)
#         base_price, peak_price = AdditionalAnalyticsFeatures.calculate_base_and_peak_prices(prices_df)
#         volatility = AdditionalAnalyticsFeatures.calculate_price_volatility_metrics(prices_df)

#         # 2. Key Metrics Row
#         st.subheader("Key Quantitative Feature Metrics")
#         m_col1, m_col2, m_col3, m_col4 = st.columns(4)
#         with m_col1:
#             st.metric("Total Solar Generation", f"{total_solar:,.2f} MWh")
#             st.metric("Base Avg Price (00-24)", f"{base_price:.2f} €/MWh")
#         with m_col2:
#             st.metric("Total Wind Generation", f"{total_wind:,.2f} MWh")
#             st.metric("Peak Avg Price (08-20)", f"{peak_price:.2f} €/MWh")
#         with m_col3:
#             st.metric("Renewable Share", f"{ren_share:.1f} %")
#             st.metric("Price Standard Dev.", f"{volatility['std_dev']:.2f} €/MWh")
#         with m_col4:
#             st.metric("Total Volume (Load)", f"{total_vol:,.2f} MWh")
#             st.metric("Price Max-Min Spread", f"{volatility['price_spread']:.2f} €/MWh")

#         st.markdown("---")

#         # 3. Daily Base vs. Peak Price Line Chart
#         st.subheader("Daily Average Base & Peak Price Trends")
#         daily_price_df = AdditionalAnalyticsFeatures.calculate_daily_base_peak_prices(prices_df)
        
#         if not daily_price_df.empty:
#             fig_daily_price = px.line(
#                 daily_price_df,
#                 x="date",
#                 y=["base_price", "peak_price"],
#                 title=f"Daily Base (00-24) vs. Peak (08-20) Price Trend ({bidding_zone})",
#                 labels={"value": "Price (€/MWh)", "variable": "Price Metric", "date": "Date"},
#                 markers=True
#             )
#             st.plotly_chart(fig_daily_price, use_container_width=True)
#         else:
#             st.info("No price data available for daily base and peak price trend.")

#         st.markdown("---")

#         # 4. Scatter Plots Section (Without trendline="ols" dependency)
#         st.subheader("Market Dynamics & Scatter Analysis")
        
#         if not prices_df.empty and not gen_df.empty:
#             prices_df["timestamp"] = pd.to_datetime(prices_df["timestamp"], utc=True)
#             gen_df["timestamp"] = pd.to_datetime(gen_df["timestamp"], utc=True)
            
#             feature_merged = pd.merge(prices_df, gen_df, on="timestamp", how="inner")

#             if not feature_merged.empty:
#                 sc_col1, sc_col2 = st.columns(2)

#                 with sc_col1:
#                     if "solar_mw" in feature_merged.columns and "price_eur_mwh" in feature_merged.columns:
#                         fig_solar_sc = px.scatter(
#                             feature_merged,
#                             x="solar_mw",
#                             y="price_eur_mwh",
#                             title="Price vs. Solar Generation",
#                             labels={"solar_mw": "Solar Generation (MW)", "price_eur_mwh": "Price (€/MWh)"},
#                             opacity=0.7
#                         )
#                         st.plotly_chart(fig_solar_sc, use_container_width=True)
#                     else:
#                         st.info("Solar data unavailable for scatter plot.")

#                 with sc_col2:
#                     if "price_eur_mwh" in feature_merged.columns:
#                         wind_cols = [c for c in ["wind_onshore_mw", "wind_offshore_mw"] if c in feature_merged.columns]
#                         if wind_cols:
#                             feature_merged["total_wind_mw"] = feature_merged[wind_cols].sum(axis=1)
#                             fig_wind_sc = px.scatter(
#                                 feature_merged,
#                                 x="total_wind_mw",
#                                 y="price_eur_mwh",
#                                 title="Price vs. Total Wind Generation",
#                                 labels={"total_wind_mw": "Wind Generation (MW)", "price_eur_mwh": "Price (€/MWh)"},
#                                 opacity=0.7
#                             )
#                             st.plotly_chart(fig_wind_sc, use_container_width=True)
#                         else:
#                             st.info("Wind generation data unavailable for scatter plot.")
#             else:
#                 st.warning("Price and Generation timestamps could not be inner-joined.")
#         else:
#             st.info("Insufficient price or generation data to display scatter plots.")

#     except Exception as e:
#         st.warning(f"Analytics notice: {e}")





import asyncio
import io
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Add src to system path for imports
sys.path.append(str(Path(__file__).resolve().parent / "src"))

from src.energy_data_engine.analytics.metrics import FundamentalMetrics
from src.energy_data_engine.analytics.spreads import SpreadCalculators
from src.energy_data_engine.analytics.features import AdditionalAnalyticsFeatures
from src.energy_data_engine.pipeline import EnergyDataPipeline
from src.energy_data_engine.storage.duck_analytics import DuckDBAnalyticsEngine

# Page Configuration
st.set_page_config(
    page_title="European Energy Data & Analytics Engine",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ European Energy Market Data Engine")
st.markdown("Real-time Power Market Analytics, Lakehouse Storage & Quantitative Feature Explorer")

# Initialize DuckDB Analytics Engine
analytics = DuckDBAnalyticsEngine()

# --- HELPER FUNCTIONS FOR CLEAN DATA EXPORT ---
def generate_clean_excel_bytes(zone: str, start_dt: pd.Timestamp, end_dt: pd.Timestamp) -> bytes:
    """Queries, deduplicates, and compiles multi-sheet Excel data in memory for Streamlit export."""
    output = io.BytesIO()
    s_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
    e_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")

    # Helper function to query DuckDB and deduplicate rows by timestamp
    def fetch_deduped(dataset_name: str) -> pd.DataFrame:
        dataset_path = analytics.data_dir / dataset_name
        if not dataset_path.exists() or not list(dataset_path.glob("**/*.parquet")):
            return pd.DataFrame()

        query_path = str(dataset_path / "**" / "*.parquet")
        query = f"""
            SELECT * FROM read_parquet('{query_path}')
            WHERE zone = '{zone}'
              AND timestamp >= '{s_str}'
              AND timestamp < '{e_str}'
            QUALIFY ROW_NUMBER() OVER (PARTITION BY timestamp ORDER BY timestamp DESC) = 1
            ORDER BY timestamp ASC
        """
        try:
            return analytics.conn.execute(query).df()
        except Exception as e:
            st.error(f"Error fetching dataset '{dataset_name}': {e}")
            return pd.DataFrame()

    # Query clean, deduplicated datasets
    df_prices = fetch_deduped("day_ahead_prices")
    df_intraday = fetch_deduped("intraday_prices")
    df_load = fetch_deduped("total_load")
    df_gen = fetch_deduped("generation")

    # Strip timezone info for Excel compatibility
    for df in [df_prices, df_intraday, df_load, df_gen]:
        if not df.empty and "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)

    # Write sheets into Excel workbook
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        if not df_prices.empty:
            df_prices.to_excel(writer, sheet_name="Day Ahead Prices", index=False)
        if not df_intraday.empty:
            df_intraday.to_excel(writer, sheet_name="Intraday Prices", index=False)
        if not df_load.empty:
            df_load.to_excel(writer, sheet_name="Total Load", index=False)
        if not df_gen.empty:
            df_gen.to_excel(writer, sheet_name="Generation Mix", index=False)

    output.seek(0)
    return output.getvalue()


# Helper function to filter DataFrame by selected dates for dashboard charts
def filter_by_date(df: pd.DataFrame, timestamp_col: str = "timestamp") -> pd.DataFrame:
    if df.empty or timestamp_col not in df.columns:
        return df
    df[timestamp_col] = pd.to_datetime(df[timestamp_col], utc=True)
    return df[(df[timestamp_col] >= start_dt) & (df[timestamp_col] < end_dt)]


# --- SIDEBAR CONTROLS ---
st.sidebar.header("🕹️ Market Controls")
bidding_zone = st.sidebar.selectbox("Select Primary Bidding Zone", ["DE_LU", "FR", "NL"], index=0)

st.sidebar.markdown("---")
st.sidebar.subheader("📅 Date Range Filter")
today = date.today()
start_date = st.sidebar.date_input("Start Date", today - timedelta(days=7))
end_date = st.sidebar.date_input("End Date", today + timedelta(days=1))

# Convert sidebar dates to UTC datetimes for filtering & ingestion
start_dt = pd.to_datetime(start_date).tz_localize("UTC")
end_dt = pd.to_datetime(end_date).tz_localize("UTC") + pd.Timedelta(days=1)

st.sidebar.markdown("---")
st.sidebar.subheader("📡 Data Pipeline Actions")

# Ingestion trigger
if st.sidebar.button("🚀 Fetch & Process Market Data"):
    with st.spinner(f"Ingesting data for selected zones ({start_date} to {end_date})..."):
        pipeline = EnergyDataPipeline()
        start_time = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        end_time = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)

        # Run async ingestion pipeline
        asyncio.run(
            pipeline.run_ingestion_pipeline(
                bidding_zones=["DE_LU", "FR", "NL"],
                start=start_time,
                end=end_time,
            )
        )
        st.sidebar.success("✅ Ingestion & Lakehouse Store Updated!")
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("📥 Clean Data Exporter")

# Multi-sheet Deduplicated Excel Download
if st.sidebar.button("📦 Prepare Clean Excel Workbook"):
    with st.spinner("Deduplicating & compiling Excel file..."):
        excel_bytes = generate_clean_excel_bytes(bidding_zone, start_dt, end_dt)
        if excel_bytes:
            st.sidebar.download_button(
                label="💾 Download Clean Excel (.xlsx)",
                data=excel_bytes,
                file_name=f"{bidding_zone}_clean_market_data_{start_date}_to_{end_date}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            st.sidebar.success("✅ Excel workbook generated successfully!")
        else:
            st.sidebar.warning("No data found to export for these dates.")


# --- MAIN DASHBOARD TABS ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Price & Load Analytics", 
    "🌱 Generation Mix & Residual Load", 
    "🔄 Cross-Border Spreads",
    "📈 Detailed Analytics & Features"
])

# --- TAB 1: Day-Ahead & Intraday Prices ---
with tab1:
    st.header(f"Day-Ahead & Intraday Market Prices ({bidding_zone})")

    try:
        raw_prices_df = analytics.query_dataset_by_zone("day_ahead_prices", zone=bidding_zone)
        prices_df = filter_by_date(raw_prices_df)

        raw_intraday_df = analytics.query_dataset_by_zone("intraday_prices", zone=bidding_zone)
        intraday_df = filter_by_date(raw_intraday_df)

        if not prices_df.empty:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Avg Day-Ahead Price", f"{prices_df['price_eur_mwh'].mean():.2f} €/MWh")
            with col2:
                st.metric("Min Day-Ahead Price", f"{prices_df['price_eur_mwh'].min():.2f} €/MWh")
            with col3:
                st.metric("Max Day-Ahead Price", f"{prices_df['price_eur_mwh'].max():.2f} €/MWh")
            with col4:
                if not intraday_df.empty and "price_eur_mwh" in intraday_df.columns:
                    st.metric("Avg Intraday Price", f"{intraday_df['price_eur_mwh'].mean():.2f} €/MWh")
                else:
                    st.metric("Avg Intraday Price", "N/A")

            # Combined Plot: Day-Ahead vs Intraday Prices
            fig_price = go.Figure()

            fig_price.add_trace(
                go.Scatter(
                    x=prices_df["timestamp"],
                    y=prices_df["price_eur_mwh"],
                    mode="lines",
                    name="Day-Ahead Price (€/MWh)",
                    line=dict(color="#1f77b4", width=2),
                )
            )

            if not intraday_df.empty and "price_eur_mwh" in intraday_df.columns:
                fig_price.add_trace(
                    go.Scatter(
                        x=intraday_df["timestamp"],
                        y=intraday_df["price_eur_mwh"],
                        mode="lines",
                        name="Intraday Price (€/MWh)",
                        line=dict(color="#ff7f0e", width=2, dash="dash"),
                    )
                )

            fig_price.update_layout(
                title=f"Day-Ahead vs. Intraday Price Time Series ({bidding_zone})",
                xaxis_title="UTC Time",
                yaxis_title="Price (€/MWh)",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )

            st.plotly_chart(fig_price, use_container_width=True)

        else:
            st.info(
                f"No price data stored for '{bidding_zone}' between {start_date} and {end_date}.\n\n"
                "👉 Click **'🚀 Fetch & Process Market Data'** in the sidebar to fetch and save data for this date range!"
            )
    except Exception as e:
        st.warning(f"Notice: {e}")


# --- TAB 2: Generation Mix & Residual Load ---
with tab2:
    st.header(f"Generation Mix & Fundamental Metrics ({bidding_zone})")
    try:
        raw_gen_df = analytics.query_dataset_by_zone("generation", zone=bidding_zone)
        raw_load_df = analytics.query_dataset_by_zone("total_load", zone=bidding_zone)

        gen_df = filter_by_date(raw_gen_df)
        load_df = filter_by_date(raw_load_df)

        if not gen_df.empty and not load_df.empty:
            # Normalize timestamps for exact matching
            gen_df["timestamp"] = pd.to_datetime(gen_df["timestamp"], utc=True)
            load_df["timestamp"] = pd.to_datetime(load_df["timestamp"], utc=True)

            merged = gen_df.merge(load_df[["timestamp", "load_mw"]], on="timestamp", how="inner")
            
            if not merged.empty:
                metrics_df = FundamentalMetrics.calculate_renewable_penetration(merged)

                # Fuel Breakdown Chart
                gen_cols = [
                    c for c in ["solar_mw", "wind_onshore_mw", "wind_offshore_mw", "gas_mw", "hard_coal_mw", "nuclear_mw"]
                    if c in metrics_df.columns
                ]
                fig_gen = px.area(
                    metrics_df,
                    x="timestamp",
                    y=gen_cols,
                    title=f"Generation Breakdown (MW) - {bidding_zone}",
                    labels={"value": "Generation (MW)", "variable": "Fuel Type"},
                )
                st.plotly_chart(fig_gen, use_container_width=True)

                # Total Load vs Residual Load Chart
                fig_res = px.line(
                    metrics_df,
                    x="timestamp",
                    y=["load_mw", "residual_load_mw"],
                    title=f"Total Load vs. Residual Load ({bidding_zone})",
                    labels={"value": "Power (MW)", "variable": "Metric"},
                )
                st.plotly_chart(fig_res, use_container_width=True)
            else:
                st.warning("Generation and Load records exist but timestamps do not align.")
        else:
            st.info(
                "No generation or load data available in Lakehouse for this zone/date range.\n\n"
                "👉 Click **'🚀 Fetch & Process Market Data'** in the sidebar!"
            )
    except Exception as e:
        st.warning(f"Notice: {e}")


# --- TAB 3: Cross-Border Price Spreads ---
with tab3:
    st.header("Cross-Border Price Spread Analytics")
    col_a, col_b = st.columns(2)
    with col_a:
        zone_a = st.selectbox("Zone A", ["DE_LU", "FR", "NL"], index=0)
    with col_b:
        zone_b = st.selectbox("Zone B", ["DE_LU", "FR", "NL"], index=1)

    if zone_a != zone_b:
        try:
            df_a = filter_by_date(analytics.query_dataset_by_zone("day_ahead_prices", zone=zone_a))
            df_b = filter_by_date(analytics.query_dataset_by_zone("day_ahead_prices", zone=zone_b))

            if not df_a.empty and not df_b.empty:
                spread_df = SpreadCalculators.calculate_cross_border_spread(df_a, df_b, zone_a, zone_b)
                spread_col = f"spread_{zone_a}_{zone_b}_eur_mwh"

                fig_spread = px.line(
                    spread_df,
                    x="timestamp",
                    y=spread_col,
                    title=f"Price Spread: {zone_a} minus {zone_b} (€/MWh)",
                    labels={spread_col: "Spread (€/MWh)"},
                )
                st.plotly_chart(fig_spread, use_container_width=True)
            else:
                st.info(
                    f"Missing price records for {zone_a} or {zone_b} in this range.\n\n"
                    "👉 Click **'🚀 Fetch & Process Market Data'** in the sidebar to fetch prices."
                )
        except Exception as e:
            st.warning(f"Spread notice: {e}")


# --- TAB 4: Detailed Analytics & Features ---
with tab4:
    st.header(f"📈 Advanced Feature & Volatility Analytics ({bidding_zone})")

    try:
        raw_prices_df = analytics.query_dataset_by_zone("day_ahead_prices", zone=bidding_zone)
        raw_gen_df = analytics.query_dataset_by_zone("generation", zone=bidding_zone)
        raw_load_df = analytics.query_dataset_by_zone("total_load", zone=bidding_zone)

        prices_df = filter_by_date(raw_prices_df)
        gen_df = filter_by_date(raw_gen_df)
        load_df = filter_by_date(raw_load_df)

        # 1. KPI Calculations
        total_solar = AdditionalAnalyticsFeatures.calculate_total_solar_generation(gen_df)
        total_wind, wind_on, wind_off = AdditionalAnalyticsFeatures.calculate_total_wind_generation(gen_df)
        
        ren_share = 0.0
        if not gen_df.empty:
            ren_share = AdditionalAnalyticsFeatures.calculate_renewable_share(gen_df)

        total_vol = AdditionalAnalyticsFeatures.calculate_total_volume(load_df)
        base_price, peak_price = AdditionalAnalyticsFeatures.calculate_base_and_peak_prices(prices_df)
        volatility = AdditionalAnalyticsFeatures.calculate_price_volatility_metrics(prices_df)

        # 2. Key Metrics Row
        st.subheader("Key Quantitative Feature Metrics")
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        with m_col1:
            st.metric("Total Solar Generation", f"{total_solar:,.2f} MWh")
            st.metric("Base Avg Price (00-24)", f"{base_price:.2f} €/MWh")
        with m_col2:
            st.metric("Total Wind Generation", f"{total_wind:,.2f} MWh")
            st.metric("Peak Avg Price (08-20)", f"{peak_price:.2f} €/MWh")
        with m_col3:
            st.metric("Renewable Share", f"{ren_share:.1f} %")
            st.metric("Price Standard Dev.", f"{volatility['std_dev']:.2f} €/MWh")
        with m_col4:
            st.metric("Total Volume (Load)", f"{total_vol:,.2f} MWh")
            st.metric("Price Max-Min Spread", f"{volatility['price_spread']:.2f} €/MWh")

        st.markdown("---")

        # 3. Daily Base vs. Peak Price Line Chart
        st.subheader("Daily Average Base & Peak Price Trends")
        daily_price_df = AdditionalAnalyticsFeatures.calculate_daily_base_peak_prices(prices_df)
        
        if not daily_price_df.empty:
            fig_daily_price = px.line(
                daily_price_df,
                x="date",
                y=["base_price", "peak_price"],
                title=f"Daily Base (00-24) vs. Peak (08-20) Price Trend ({bidding_zone})",
                labels={"value": "Price (€/MWh)", "variable": "Price Metric", "date": "Date"},
                markers=True
            )
            st.plotly_chart(fig_daily_price, use_container_width=True)
        else:
            st.info("No price data available for daily base and peak price trend.")

        st.markdown("---")

        # 4. Scatter Plots Section
        st.subheader("Market Dynamics & Scatter Analysis")
        
        if not prices_df.empty and not gen_df.empty:
            prices_df["timestamp"] = pd.to_datetime(prices_df["timestamp"], utc=True)
            gen_df["timestamp"] = pd.to_datetime(gen_df["timestamp"], utc=True)
            
            feature_merged = pd.merge(prices_df, gen_df, on="timestamp", how="inner")

            if not feature_merged.empty:
                sc_col1, sc_col2 = st.columns(2)

                with sc_col1:
                    if "solar_mw" in feature_merged.columns and "price_eur_mwh" in feature_merged.columns:
                        fig_solar_sc = px.scatter(
                            feature_merged,
                            x="solar_mw",
                            y="price_eur_mwh",
                            title="Price vs. Solar Generation",
                            labels={"solar_mw": "Solar Generation (MW)", "price_eur_mwh": "Price (€/MWh)"},
                            opacity=0.7
                        )
                        st.plotly_chart(fig_solar_sc, use_container_width=True)
                    else:
                        st.info("Solar data unavailable for scatter plot.")

                with sc_col2:
                    if "price_eur_mwh" in feature_merged.columns:
                        wind_cols = [c for c in ["wind_onshore_mw", "wind_offshore_mw"] if c in feature_merged.columns]
                        if wind_cols:
                            feature_merged["total_wind_mw"] = feature_merged[wind_cols].sum(axis=1)
                            fig_wind_sc = px.scatter(
                                feature_merged,
                                x="total_wind_mw",
                                y="price_eur_mwh",
                                title="Price vs. Total Wind Generation",
                                labels={"total_wind_mw": "Wind Generation (MW)", "price_eur_mwh": "Price (€/MWh)"},
                                opacity=0.7
                            )
                            st.plotly_chart(fig_wind_sc, use_container_width=True)
                        else:
                            st.info("Wind generation data unavailable for scatter plot.")
            else:
                st.warning("Price and Generation timestamps could not be inner-joined.")
        else:
            st.info("Insufficient price or generation data to display scatter plots.")

    except Exception as e:
        st.warning(f"Analytics notice: {e}")