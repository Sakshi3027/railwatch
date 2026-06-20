import duckdb
import pandas as pd
import numpy as np
import pickle
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score
import xgboost as xgb
import shap

DB_PATH = "data/railwatch.duckdb"
MODELS_DIR = Path("models")

def load_data():
    print("Loading data from DuckDB...")
    con = duckdb.connect(DB_PATH)
    df = con.execute("SELECT * FROM amtrak_delays").df()
    con.close()
    print(f"  Loaded {len(df)} rows")
    return df

def engineer_features(df):
    print("Engineering features...")
    df = df.copy()

    df["is_freight_rr"] = (df["host_railroad"] != "Amtrak").astype(int)
    df["is_long_distance"] = df["route"].isin([
        "Southwest Chief", "Empire Builder", "California Zephyr",
        "Coast Starlight", "Sunset Limited", "Texas Eagle",
        "Capitol Limited", "Lake Shore Limited"
    ]).astype(int)
    df["fti_ratio"] = df["freight_interference_min"] / (df["total_delay_minutes"] + 1)
    df["mechanical_ratio"] = df["mechanical_min"] / (df["total_delay_minutes"] + 1)
    df["weather_ratio"] = df["weather_min"] / (df["total_delay_minutes"] + 1)
    df["slow_orders_ratio"] = df["slow_orders_min"] / (df["total_delay_minutes"] + 1)
    df["passenger_ratio"] = df["passenger_min"] / (df["total_delay_minutes"] + 1)
    df["is_winter"] = df["month"].isin([12, 1, 2]).astype(int)
    df["is_summer"] = df["month"].isin([6, 7, 8]).astype(int)
    df["delay_severity"] = pd.cut(
        df["total_delay_minutes"],
        bins=[0, 1000, 3000, 6000, 99999],
        labels=[0, 1, 2, 3]
    ).astype(int)

    rr_encoder = LabelEncoder()
    df["host_rr_encoded"] = rr_encoder.fit_transform(df["host_railroad"])

    route_encoder = LabelEncoder()
    df["route_encoded"] = route_encoder.fit_transform(df["route"])

    return df, rr_encoder, route_encoder

FEATURES = [
    "is_freight_rr",
    "is_long_distance",
    "fti_ratio",
    "mechanical_ratio",
    "weather_ratio",
    "slow_orders_ratio",
    "passenger_ratio",
    "is_winter",
    "is_summer",
    "delay_severity",
    "host_rr_encoded",
    "route_encoded",
    "train_miles_10k",
    "fti_per_10k",
    "month",
    "year",
]

def train(df):
    print("\nTraining XGBoost delay attribution model...")

    target_encoder = LabelEncoder()
    df["label"] = target_encoder.fit_transform(df["primary_cause"])

    X = df[FEATURES]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"  Train: {len(X_train)} rows | Test: {len(X_test)} rows")

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=8,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=2,
        eval_metric="mlogloss",
        random_state=42,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\n  Accuracy: {acc:.2%}")
    print("\n  Classification Report:")
    print(classification_report(
        y_test, y_pred,
        target_names=target_encoder.classes_
    ))

    return model, target_encoder, X_test, y_test

def explain_with_shap(model, X_test):
    print("\nRunning SHAP explainability...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test)

    # shap_values shape: (n_samples, n_features, n_classes) — take mean across classes
    if isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
        mean_shap = np.abs(shap_values).mean(axis=(0, 2))
    elif isinstance(shap_values, list):
        mean_shap = np.mean([np.abs(sv).mean(axis=0) for sv in shap_values], axis=0)
    else:
        mean_shap = np.abs(shap_values).mean(axis=0)

    feature_importance = pd.DataFrame({
        "feature": FEATURES,
        "mean_shap": mean_shap.flatten()
    }).sort_values("mean_shap", ascending=False)

    print("\n  Top features by mean absolute SHAP value:")
    print(feature_importance.to_string(index=False))
    return feature_importance

def save_artifacts(model, target_encoder, rr_encoder, route_encoder, feature_importance):
    print("\nSaving model artifacts...")
    with open(MODELS_DIR / "xgb_model.pkl", "wb") as f:
        pickle.dump(model, f)
    with open(MODELS_DIR / "target_encoder.pkl", "wb") as f:
        pickle.dump(target_encoder, f)
    with open(MODELS_DIR / "rr_encoder.pkl", "wb") as f:
        pickle.dump(rr_encoder, f)
    with open(MODELS_DIR / "route_encoder.pkl", "wb") as f:
        pickle.dump(route_encoder, f)
    feature_importance.to_csv(MODELS_DIR / "feature_importance.csv", index=False)
    print("  Saved: xgb_model.pkl, encoders, feature_importance.csv")

if __name__ == "__main__":
    print("=== RailWatch Delay Attribution Model ===\n")
    df = load_data()
    df, rr_encoder, route_encoder = engineer_features(df)
    model, target_encoder, X_test, y_test = train(df)
    feature_importance = explain_with_shap(model, X_test)
    save_artifacts(model, target_encoder, rr_encoder, route_encoder, feature_importance)
    print("\nDone. Model ready for inference.")
