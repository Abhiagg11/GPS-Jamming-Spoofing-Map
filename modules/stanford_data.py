
import json
from pathlib import Path

import h3


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = PROJECT_ROOT / "downloaded_json_files"


def read_json(path):
    """Read a Stanford JSON file safely."""
    if not path.exists():
        return {}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        print(f"Could not read {path}: {error}")
        return {}


def extract_date(file):
    """Extract YYYY-MM-DD from YYYY/MM/DD folder structure."""
    return (
        f"{file.parent.parent.parent.name}-"
        f"{file.parent.parent.name}-"
        f"{file.parent.name}"
    )


def valid_h3_cell(cell_id):
    """Check whether the supplied H3 index is valid."""
    try:
        return h3.is_valid_cell(cell_id)
    except (TypeError, ValueError):
        return False


def load_event_points(start_date, end_date):
    """Load Stanford jamming and spoofing event locations."""
    events = []

    for event_type in ["jamming", "spoofing"]:
        folder = DATA_ROOT / event_type

        if not folder.exists():
            continue

        for file in sorted(folder.glob("**/events.json")):
            date = extract_date(file)

            if not start_date <= date <= end_date:
                continue

            payload = read_json(file)

            for item in payload.get("data", []):
                try:
                    latitude = float(item["latitude"])
                    longitude = float(item["longitude"])

                    if not (-90 <= latitude <= 90):
                        continue

                    if not (-180 <= longitude <= 180):
                        continue

                    events.append({
                        "event_id": str(item.get("eventId", "")),
                        "date": date,
                        "event_type": event_type,
                        "latitude": latitude,
                        "longitude": longitude,
                        "start_time": item.get("startTime"),
                        "end_time": item.get("endTime"),
                        "affected_flights": item.get("numFltAffected"),
                        "source": "Stanford GPS Lab",
                    })

                except (KeyError, TypeError, ValueError):
                    continue

    return events


def load_jamming_cells(start_date, end_date):
    """Load Stanford jamming H3 heatmap cells."""
    cells = []
    folder = DATA_ROOT / "jamming"

    if not folder.exists():
        return cells

    for file in sorted(folder.glob("**/heatmap.json")):
        date = extract_date(file)

        if not start_date <= date <= end_date:
            continue

        payload = read_json(file)

        for item in payload.get("data", []):
            try:
                cell_id = item["h3Index"]

                if not valid_h3_cell(cell_id):
                    continue

                latitude, longitude = h3.cell_to_latlng(cell_id)

                boundary = [
                    [lat, lon]
                    for lat, lon in h3.cell_to_boundary(cell_id)
                ]

                cells.append({
                    "cell_id": cell_id,
                    "date": date,
                    "event_type": "jamming",
                    "latitude": latitude,
                    "longitude": longitude,
                    "boundary": boundary,
                    "low_quality_count": item.get("lowQualityCount", 0),
                    "total_aircraft_count": item.get("totalAircraftCount", 0),
                    "source": "Stanford GPS Lab",
                })

            except (KeyError, TypeError, ValueError):
                continue

    return cells


def load_spoofing_cells(start_date, end_date):
    """Load Stanford spoofing H3 cells grouped by event ID."""
    cells = []
    folder = DATA_ROOT / "spoofing"

    if not folder.exists():
        return cells

    for file in sorted(folder.glob("**/heatmap.json")):
        date = extract_date(file)

        if not start_date <= date <= end_date:
            continue

        payload = read_json(file)
        event_groups = payload.get("data", {})

        for event_id, records in event_groups.items():
            if not isinstance(records, list):
                continue

            for item in records:
                try:
                    cell_id = item["h3Index"]

                    if not valid_h3_cell(cell_id):
                        continue

                    latitude, longitude = h3.cell_to_latlng(cell_id)

                    boundary = [
                        [lat, lon]
                        for lat, lon in h3.cell_to_boundary(cell_id)
                    ]

                    cells.append({
                        "cell_id": cell_id,
                        "date": date,
                        "event_id": str(event_id),
                        "event_type": "spoofing",
                        "latitude": latitude,
                        "longitude": longitude,
                        "boundary": boundary,
                        "spoofed_flight_count": item.get(
                            "spoofedFlightCount", 0
                        ),
                        "seen_aircraft_count": item.get(
                            "seenAircraftCount", 0
                        ),
                        "source": "Stanford GPS Lab",
                    })

                except (KeyError, TypeError, ValueError):
                    continue

    return cells


def load_stanford_data(start_date, end_date):
    """Load Stanford events and heatmap cells for a date range."""

    return {
        "events": load_event_points(start_date, end_date),
        "jamming_cells": load_jamming_cells(start_date, end_date),
        "spoofing_cells": load_spoofing_cells(start_date, end_date),
    }
