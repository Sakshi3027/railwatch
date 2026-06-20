import duckdb
import pandas as pd
from pathlib import Path

DB_PATH = "data/railwatch.duckdb"
RAW_PATH = "data/raw/amtrak_delays_sample.csv"

def ingest():
    print("=== RailWatch DuckDB Ingestion ===\n")
    con = duckdb.connect(DB_PATH)

    df = pd.read_csv(RAW_PATH)
    print(f"Loaded {len(df)} rows from {RAW_PATH}")

    con.execute("DROP TABLE IF EXISTS amtrak_delays")
    con.execute("""
        CREATE TABLE amtrak_delays AS
        SELECT * FROM df
    """)
    print("Created table: amtrak_delays")

    con.execute("""
        CREATE OR REPLACE VIEW host_railroad_scorecard AS
        SELECT
            host_railroad,
            ROUND(AVG(fti_per_10k), 1)         AS avg_fti_per_10k,
            ROUND(AVG(on_time_pct), 1)          AS avg_otp,
            SUM(total_delay_minutes)             AS total_delay_min,
            SUM(freight_interference_min)        AS total_fti_min,
            COUNT(*)                             AS records,
            CASE
                WHEN AVG(fti_per_10k) < 600  THEN 'A'
                WHEN AVG(fti_per_10k) < 800  THEN 'B'
                WHEN AVG(fti_per_10k) < 1000 THEN 'C'
                WHEN AVG(fti_per_10k) < 1200 THEN 'D'
                ELSE 'F'
            END AS grade
        FROM amtrak_delays
        GROUP BY host_railroad
        ORDER BY avg_fti_per_10k DESC
    """)
    print("Created view: host_railroad_scorecard")

    con.execute("""
        CREATE OR REPLACE VIEW monthly_fti_trend AS
        SELECT
            year,
            month,
            host_railroad,
            ROUND(AVG(fti_per_10k), 1) AS avg_fti_per_10k,
            ROUND(AVG(on_time_pct), 1) AS avg_otp,
            SUM(freight_interference_min) AS total_fti_min
        FROM amtrak_delays
        GROUP BY year, month, host_railroad
        ORDER BY year, month, host_railroad
    """)
    print("Created view: monthly_fti_trend")

    con.execute("""
        CREATE OR REPLACE VIEW route_risk_summary AS
        SELECT
            route,
            host_railroad,
            ROUND(AVG(fti_per_10k), 1) AS avg_fti_per_10k,
            ROUND(AVG(on_time_pct), 1) AS avg_otp,
            CASE
                WHEN AVG(fti_per_10k) > 1100 THEN 'Critical'
                WHEN AVG(fti_per_10k) > 900  THEN 'High'
                WHEN AVG(fti_per_10k) > 600  THEN 'Medium'
                ELSE 'Normal'
            END AS risk_level
        FROM amtrak_delays
        GROUP BY route, host_railroad
        ORDER BY avg_fti_per_10k DESC
    """)
    print("Created view: route_risk_summary")

    print("\n=== HOST RAILROAD SCORECARD ===")
    print(con.execute("SELECT * FROM host_railroad_scorecard").df().to_string(index=False))

    print("\n=== ROUTE RISK SUMMARY ===")
    print(con.execute("SELECT * FROM route_risk_summary").df().to_string(index=False))

    con.close()
    print(f"\nDatabase saved to {DB_PATH}")

if __name__ == "__main__":
    ingest()
