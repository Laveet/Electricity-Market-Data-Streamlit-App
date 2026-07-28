# ⚡ Energy Data Engine

An enterprise-grade, asynchronous data pipeline, lakehouse engine, and quantitative analytics dashboard designed for wholesale European electricity markets (**DE_LU**, **FR**, **NL**).

Built to ingest, validate, store, and analyze **Day-Ahead Prices**, **Actual Generation by Fuel Type**, and **Total Load** using modern data engineering patterns (AsyncIO, Pydantic, PyArrow, DuckDB, Streamlit, and GitHub Actions).

---

## 🏗️ System Architecture & Data Methodology

```mermaid
flowchart TD
    subgraph External_Sources ["🌐 Data Ingestion (ENTSO-E Transparency Platform)"]
        A[ENTSO-E Rest API]
    end

    subgraph Async_Ingestion ["⚡ Async Pipeline Layer (Python)"]
        B[AsyncEntsoeClient / httpx] --> C[Pydantic v2 Data Schemas & Validation]
        C --> D[PyArrow Partitioned Writer]
    end

    subgraph Storage_Layer ["💾 Parquet Lakehouse Storage"]
        D --> E[(data/lakehouse/day_ahead_prices)]
        D --> F[(data/lakehouse/total_load)]
        D --> G[(data/lakehouse/generation)]
    end

    subgraph Analytics_Engine ["🦆 Analytics & Query Layer"]
        H[DuckDB Analytics Engine]
        E --> H
        F --> H
        G --> H
        H --> I[Analytics & Features Engine / features.py]
    end

    subgraph Presentation ["📊 Visualization Layer"]
        I --> J[Streamlit Interactive Dashboard]
    end

    subgraph Automation ["🤖 CI/CD Orchestration"]
        K[GitHub Actions Daily Cron Job] -->|Triggers at 06:00 UTC| B
    end
    