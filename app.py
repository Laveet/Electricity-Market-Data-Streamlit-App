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
from src.energy_data_engine.analytics.forecast_errors import (
    compute_all_metrics,
    find_worst_error_periods,
    METRIC_GLOSSARY,
)
from src.energy_data_engine.pipeline import EnergyDataPipeline
from src.energy_data_engine.storage.duck_analytics import DuckDBAnalyticsEngine
from src.energy_data_engine.storage.parquet_store import ParquetLakehouseWriter
from src.energy_data_engine.clients.entsoe import AsyncEntsoeClient
from src.energy_data_engine.forecasting.baseline_forecaster import SeasonalNaiveForecaster
from config.settings import settings

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


# --- SHARED HELPER: renders one Forecast Accuracy section (Load or Price) ---
def render_forecast_accuracy_section(
    section_title: str,
    y_axis_title: str,
    unit_label: str,
    value_fmt: str,
    bidding_zone: str,
    zone_tz: str,
    target_date,
    actual_dataset: str,
    actual_value_col: str,
    reference_dataset: str,
    reference_value_col: str,
    reference_label: str,
    reference_note: str,
    accuracy_method: str,
    top_n_worst: int = 3,
):
    """Builds the comparison chart, error plot, accuracy metrics, and worst-hour
    table for one quantity (Load or Price). Works generically for any hourly
    dataset that has (a) a historical 'actual' series and (b) an optional
    'reference' series to benchmark against the same actual data."""
    day_start_local = pd.Timestamp(target_date, tz=zone_tz)
    day_start_utc = day_start_local.tz_convert("UTC")
    day_end_utc = (day_start_local + pd.Timedelta(days=1)).tz_convert("UTC")

    history_df = analytics.query_dataset_by_zone(actual_dataset, zone=bidding_zone)

    own_fc_df = SeasonalNaiveForecaster(lookback_weeks=8).forecast(
        history_df, target_date, zone_timezone=zone_tz, value_col=actual_value_col,
    ).rename(columns={"own_forecast": "own_value"})

    actual_df = pd.DataFrame()
    if not history_df.empty:
        hdf = history_df.copy()
        hdf["timestamp"] = pd.to_datetime(hdf["timestamp"], utc=True)
        actual_df = hdf[
            (hdf["timestamp"] >= day_start_utc) & (hdf["timestamp"] < day_end_utc)
        ][["timestamp", actual_value_col]].rename(columns={actual_value_col: "actual_value"})
    has_actual = not actual_df.empty

    reference_df = pd.DataFrame()
    if reference_dataset:
        rdf = analytics.query_dataset_by_zone(reference_dataset, zone=bidding_zone)
        if not rdf.empty:
            rdf["timestamp"] = pd.to_datetime(rdf["timestamp"], utc=True)
            reference_df = rdf[
                (rdf["timestamp"] >= day_start_utc) & (rdf["timestamp"] < day_end_utc)
            ][["timestamp", reference_value_col]].rename(columns={reference_value_col: "reference_value"})
    has_reference = not reference_df.empty

    combined = own_fc_df.copy()
    if has_reference:
        combined = combined.merge(reference_df, on="timestamp", how="outer")
    if has_actual:
        combined = combined.merge(actual_df, on="timestamp", how="outer")
    combined = combined.sort_values("timestamp").reset_index(drop=True)

    if combined["own_value"].isna().all() and not has_reference and not has_actual:
        st.info(
            f"Not enough historical data yet to build a forecast for {target_date.isoformat()}, "
            f"and no {reference_label} data cached either."
        )
        return

    # Data may be hourly or 15-minute (ENTSO-E publishes both, depending on series/zone) --
    # size the worst-period highlight band to whatever spacing this data actually has,
    # so it doesn't swallow several neighboring points on fine-grained series.
    _spacing = combined["timestamp"].sort_values().diff().dropna()
    _spacing = _spacing[_spacing > pd.Timedelta(0)]
    period_width = _spacing.median() if not _spacing.empty else pd.Timedelta(hours=1)
    highlight_half_width = period_width * 0.4

    # --- Main comparison chart, with the single worst period for each forecast highlighted ---
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=combined["timestamp"], y=combined["own_value"], mode="lines+markers",
        name="App's Own Forecast (Seasonal Baseline)", line=dict(color="#2ca02c", width=2),
    ))
    if has_reference:
        fig.add_trace(go.Scatter(
            x=combined["timestamp"], y=combined["reference_value"], mode="lines+markers",
            name=reference_label, line=dict(color="#1f77b4", width=2, dash="dash"),
        ))
    if has_actual:
        fig.add_trace(go.Scatter(
            x=combined["timestamp"], y=combined["actual_value"], mode="lines+markers",
            name="Actual", line=dict(color="#d62728", width=3),
        ))

    worst_own = pd.DataFrame()
    worst_ref = pd.DataFrame()
    if has_actual:
        worst_own = find_worst_error_periods(combined, "actual_value", "own_value", top_n=top_n_worst)
        if not worst_own.empty:
            ts0 = worst_own.iloc[0]["timestamp"]
            fig.add_vrect(
                x0=ts0 - highlight_half_width, x1=ts0 + highlight_half_width,
                fillcolor="#2ca02c", opacity=0.18, line_width=0,
                annotation_text="Own's worst period", annotation_position="top left",
            )
        if has_reference:
            worst_ref = find_worst_error_periods(combined, "actual_value", "reference_value", top_n=top_n_worst)
            if not worst_ref.empty:
                ts1 = worst_ref.iloc[0]["timestamp"]
                fig.add_vrect(
                    x0=ts1 - highlight_half_width, x1=ts1 + highlight_half_width,
                    fillcolor="#1f77b4", opacity=0.18, line_width=0,
                    annotation_text=f"{reference_label}'s worst period", annotation_position="bottom left",
                )

    fig.update_layout(
        title=f"{section_title} — {bidding_zone} — {target_date.isoformat()}",
        xaxis_title=f"Local Time ({zone_tz})",
        yaxis_title=y_axis_title,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Error-over-time chart: shaded area shows the size of the miss at every hour ---
    if has_actual:
        fig_err = go.Figure()
        own_err = combined["own_value"] - combined["actual_value"]
        fig_err.add_trace(go.Scatter(
            x=combined["timestamp"], y=own_err, mode="lines", name="Own Forecast Error",
            fill="tozeroy", line=dict(color="#2ca02c"),
        ))
        if has_reference:
            ref_err = combined["reference_value"] - combined["actual_value"]
            fig_err.add_trace(go.Scatter(
                x=combined["timestamp"], y=ref_err, mode="lines", name=f"{reference_label} Error",
                fill="tozeroy", line=dict(color="#1f77b4"),
            ))
        fig_err.add_hline(y=0, line_color="gray", line_width=1)
        fig_err.update_layout(
            title="Forecast Error Over Time (Forecast − Actual) — shaded area = size of the miss",
            xaxis_title=f"Local Time ({zone_tz})",
            yaxis_title=f"Error ({unit_label})",
            hovermode="x unified",
            height=300,
        )
        st.plotly_chart(fig_err, use_container_width=True)

        # --- Accuracy metrics, scored against actual ---
        st.subheader("📏 Forecast Accuracy vs. Actual")
        m1, m2 = st.columns(2)
        with m1:
            st.markdown("**App's Own Forecast**")
            own_metrics = compute_all_metrics(combined["actual_value"], combined["own_value"], method=accuracy_method)
            st.metric(f"Accuracy (100 − {accuracy_method.upper()})", f"{own_metrics['accuracy_pct']:.1f}%")
            oc1, oc2, oc3, oc4 = st.columns(4)
            oc1.metric("MAE", value_fmt.format(own_metrics["mae"]))
            oc2.metric("RMSE", value_fmt.format(own_metrics["rmse"]))
            oc3.metric("MSE", f"{own_metrics['mse']:,.1f}")
            oc4.metric("MAPE", f"{own_metrics['mape_pct']:.2f}%")
        with m2:
            st.markdown(f"**{reference_label}**")
            if has_reference:
                ref_metrics = compute_all_metrics(combined["actual_value"], combined["reference_value"], method=accuracy_method)
                st.metric(f"Accuracy (100 − {accuracy_method.upper()})", f"{ref_metrics['accuracy_pct']:.1f}%")
                rc1, rc2, rc3, rc4 = st.columns(4)
                rc1.metric("MAE", value_fmt.format(ref_metrics["mae"]))
                rc2.metric("RMSE", value_fmt.format(ref_metrics["rmse"]))
                rc3.metric("MSE", f"{ref_metrics['mse']:,.1f}")
                rc4.metric("MAPE", f"{ref_metrics['mape_pct']:.2f}%")
            else:
                st.info(reference_note)

        st.markdown("**🔻 Time periods with the largest forecast error**")
        wc1, wc2 = st.columns(2)
        with wc1:
            st.caption("App's Own Forecast")
            if not worst_own.empty:
                show = worst_own.copy()
                show["timestamp"] = show["timestamp"].dt.tz_convert(zone_tz).dt.strftime("%Y-%m-%d %H:%M")
                st.dataframe(show[["timestamp", "actual", "forecast", "abs_error", "pct_error"]], hide_index=True, use_container_width=True)
            else:
                st.caption("—")
        with wc2:
            st.caption(reference_label)
            if not worst_ref.empty:
                show = worst_ref.copy()
                show["timestamp"] = show["timestamp"].dt.tz_convert(zone_tz).dt.strftime("%Y-%m-%d %H:%M")
                st.dataframe(show[["timestamp", "actual", "forecast", "abs_error", "pct_error"]], hide_index=True, use_container_width=True)
            else:
                st.caption("—")

    else:
        st.subheader("🔀 Forecast Divergence (actual data not available yet)")
        st.info(
            f"{target_date.isoformat()} hasn't happened (or hasn't been published) yet, so "
            "there's no actual data to score against. Shown instead: how far the two "
            "forecasts currently disagree with each other."
        )
        if has_reference:
            div_metrics = compute_all_metrics(combined["reference_value"], combined["own_value"], method=accuracy_method)
            d1, d2, d3 = st.columns(3)
            d1.metric("Mean Absolute Divergence", value_fmt.format(div_metrics["mae"]))
            d2.metric("Divergence %", f"{div_metrics['mape_pct']:.2f}%")
            d3.metric("RMS Divergence", value_fmt.format(div_metrics["rmse"]))
        else:
            st.warning(reference_note)


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
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Price & Load Analytics",
    "🌱 Generation Mix & Residual Load",
    "🔄 Cross-Border Spreads",
    "📈 Detailed Analytics & Features",
    "⚡ Trading & Market Fundamentals",
    "🎯 Forecast Accuracy",
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
    # --- TAB 5: Trading & Market Fundamental Metrics ---
with tab5:
    st.header(f"⚡ Trading & Market Fundamental Metrics ({bidding_zone})")

    try:
        raw_prices_df = analytics.query_dataset_by_zone(
            "day_ahead_prices",
            zone=bidding_zone
        )

        raw_gen_df = analytics.query_dataset_by_zone(
            "generation",
            zone=bidding_zone
        )

        raw_load_df = analytics.query_dataset_by_zone(
            "total_load",
            zone=bidding_zone
        )

        prices_df = filter_by_date(raw_prices_df)
        gen_df = filter_by_date(raw_gen_df)
        load_df = filter_by_date(raw_load_df)

        if not prices_df.empty and not gen_df.empty and not load_df.empty:

            # Normalize timestamps
            prices_df["timestamp"] = pd.to_datetime(
                prices_df["timestamp"],
                utc=True
            )

            gen_df["timestamp"] = pd.to_datetime(
                gen_df["timestamp"],
                utc=True
            )

            load_df["timestamp"] = pd.to_datetime(
                load_df["timestamp"],
                utc=True
            )

            merged_df = prices_df.merge(
                gen_df,
                on="timestamp",
                how="inner"
            ).merge(
                load_df[["timestamp", "load_mw"]],
                on="timestamp",
                how="inner"
            )


            if not merged_df.empty:

                # 1. Fundamental Calculations
                df_analyzed = FundamentalMetrics.calculate_renewable_penetration(
                    merged_df
                )

                neg_stats = FundamentalMetrics.calculate_negative_price_stats(
                    df_analyzed
                )

                capture_stats = FundamentalMetrics.calculate_capture_prices(
                    df_analyzed
                )

                corr = FundamentalMetrics.calculate_residual_load_price_correlation(
                    df_analyzed
                )


                # 2. KPI Cards
                st.subheader("Market Fundamental KPI Dashboard")

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(
                        label="Negative Price Frequency",
                        value=f"{neg_stats['neg_frequency_pct']}%",
                        delta=f"{neg_stats['neg_hours']} Hours",
                        delta_color="inverse"
                    )

                with col2:
                    st.metric(
                        label="Baseload Price",
                        value=f"€{capture_stats.get('baseload_price_eur',0.0):.2f}/MWh"
                    )

                with col3:
                    solar_cp = capture_stats.get(
                        "solar_capture_price",
                        0.0
                    )

                    solar_cf = capture_stats.get(
                        "solar_capture_factor",
                        0.0
                    )

                    st.metric(
                        label="Solar Capture Price",
                        value=f"€{solar_cp:.2f}/MWh",
                        delta=f"CF: {solar_cf:.1%}"
                    )


                with col4:
                    wind_cp = capture_stats.get(
                        "wind_onshore_capture_price",
                        0.0
                    )

                    wind_cf = capture_stats.get(
                        "wind_onshore_capture_factor",
                        0.0
                    )

                    st.metric(
                        label="Wind Onshore Capture Price",
                        value=f"€{wind_cp:.2f}/MWh",
                        delta=f"CF: {wind_cf:.1%}"
                    )


                st.markdown("---")


                # 3. Residual Load vs Price Analysis
                st.subheader(
                    "📈 Merit Order Dynamics: Residual Load vs Market Price"
                )


                st.markdown(
                    f"""
                    **Pearson Correlation:** `{corr}`

                    Residual load represents remaining demand after renewable 
                    generation. Increasing residual load generally pushes 
                    higher-cost thermal generators into dispatch, increasing 
                    market prices.
                    """
                )


                fig_scatter = px.scatter(
                    df_analyzed,
                    x="residual_load_mw",
                    y="price_eur_mwh",
                    color="renewable_penetration_pct",
                    color_continuous_scale="Viridis",
                    labels={
                        "residual_load_mw":
                            "Residual Net Load (MW)",

                        "price_eur_mwh":
                            "Day-Ahead Price (€/MWh)",

                        "renewable_penetration_pct":
                            "Renewable Penetration %"
                    },

                    title=
                    "Price Elasticity & Merit Order Curve"
                )


                fig_scatter.update_layout(
                    template="plotly_dark",
                    height=550
                )


                st.plotly_chart(
                    fig_scatter,
                    use_container_width=True
                )


            else:
                st.warning(
                    "Price, generation and load data could not be aligned."
                )

        else:
            st.info(
                """
                Missing price, generation or load data.

                👉 Use **Fetch & Process Market Data** from sidebar.
                """
            )


    except Exception as e:
        st.warning(
            f"Trading analytics notice: {e}"
        )


# --- TAB 6: Forecast Accuracy (Load & Price) ---
with tab6:
    st.header(f"🎯 Forecast Accuracy ({bidding_zone})")
    st.markdown(
        "Compares this app's own baseline forecast against a published reference "
        "series, and — once actual data is available — scores both against reality. "
        "Pick a *future* date to see how the two forecasts currently diverge from "
        "each other, or a *past* date to see which one was more accurate."
    )

    with st.expander("ℹ️ What do MSE, RMSE, MAPE, WAPE and Accuracy % mean?"):
        for short_name, long_name, description in METRIC_GLOSSARY:
            st.markdown(f"**{short_name}** ({long_name}) — {description}")

    fc_col1, fc_col2, fc_col3 = st.columns([2, 1.3, 1.3])
    with fc_col1:
        target_date = st.date_input(
            "🎯 Target Date to Forecast",
            value=date.today() + timedelta(days=1),
            key="forecast_target_date",
        )
    with fc_col2:
        accuracy_method_choice = st.radio(
            "Headline Accuracy Metric",
            options=["WAPE (recommended)", "MAPE"],
            key="accuracy_method_choice",
        )
        accuracy_method = "wape" if accuracy_method_choice.startswith("WAPE") else "mape"
    with fc_col3:
        st.markdown("&nbsp;")
        fetch_entsoe_forecast = st.button("🔮 Fetch ENTSO-E Load Forecast")

    try:
        zone_cfg = settings.load_zone_config().get("bidding_zones", {}).get(bidding_zone, {})
        zone_tz = zone_cfg.get("timezone", "UTC")
    except Exception as e:
        zone_tz = "UTC"
        st.warning(f"Could not load zone timezone config, defaulting to UTC: {e}")

    if fetch_entsoe_forecast:
        try:
            fc_day_start_local = pd.Timestamp(target_date, tz=zone_tz)
            fc_day_start_utc = fc_day_start_local.tz_convert("UTC")
            fc_day_end_utc = (fc_day_start_local + pd.Timedelta(days=1)).tz_convert("UTC")
            with st.spinner("Fetching ENTSO-E day-ahead load forecast..."):
                entsoe_client = AsyncEntsoeClient()
                fc_records = asyncio.run(
                    entsoe_client.fetch_load_forecast(
                        bidding_zone, fc_day_start_utc.to_pydatetime(), fc_day_end_utc.to_pydatetime()
                    )
                )
                if fc_records:
                    ParquetLakehouseWriter().write_records(fc_records, dataset_name="total_load_forecast")
                    st.success(
                        f"✅ Cached ENTSO-E load forecast for {target_date.isoformat()} "
                        f"({len(fc_records)} hourly points)."
                    )
                else:
                    st.warning(
                        "ENTSO-E returned no forecast data for this date — it may be outside "
                        "their published horizon (typically available from ~1 day before delivery)."
                    )
        except Exception as e:
            st.warning(f"ENTSO-E forecast fetch notice: {e}")

    load_subtab, price_subtab = st.tabs(["⚡ Load Forecast (MW)", "💶 Price Forecast (€/MWh)"])

    with load_subtab:
        try:
            render_forecast_accuracy_section(
                section_title="Load Forecast Comparison",
                y_axis_title="Load (MW)",
                unit_label="MW",
                value_fmt="{:,.0f} MW",
                bidding_zone=bidding_zone,
                zone_tz=zone_tz,
                target_date=target_date,
                actual_dataset="total_load",
                actual_value_col="load_mw",
                reference_dataset="total_load_forecast",
                reference_value_col="forecast_load_mw",
                reference_label="ENTSO-E Day-Ahead Forecast",
                reference_note=(
                    "No ENTSO-E forecast cached for this date yet. Click "
                    "**🔮 Fetch ENTSO-E Load Forecast** above."
                ),
                accuracy_method=accuracy_method,
            )
        except Exception as e:
            st.warning(f"Load Forecast Accuracy notice: {e}")

    with price_subtab:
        st.caption(
            "ℹ️ ENTSO-E does not publish a separate day-ahead **price** forecast — the "
            "Day-Ahead price *is* the settled market outcome, fixed ~12–36h before "
            "delivery, so it's treated here as the value being forecast (same role "
            "Actual Load plays on the Load tab). The reference series shown instead is "
            "the **Intraday Market VWAP** — the volume-weighted price actually traded "
            "much closer to real time — as the closest available 'how did the day-ahead "
            "price compare to what really happened' benchmark. Use the sidebar's "
            "**Fetch & Process Market Data** to backfill Day-Ahead / Intraday price data "
            "for more dates (no separate fetch button needed here)."
        )
        try:
            render_forecast_accuracy_section(
                section_title="Price Forecast Comparison",
                y_axis_title="Price (€/MWh)",
                unit_label="€/MWh",
                value_fmt="{:,.2f} €/MWh",
                bidding_zone=bidding_zone,
                zone_tz=zone_tz,
                target_date=target_date,
                actual_dataset="day_ahead_prices",
                actual_value_col="price_eur_mwh",
                reference_dataset="intraday_prices",
                reference_value_col="vwap_eur_mwh",
                reference_label="Intraday Market VWAP",
                reference_note=(
                    "No intraday price data cached for this date yet. Use the sidebar's "
                    "**Fetch & Process Market Data**."
                ),
                accuracy_method=accuracy_method,
            )
        except Exception as e:
            st.warning(f"Price Forecast Accuracy notice: {e}")
