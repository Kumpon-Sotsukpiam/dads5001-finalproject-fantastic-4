# 🏙️ Bangkok Complaints Analytics — Team Fantastic 4

**DADS5001 — Data Analytics and Data Science Tools and Programming · Final Project**

A data-centric Streamlit app with an AI add-on, analyzing **168,589 public complaints**
from Bangkok's Traffy Fondue platform (July – December 2025) across all 50 districts.

> 📹 **Demo video:** _[add link here]_
> 🌐 **Live app:** [dads5001-finalproject-fantastic-4.streamlit.app](https://dads5001-finalproject-fantastic-4-zg4hptp4pvp6hyac7nwknp.streamlit.app)

---

## 🚨 Issues and Motivation

Bangkok citizens file thousands of complaints daily via Traffy Fondue — flooding,
broken roads, noise, waste, and more. The Bangkok Metropolitan Administration (BMA)
faces three challenges:

1. **Where** are problems concentrated, and which districts underperform?
2. **Which** problem types are slow to resolve or keep being reopened?
3. **How** can non-technical staff query this data without writing SQL?

## 🎯 Objective

Build a data-centric analytics application that turns raw complaint records into
actionable priorities for city management, with two modes of use:

- **Non-AI mode** — interactive dashboards, geographic maps, and a raw-data explorer
- **AI mode** — one-click AI insights on every page plus a RAG chatbot (Thai/English)

---

## 🛠️ Solution (Methodology)

### Data Pipeline

```
CSV files (Jul–Dec 2025)
   → Pandas + DuckDB        (cleaning, enrichment, type coercion)
   → MongoDB Atlas          (raw document store + text index for RAG)
   → Snowflake              (pre-aggregated analytics tables, key-pair auth)
   → Streamlit + Plotly     (visualization)
```

| Step | Script | Description |
|---|---|---|
| 1 | `pipeline_mongo.py` | Load 6 monthly CSVs → clean with Pandas/DuckDB → upsert to MongoDB with indexes |
| 2 | `pipeline_snowflake.py` | Pull from MongoDB → build aggregates with DuckDB → bulk-load to Snowflake |

**Local cache:** `data_cache/clean_df.parquet` — cleaned dataset cached locally to reduce MongoDB round-trips. App loads from Parquet first and falls back to MongoDB if not available.

### Non-AI Mode Pages

| Page | Primary Source | What it shows |
|---|---|---|
| 📊 Dashboard | MongoDB + DuckDB | KPIs, weekly ticket volume, top problem types, district rankings |
| 🗺️ Map | MongoDB | 168K geo-located complaints (pydeck), cascading filters, status distribution |
| 🔍 Explorer | MongoDB + DuckDB | Raw-record drill-down with cascading filters, keyword search, CSV export |
| ❄️ Snowflake Analytics | Snowflake | Severity matrix, reopen rates, satisfaction heatmap, district scorecard |

### AI Mode (toggle in sidebar)

Enabled via the **🤖 AI Mode** toggle in the sidebar — persists across all pages.

- **✨ AI Insight buttons** on every analytics page — sends current filtered data to **Groq `llama-3.1-8b-instant`** for actionable summaries
- **🤖 AI Assistant page** — RAG chatbot: MongoDB `$text` search retrieval (with regex fallback for Thai text) → context construction → Groq LLM answer, supports Thai and English

---

## ✅ Course Requirement Mapping

| Requirement | Implementation |
|---|---|
| Multi-page Streamlit app | `app.py` (st.navigation) + `home.py` + 5 pages in `pages/` |
| Pandas + DuckDB | `utils/queries.py`, `pages/4_🔍_Explorer.py`, both pipeline scripts |
| External cloud storage | MongoDB Atlas (`utils/db.py`) + Snowflake (RSA key-pair auth) |
| 2 modes (Non-AI / AI) | Sidebar **AI Mode** toggle (`utils/ui.py`), state persists via `session_state` |
| `st.cache_data` | All query functions in `utils/queries.py` and Snowflake loaders (TTL 1 h) |
| `st.cache_resource` | MongoDB client, Groq client (`utils/db.py`, `utils/rag.py`) |
| `st.session_state` | AI mode state (`ai_mode`), chat history, theme detection |

---

## 📊 Visualization

- **Plotly** — bar, line, scatter, pie, heatmap with a custom **dual-theme template** (`utils/theme.py`) that adapts to Streamlit's Light/Dark setting
- **pydeck** — GPS scatter-plot map of all 168K complaints
- **Styled DataFrames** — district scorecard with performance-tier color coding (green/amber/red)
- **Theme support** — Light and Dark modes detected via `st.context.theme`; backgrounds, text color, and chart templates all adapt automatically

---

## 🚀 How to Run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure credentials

```bash
cp .env.example .env   # fill in real values
```

Required credentials:

| Variable | Description |
|---|---|
| `MONGO_URI` | MongoDB Atlas connection string |
| `SNOWFLAKE_ACCOUNT` | Snowflake account identifier |
| `SNOWFLAKE_USER` | Snowflake username |
| `SNOWFLAKE_PRIVATE_KEY_PATH` | Path to `rsa_key.p8` |
| `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE` | RSA key passphrase (if set) |
| `GROQ_API_KEY` | Groq API key (for AI mode) |

> ⚠️ Never commit `.env` or `rsa_key.p8` — both are in `.gitignore`

### 3. Populate cloud storage (first time only)

```bash
python pipeline_mongo.py       # CSV → MongoDB
python pipeline_snowflake.py   # MongoDB aggregates → Snowflake
```

### 4. Launch the app

```bash
streamlit run app.py
```

---

## 📂 Project Structure

```
├── app.py                           # Entrypoint: st.navigation (defines page order)
├── home.py                          # Home page: hero, motivation, objective, pipeline overview
├── pages/
│   ├── 2_📊_Dashboard.py            # Analytics dashboard (MongoDB + DuckDB)
│   ├── 3_🗺️_Map.py                  # Geographic map (pydeck)
│   ├── 4_🔍_Explorer.py             # Raw data explorer (DuckDB in-memory filtering)
│   ├── 5_❄️_Snowflake_Analytics.py  # Deep-dive performance analytics (Snowflake)
│   └── 6_🤖_AI_Assistant.py         # RAG chatbot (AI mode only)
├── utils/
│   ├── db.py                        # Cached MongoDB + Snowflake connections
│   ├── queries.py                   # Cached DuckDB aggregation queries
│   ├── rag.py                       # MongoDB text search + Groq LLM (RAG)
│   ├── theme.py                     # Dual-theme CSS + Plotly template builder
│   └── ui.py                        # AI mode toggle (shared across pages)
├── pipeline_mongo.py                # ETL step 1: CSV → MongoDB
├── pipeline_snowflake.py            # ETL step 2: MongoDB aggregates → Snowflake
├── data_cache/
│   └── clean_df.parquet             # Local Parquet cache (auto-generated)
├── dataset/                         # Traffy Fondue monthly CSVs (Jul–Dec 2025)
├── .streamlit/
│   └── config.toml                  # Streamlit theme config (base: light)
├── requirements.txt
├── .env.example
└── benchmark_db.py                  # DB connection benchmark utility
```

---

## 👥 Team — Fantastic 4

| Student ID | Name | Responsibility |
|---|---|---|
| 6810422005 | Nanthiwat Tawilpri | Data pipeline & MongoDB |
| 6810422015 | Rachaphol Vongbuntoon | Snowflake & analytics pages |
| 6810422024 | Kumpon Sotsukpiam | AI integration & RAG |
| 6810422027 | Nutdanai Kaewhiran | Visualization & theming |

---

## 🙏 Data Source

[Traffy Fondue](https://www.traffy.in.th/) — Bangkok's public complaint platform,
dataset covering July – December 2025, provided for academic use.
