
import pandas as pd
from pathlib import Path

# Locate airport database
PROJECT_ROOT = Path(__file__).resolve().parent.parent
AIRPORT_FILE = PROJECT_ROOT / "data" / "airports.csv"


def load_airports():
    """Load airport reference data."""

    if not AIRPORT_FILE.exists():
        raise FileNotFoundError(
            f"Airport database not found: {AIRPORT_FILE}"
        )

    df = pd.read_csv(AIRPORT_FILE)

    # Keep useful airport fields
    columns = [
        "ident",
        "type",
        "name",
        "latitude_deg",
        "longitude_deg",
        "iso_country",
        "municipality",
        "icao_code",
        "iata_code",
    ]

    df = df[columns]

    # Keep airports with valid coordinates
    df = df.dropna(
        subset=["latitude_deg", "longitude_deg"]
    )

    return df


def search_airport(code):
    """Search airport using IATA or ICAO code."""

    airports = load_airports()

    code = code.strip().upper()

    result = airports[
        (airports["iata_code"].fillna("").str.upper() == code)
        | (airports["icao_code"].fillna("").str.upper() == code)
    ]

    return result
