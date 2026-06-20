import os
import pickle
import duckdb
import pandas as pd
import numpy as np
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="RailWatch API",
    description="Freight interference accountability intelligence system for Amtrak",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "data/railwatch.duckdb"
MODELS_DIR = Path("models")

def get_db():
    return duckdb.connect(DB_PATH)

def load_model():
    with open(MODELS_DIR / "xgb_model.pkl", "rb") as f:
        model = pickle.load(f)
    with open(MODELS_DIR / "target_encoder.pkl", "rb") as f:
        target_encoder = pickle.load(f)
    with open(MODELS_DIR / "rr_encoder.pkl", "rb") as f:
        rr_encoder = pickle.load(f)
    with open(MODELS_DIR / "route_encoder.pkl", "rb") as f:
        route_encoder = pickle.load(f)
    return model, target_encoder, rr_encoder, route_encoder

# ── Health ──────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "service": "RailWatch API", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy"}

# ── KPIs ────────────────────────────────────────────────────────────────────

@app.get("/api/kpis")
def get_kpis():
    con = get_db()
    row = con.execute("""
        SELECT
            SUM(total_delay_minutes)          AS total_delay_min,
            SUM(freight_interference_min)     AS total_fti_min,
            ROUND(AVG(on_time_pct), 1)        AS avg_otp,
            ROUND(AVG(fti_per_10k), 1)        AS avg_fti_per_10k,
            COUNT(DISTINCT route)             AS total_routes,
            COUNT(DISTINCT host_railroad)     AS total_railroads
        FROM amtrak_delays
        WHERE year = 2024
    """).df().iloc[0]
    con.close()

    routes_failing = get_db().execute("""
        SELECT COUNT(*) AS cnt FROM route_risk_summary
        WHERE risk_level IN ('Critical', 'High')
    """).df().iloc[0]["cnt"]

    return {
        "total_delay_minutes": int(row["total_delay_min"]),
        "total_fti_minutes": int(row["total_fti_min"]),
        "avg_on_time_pct": float(row["avg_otp"]),
        "avg_fti_per_10k": float(row["avg_fti_per_10k"]),
        "total_routes": int(row["total_routes"]),
        "total_railroads": int(row["total_railroads"]),
        "routes_failing_fra_target": int(routes_failing),
    }

# ── Scorecard ────────────────────────────────────────────────────────────────

@app.get("/api/scorecard")
def get_scorecard():
    con = get_db()
    df = con.execute("SELECT * FROM host_railroad_scorecard").df()
    con.close()
    return df.to_dict(orient="records")

# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/api/routes")
def get_routes():
    con = get_db()
    df = con.execute("SELECT * FROM route_risk_summary").df()
    con.close()
    return df.to_dict(orient="records")

# ── Monthly trend ─────────────────────────────────────────────────────────────

@app.get("/api/trend")
def get_trend(host_railroad: str = None):
    con = get_db()
    if host_railroad:
        df = con.execute("""
            SELECT * FROM monthly_fti_trend
            WHERE host_railroad = ?
            ORDER BY year, month
        """, [host_railroad]).df()
    else:
        df = con.execute("""
            SELECT year, month,
                   ROUND(AVG(avg_fti_per_10k), 1) AS avg_fti_per_10k,
                   ROUND(AVG(avg_otp), 1)          AS avg_otp,
                   SUM(total_fti_min)              AS total_fti_min
            FROM monthly_fti_trend
            GROUP BY year, month
            ORDER BY year, month
        """).df()
    con.close()
    return df.to_dict(orient="records")

# ── Delays table ──────────────────────────────────────────────────────────────

@app.get("/api/delays")
def get_delays(year: int = 2024, host_railroad: str = None):
    con = get_db()
    if host_railroad:
        df = con.execute("""
            SELECT * FROM amtrak_delays
            WHERE year = ? AND host_railroad = ?
            ORDER BY fti_per_10k DESC
        """, [year, host_railroad]).df()
    else:
        df = con.execute("""
            SELECT * FROM amtrak_delays
            WHERE year = ?
            ORDER BY fti_per_10k DESC
        """, [year]).df()
    con.close()
    return df.to_dict(orient="records")

# ── Feature importance ────────────────────────────────────────────────────────

@app.get("/api/feature-importance")
def get_feature_importance():
    df = pd.read_csv(MODELS_DIR / "feature_importance.csv")
    return df.to_dict(orient="records")

# ── Predict ───────────────────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    route: str
    host_railroad: str
    month: int
    year: int
    total_delay_minutes: int
    train_miles_10k: float
    fti_per_10k: float

@app.post("/api/predict")
def predict(req: PredictRequest):
    model, target_encoder, rr_encoder, route_encoder = load_model()

    long_distance_routes = [
        "Southwest Chief", "Empire Builder", "California Zephyr",
        "Coast Starlight", "Sunset Limited", "Texas Eagle",
        "Capitol Limited", "Lake Shore Limited"
    ]

    try:
        rr_enc = rr_encoder.transform([req.host_railroad])[0]
    except ValueError:
        rr_enc = 0
    try:
        route_enc = route_encoder.transform([req.route])[0]
    except ValueError:
        route_enc = 0

    delay = req.total_delay_minutes
    features = np.array([[
        1 if req.host_railroad != "Amtrak" else 0,
        1 if req.route in long_distance_routes else 0,
        0.7, 0.08, 0.05, 0.12, 0.05,
        1 if req.month in [12, 1, 2] else 0,
        1 if req.month in [6, 7, 8] else 0,
        2 if delay > 3000 else (1 if delay > 1000 else 0),
        rr_enc, route_enc,
        req.train_miles_10k,
        req.fti_per_10k,
        req.month,
        req.year,
    ]])

    pred = model.predict(features)[0]
    proba = model.predict_proba(features)[0]
    label = target_encoder.inverse_transform([pred])[0]
    confidence = float(proba[pred])

    return {
        "predicted_cause": label,
        "confidence": round(confidence, 3),
        "probabilities": {
            cls: round(float(p), 3)
            for cls, p in zip(target_encoder.classes_, proba)
        }
    }
