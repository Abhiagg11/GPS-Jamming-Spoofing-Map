
import requests
import pandas as pd

BASE_URL = "https://adsb.aero/api/v1"
TIMEOUT = 30
MAX_AGE_DAYS = 6


class ADSBProviderError(Exception):
    pass


def _request(method, path, **kwargs):
    try:
        response = requests.request(
            method,
            f"{BASE_URL}{path}",
            timeout=TIMEOUT,
            **kwargs,
        )
        response.raise_for_status()
        return response.json()

    except requests.HTTPError as exc:
        try:
            detail = response.json()
            message = detail.get("hint") or detail.get("detail") or detail
        except Exception:
            message = str(exc)

        raise ADSBProviderError(
            f"ADS-B API error: {message}"
        ) from exc

    except requests.RequestException as exc:
        raise ADSBProviderError(
            f"Could not connect to ADS-B provider: {exc}"
        ) from exc


def _validate_date(flight_date):
    selected = pd.Timestamp(flight_date).date()
    today = pd.Timestamp.now(tz="UTC").date()

    if selected > today:
        raise ValueError("Future dates cannot be searched.")

    if (today - selected).days > MAX_AGE_DAYS:
        raise ValueError(
            "Only the latest 7 calendar days are supported."
        )


def get_data_range():
    return _request("GET", "/data-range")


def get_airport_geometry(airport_code):
    airport = _request(
        "GET",
        f"/airports/{airport_code.strip().upper()}",
    )

    airspaces = airport.get("airspaces") or []

    if airspaces:
        return airspaces[0]["geometry"]

    return {
        "type": "Circle",
        "coordinates": [airport["lon"], airport["lat"]],
        "radius": 9000,
    }


def _date_query(flight_date):
    selected = pd.Timestamp(flight_date, tz="UTC")

    return {
        "end_date": (
            selected + pd.Timedelta(days=1)
        ).isoformat().replace("+00:00", "Z"),
        "start_from": selected.isoformat().replace("+00:00", "Z"),
        "window_days": 7,
        "limit": 200,
        "include_path": False,
    }


def search_by_route(departure, destination, flight_date):
    _validate_date(flight_date)

    start_geometry = get_airport_geometry(departure)
    end_geometry = get_airport_geometry(destination)

    payload = {
        "match": {
            "and": [
                {
                    "endpoint_within": {
                        "mode": "start",
                        "geometry": start_geometry,
                    }
                },
                {
                    "endpoint_within": {
                        "mode": "end",
                        "geometry": end_geometry,
                    }
                },
            ]
        },
        **_date_query(flight_date),
    }

    result = _request("POST", "/query", json=payload)
    return result.get("flights", [])


def search_by_callsign(callsign, flight_date):
    _validate_date(flight_date)

    payload = {
        "match": {
            "callsign_prefix": callsign.strip().upper(),
        },
        **_date_query(flight_date),
    }

    result = _request("POST", "/query", json=payload)
    return result.get("flights", [])


def get_flight_track(flight_id):
    flight = _request(
        "GET",
        f"/flights/{flight_id}",
    )

    path = flight.get("path") or {}
    segments = path.get("coordinates") or []
    timestamps = flight.get("timestamps") or []

    track_points = []

    for segment_index, segment in enumerate(segments):
        segment_times = (
            timestamps[segment_index]
            if segment_index < len(timestamps)
            else []
        )

        for point_index, coordinate in enumerate(segment):
            if point_index >= len(segment_times):
                continue

            track_points.append({
                "timestamp": pd.to_datetime(
                    segment_times[point_index],
                    unit="s",
                    utc=True,
                ),
                "latitude": float(coordinate[1]),
                "longitude": float(coordinate[0]),
                "altitude_ft": (
                    float(coordinate[2])
                    if len(coordinate) > 2
                    else None
                ),
                "segment": segment_index,
            })

    track = pd.DataFrame(track_points)

    if not track.empty:
        track = track.sort_values(
            "timestamp"
        ).reset_index(drop=True)

    return flight, track


def detect_position_gaps(track, threshold_seconds=60):
    if track.empty or len(track) < 2:
        return pd.DataFrame()

    data = track.sort_values("timestamp").copy()

    data["previous_timestamp"] = data["timestamp"].shift(1)
    data["previous_latitude"] = data["latitude"].shift(1)
    data["previous_longitude"] = data["longitude"].shift(1)

    data["gap_seconds"] = (
        data["timestamp"] - data["previous_timestamp"]
    ).dt.total_seconds()

    gaps = data[
        data["gap_seconds"] > threshold_seconds
    ].copy()

    return gaps[[
        "previous_timestamp",
        "timestamp",
        "previous_latitude",
        "previous_longitude",
        "latitude",
        "longitude",
        "gap_seconds",
    ]].reset_index(drop=True)
