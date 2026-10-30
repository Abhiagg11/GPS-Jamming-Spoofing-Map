from math import radians, sin, cos, asin, sqrt
import pandas as pd
from shapely.geometry import shape, Point

REQUIRED_COLUMNS = {"timestamp", "latitude", "longitude", "event_type", "confidence", "source"}

def haversine_km(lat1, lon1, lat2, lon2):
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 6371.0 * 2 * asin(sqrt(a))

def find_matching_reports(df, geometry, start_dt, end_dt, radius_km=100, time_window_minutes=30):
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        return pd.DataFrame(), ["Missing required columns: " + ", ".join(sorted(missing))]
    try:
        data = df.copy()
        data["latitude"] = pd.to_numeric(data["latitude"], errors="raise")
        data["longitude"] = pd.to_numeric(data["longitude"], errors="raise")
        if not data["latitude"].between(-90, 90).all() or not data["longitude"].between(-180, 180).all():
            return pd.DataFrame(), ["Latitude/longitude values must be valid decimal degrees."]
        data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True, errors="coerce")
        if data["timestamp"].isna().any():
            return pd.DataFrame(), ["Some timestamps could not be parsed. Use ISO 8601 timestamps with UTC (for example 2026-10-30T06:55:00Z)."]
        selected_shape = shape(geometry)
        # Geometry containment is used for polygon/rectangle/circle GeoJSON output where supported.
        # For a point or unsupported geometry, use distance from the marked location.
        geom_type = selected_shape.geom_type
        if geom_type in {"Polygon", "MultiPolygon"}:
            data["inside_marked_area"] = data.apply(lambda r: selected_shape.contains(Point(r["longitude"], r["latitude"])), axis=1)
            # Also include reports just outside the drawn boundary within the user-selected radius.
            centroid = selected_shape.centroid
            data["distance_km"] = data.apply(lambda r: haversine_km(centroid.y, centroid.x, r.latitude, r.longitude), axis=1)
            spatial = data["inside_marked_area"] | (data["distance_km"] <= radius_km)
        else:
            centroid = selected_shape
            data["distance_km"] = data.apply(lambda r: haversine_km(centroid.y, centroid.x, r.latitude, r.longitude), axis=1)
            data["inside_marked_area"] = data["distance_km"] == 0
            spatial = data["distance_km"] <= radius_km
        window_start = pd.Timestamp(start_dt) - pd.Timedelta(minutes=time_window_minutes)
        window_end = pd.Timestamp(end_dt) + pd.Timedelta(minutes=time_window_minutes)
        temporal = data["timestamp"].between(window_start, window_end)
        matches = data.loc[spatial & temporal].copy()
        matches = matches.sort_values(["timestamp", "distance_km"] if "distance_km" in matches else ["timestamp"])
        return matches, []
    except Exception as exc:
        return pd.DataFrame(), [f"Could not process evidence data: {exc}"]

def build_assessment(matches):
    if matches.empty:
        return "No matching records were found in the supplied dataset. This is not proof that GNSS interference was absent; dataset coverage, reporting delays and provider methodology may affect the result."
    types = ", ".join(sorted(matches["event_type"].astype(str).str.lower().unique()))
    sources = ", ".join(sorted(matches["source"].astype(str).unique()))
    return (
        f"Potentially relevant evidence was found: {len(matches)} record(s), event type(s): {types}. "
        f"Reported source(s): {sources}. Treat this as a lead for investigation, not confirmation of jamming or spoofing. "
        "Review the original provider reports, timestamps, aircraft navigation indicators and nearby-aircraft behaviour before drawing an operational conclusion."
    )
