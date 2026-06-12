# 🏙️ Bangkok Complaints Analytics — Team Fantastic 4

**DADS5001 — Data Analytics and Data Science Tools and Programming · Final Project**

A data-centric Streamlit app with an AI add-on, analyzing **168,589 public complaints**
from Bangkok's Traffy Fondue platform (July – December 2025) across all 50 districts.

> 📹 **Demo video:** _[add link here]_
> 🌐 **Live app:** _[add Streamlit Cloud link here]_

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

## 🛠️ Solution (Methodology)

### Data pipeline

```
CSV files (Jul–Dec 2025)
   → Pandas + DuckDB        (cleaning, enrichment, type coercion)
   → MongoDB Atlas          (raw document store + text index for RAG)
   → Snowflake              (pre-aggregated analytics tables, key-pair auth)
   → Streamlit + Plotly     (visualization)
```

| Step | Script | Description |
|---|---|---|
| 1 | `pipeline_mongo.py` | Load 6 monthly CSVs → clean with DuckDB → upsert to MongoDB with indexes |
| 2 | `pipeline_snowflake.py` | Pull from MongoDB → build aggregates with DuckDB → bulk-load to Snowflake |

### Non-AI mode

| Page | Source | What it shows |
|---|---|---|
| 📊 Dashboard | MongoDB + DuckDB | KPIs, weekly/monthly trends, top problem types, district rankings |
| 🗺️ Map | MongoDB | 168K geo-located complaints (pydeck), cascading filters, status distribution |
| 🔍 Explorer | MongoDB + DuckDB | Raw-record drill-down with cascading filters, keyword search, CSV export |
| ❄️ Snowflake Analytics | Snowflake | Severity matrix, reopen rates, satisfaction heatmap, district scorecard |

### AI mode (toggle in sidebar)

- **✨ AI Insight buttons** on every analytics page — the current filtered data is
  summarized and sent to **Groq (llama-3.1-8b-instant)** for actionable insights
- **🤖 AI Assistant** — RAG chatbot: MongoDB **$text search** retrieval (with regex
  fallback for Thai) → context construction → LLM answer, in Thai or English

## ✅ Course Requirement Mapping

| Requirement | Where |
|---|---|
| Multi-pages (Streamlit) | `app.py` + 5 pages in `pages/` |
| DuckDB + Pandas | `utils/queries.py`, `pages/4_🔍_Explorer.py`, both pipelines |
| External cloud storage | MongoDB Atlas (`utils/db.py`) + Snowflake (key-pair auth) |
| 2 modes (Non-AI vs AI) | Sidebar **AI Mode** toggle (`utils/ui.py`), persists across pages |
| `st.cache_data` | All query functions (`utils/queries.py`, Snowflake loaders, TTL 1 h) |
| `st.cache_resource` | MongoDB connection, Groq client (`utils/db.py`, `utils/rag.py`) |
| `st.session_state` | AI-mode state, chat history, theme memory |

## 📊 Visualization

Streamlit + **Plotly** (bar/line/pie/scatter/heatmap with a custom dual-theme
template) + **pydeck** (GPS scatter map) + styled **DataFrames** (scorecard with
performance-tier coloring). Full **Light/Dark theme** support — backgrounds, text,
and chart templates all follow the active Streamlit theme.

## 🚀 How to Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure secrets
cp .env.example .env          # then fill in real credentials

# 3. (First time only) Populate the cloud storage
python pipeline_mongo.py      # CSV → MongoDB
python pipeline_snowflake.py  # MongoDB → Snowflake

# 4. Launch the app
streamlit run app.py
```

**Credentials needed:** MongoDB Atlas URI · Snowflake account + RSA private key
(`SNOWFLAKE_PRIVATE_KEY_PATH`) · Groq API key. See `.env.example`.
Never commit `.env` or `rsa_key.p8`.

## 📂 Project Structure

```
├── app.py                      # Home: hero, motivation, objective, story flow
├── pages/
│   ├── 2_📊_Dashboard.py       # Non-AI analytics (MongoDB + DuckDB)
│   ├── 3_🗺️_Map.py             # Geographic distribution (pydeck)
│   ├── 4_🔍_Explorer.py        # Raw-data explorer (DuckDB SQL filtering)
│   ├── 5_❄️_Snowflake_Analytics.py  # Deep-dive performance analytics
│   └── 6_🤖_AI_Assistant.py    # RAG chatbot (AI mode only)
├── utils/
│   ├── db.py                   # Cached MongoDB / Snowflake connections
│   ├── queries.py              # Cached DuckDB aggregation queries
│   ├── rag.py                  # Text search + Groq LLM helpers
│   ├── theme.py                # Dual-theme CSS + Plotly template
│   └── ui.py                   # Shared AI-mode toggle
├── pipeline_mongo.py           # ETL step 1: CSV → MongoDB
├── pipeline_snowflake.py       # ETL step 2: MongoDB → Snowflake
├── dataset/                    # Traffy Fondue monthly CSVs (2025)
└── requirements.txt
```

## 👥 Team — Fantastic 4

| Name | Student ID | Responsibility |
|---|---|---|
| _[name]_ | _[id]_ | _[e.g. Data pipeline & MongoDB]_ |
| _[name]_ | _[id]_ | _[e.g. Snowflake & analytics pages]_ |
| _[name]_ | _[id]_ | _[e.g. AI integration & RAG]_ |
| _[name]_ | _[id]_ | _[e.g. Visualization & theming]_ |

## 🙏 Data Source

[Traffy Fondue](https://www.traffy.in.th/) — Bangkok public complaint platform,
data covering July – December 2025.
