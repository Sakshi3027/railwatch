import os
import requests
import pandas as pd
from pathlib import Path

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

SOURCES = {
    "ontime_2024": "https://www.bts.gov/sites/bts.dot.gov/files/docs/legacy/additional-attachment-files/Amtrak_OTP_2024.csv",
    "delays_by_cause": "https://www.bts.gov/sites/bts.dot.gov/files/table_01_73.csv",
}

def download_file(name: str, url: str) -> Path:
    print(f"Downloading {name}...")
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code == 200:
        out_path = RAW_DIR / f"{name}.csv"
        out_path.write_bytes(response.content)
        print(f"  Saved to {out_path} ({len(response.content)} bytes)")
        return out_path
    else:
        print(f"  Failed ({response.status_code}) — will use sample data instead")
        return None

def create_sample_data():
    print("\nCreating sample BTS delay dataset...")
    import random
    random.seed(42)

    routes = [
        "Southwest Chief", "Empire Builder", "California Zephyr",
        "Coast Starlight", "Sunset Limited", "Texas Eagle",
        "Capitol Limited", "Lake Shore Limited", "NE Regional", "Acela"
    ]
    host_rrs = {
        "Southwest Chief": "BNSF", "Empire Builder": "BNSF",
        "California Zephyr": "UP", "Coast Starlight": "UP",
        "Sunset Limited": "UP", "Texas Eagle": "UP",
        "Capitol Limited": "CSX", "Lake Shore Limited": "CSX",
        "NE Regional": "Amtrak", "Acela": "Amtrak"
    }
    delay_causes = ["freight_interference", "slow_orders", "mechanical", "weather", "passenger"]
    cause_weights = {
        "BNSF":   [0.72, 0.12, 0.08, 0.05, 0.03],
        "UP":     [0.68, 0.14, 0.09, 0.06, 0.03],
        "CSX":    [0.55, 0.18, 0.12, 0.10, 0.05],
        "Amtrak": [0.05, 0.05, 0.45, 0.20, 0.25],
    }

    rows = []
    for year in [2022, 2023, 2024]:
        for month in range(1, 13):
            for route in routes:
                rr = host_rrs[route]
                weights = cause_weights[rr]
                total_delay = random.randint(800, 8000) if rr != "Amtrak" else random.randint(100, 800)
                otp = random.uniform(0.38, 0.65) if rr != "Amtrak" else random.uniform(0.78, 0.94)
                train_miles = random.randint(8000, 15000)
                cause = random.choices(delay_causes, weights=weights)[0]
                rows.append({
                    "year": year,
                    "month": month,
                    "route": route,
                    "host_railroad": rr,
                    "total_delay_minutes": total_delay,
                    "on_time_pct": round(otp * 100, 1),
                    "train_miles_10k": round(train_miles / 10000, 2),
                    "fti_per_10k": round(total_delay / (train_miles / 10000), 1),
                    "primary_cause": cause,
                    "freight_interference_min": int(total_delay * weights[0]),
                    "slow_orders_min": int(total_delay * weights[1]),
                    "mechanical_min": int(total_delay * weights[2]),
                    "weather_min": int(total_delay * weights[3]),
                    "passenger_min": int(total_delay * weights[4]),
                })

    df = pd.DataFrame(rows)
    out_path = RAW_DIR / "amtrak_delays_sample.csv"
    df.to_csv(out_path, index=False)
    print(f"  Saved {len(df)} rows to {out_path}")
    print(f"\nSample data preview:")
    print(df.head(10).to_string(index=False))
    return df

if __name__ == "__main__":
    print("=== RailWatch BTS Data Downloader ===\n")
    success = False
    for name, url in SOURCES.items():
        result = download_file(name, url)
        if result:
            success = True
            break
    if not success:
        df = create_sample_data()
    print("\nDone. Check data/raw/ for output files.")
