# RailWatch

Freight interference accountability intelligence system for Amtrak passenger rail.

## Live Demo

- **Dashboard**: https://railwatch-smoky.vercel.app
- **API**: https://railwatch-api.onrender.com/docs
- **GitHub**: https://github.com/Sakshi3027/railwatch

## The Problem

Freight train interference caused 850,000 minutes of delay to Amtrak passengers in 2024. Host railroads are legally required to give Amtrak preference under the Rail Passenger Service Act — but violations are hard to detect, attribute, and escalate at scale.

RailWatch is an internal-grade intelligence tool that detects, attributes, and tracks host railroad violations using public BTS data and Amtrak's own Host Railroad Report Card metrics.

## What It Does

- **Delay Attribution Engine** — XGBoost classifier that labels every delay event by root cause: freight interference, slow orders, mechanical, weather, or passenger-caused
- **Host Railroad Scorecard** — letter grades per railroad computed using Amtrak's own FTI metric (delay minutes per 10,000 train-miles)
- **LangGraph Agent** — reads monthly Host Railroad PDFs, runs attribution model, generates structured escalation briefings automatically
- **Analytics Dashboard** — route-level and railroad-level analyst view with live risk indicators
- **Live Train Map** — real-time Amtrak train positions via GTFS-RT feed with delay status overlaid

## Tech Stack

| Layer | Technology |
|---|---|
| Data ingestion | dlt + DuckDB |
| ML model | XGBoost + SHAP |
| Vector store | Qdrant Cloud |
| Agent orchestration | LangGraph + Groq |
| Observability | LangSmith |
| Backend | FastAPI |
| Frontend | Next.js + Recharts + Mapbox GL |
| Scheduler | Modal |
| Deploy | Render + Vercel |
| CI/CD | GitHub Actions |

## Data Sources

All free and public:
- BTS On-Time Performance data (bts.gov)
- Amtrak Host Railroad Report Cards (monthly PDFs)
- Amtrak GTFS static schedule feed
- Amtrak GTFS-RT real-time train positions
- NOAA Weather API

## Project Structure
railwatch/

├── data/              # Raw and processed BTS + Amtrak data

├── pipeline/          # dlt ingestion scripts

├── models/            # XGBoost training and SHAP explainability

├── agent/             # LangGraph agent nodes and graph

├── backend/           # FastAPI routes and API layer

├── frontend/          # Next.js dashboard

├── notebooks/         # EDA and model analysis

└── .github/workflows/ # CI/CD pipelines

## Author

Sakshi Chavan — [github.com/Sakshi3027](https://github.com/Sakshi3027) · [Medium @SakshiChavan](https://medium.com/@SakshiChavan)
