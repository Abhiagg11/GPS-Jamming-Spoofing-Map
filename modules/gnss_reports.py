import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_FILE = PROJECT_ROOT / "data" / "gnss_reports.csv"
REQUIRED_COLUMNS = ["timestamp", "latitude", "longitude", "event_type", "confidence", "source"]

def load_gnss_reports():
    if not REPORT_FILE.exists():
        return pd.DataFrame(columns=REQUIRED_COLUMNS), [f"Report file not found: {REPORT_FILE}"]
    try:
        df = pd.read_csv(REPORT_FILE)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=REQUIRED_COLUMNS), ["The GNSS report CSV is empty."]
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        return pd.DataFrame(columns=REQUIRED_COLUMNS), [f"Missing columns: {', '.join(missing)}"]
    if df.empty:
        return pd.DataFrame(columns=REQUIRED_COLUMNS), []
    df = df[REQUIRED_COLUMNS].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    valid = df["timestamp"].notna() & df["latitude"].between(-90, 90) & df["longitude"].between(-180, 180)
    errors = []
    invalid_count = int((~valid).sum())
    if invalid_count:
        errors.append(f"{invalid_count} invalid report row(s) skipped.")
    df = df[valid].copy()
    df["event_type"] = df["event_type"].fillna("unknown").astype(str).str.lower()
    df["confidence"] = df["confidence"].fillna("unknown").astype(str)
    df["source"] = df["source"].fillna("unknown").astype(str)
    return df.reset_index(drop=True), errors
