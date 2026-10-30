<<<<<<< HEAD
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json

import pandas as pd
import streamlit as st
from PIL import Image

from modules.screenshot_analysis import analyse_screenshot
from modules.map_view import render_investigation_map
from modules.investigation import find_matching_reports, build_assessment

ROOT = Path(__file__).parent

st.set_page_config(page_title="GNSS Interference Investigator", page_icon="🛰️", layout="wide")
st.title("🛰️ GNSS Interference Investigator")
st.caption("Flight monitoring investigation workspace · MVP v0.1")

with st.sidebar:
    st.header("Investigation")
    flight_id = st.text_input("Flight number / callsign", value="")
    event_date = st.date_input("Date of incident", value=datetime.now().date())
    loss_start = st.time_input("Position loss start (UTC)", value=datetime.now().replace(hour=7, minute=0, second=0).time())
    loss_end = st.time_input("Position loss end (UTC)", value=datetime.now().replace(hour=7, minute=15, second=0).time())
    radius_km = st.slider("Search radius (km)", min_value=10, max_value=500, value=100, step=10)
    time_window = st.slider("Time matching window (minutes)", min_value=5, max_value=180, value=30, step=5)
    st.divider()
    st.caption("MVP note: the app does not independently confirm jamming or spoofing. It compares the selected incident area/time with evidence you provide.")

st.subheader("1 · Upload and analyse a Mission Watch screenshot")
upload = st.file_uploader("Upload a flight route screenshot", type=["png", "jpg", "jpeg", "webp"])
analysis = None
if upload:
    try:
        image = Image.open(upload).convert("RGB")
        left, right = st.columns([1.15, 1])
        with left:
            st.image(image, caption="Uploaded screenshot", use_container_width=True)
        with right:
            with st.spinner("Analysing visible text and coordinate patterns…"):
                analysis = analyse_screenshot(image)
            st.markdown("**Automatically extracted information**")
            st.write("Flight / callsign:", analysis.get("flight_id") or "Not confidently detected")
            st.write("Coordinates detected:", analysis.get("coordinates_text") or "None detected")
            st.write("OCR status:", analysis.get("ocr_status"))
            st.write("Other useful text:")
            st.text(analysis.get("text_excerpt") or "No text extracted")
            if analysis.get("notes"):
                for note in analysis["notes"]:
                    st.caption("• " + note)
        if analysis.get("flight_id") and not flight_id:
            st.info(f"Possible flight identifier detected: {analysis['flight_id']}. Confirm it in the sidebar.")
    except Exception as exc:
        st.error(f"Could not read this image: {exc}")
else:
    st.info("Upload a screenshot to try automatic extraction. You can still proceed using manual coordinates below.")

st.divider()
st.subheader("2 · Confirm the affected geographical area")
st.write("Automatic screenshot reading is a helper, not a source of truth. Confirm the coordinates and draw or edit the affected area on the map.")

# Seed the initial map near the coordinate visible in the supplied example screenshot.
def_lat, def_lon = 0.0, 0.0
if analysis and analysis.get("first_coordinate"):
    suggested_lat, suggested_lon = analysis["first_coordinate"]
    st.info(f"OCR coordinate suggestion: {suggested_lat:.5f}, {suggested_lon:.5f}. This may be a cursor coordinate rather than the affected-area centre; verify it against the screenshot before using it.")
    use_ocr_coordinate = st.checkbox("Use this OCR coordinate as the initial map centre", value=False)
    if use_ocr_coordinate:
        def_lat, def_lon = suggested_lat, suggested_lon

c1, c2 = st.columns(2)
with c1:
    center_lat = st.number_input("Map centre latitude (decimal degrees)", min_value=-90.0, max_value=90.0, value=float(def_lat), format="%.5f")
with c2:
    center_lon = st.number_input("Map centre longitude (decimal degrees)", min_value=-180.0, max_value=180.0, value=float(def_lon), format="%.5f")

map_result = render_investigation_map(center_lat, center_lon)
selected_area = map_result.get("geometry") if map_result else None
if selected_area:
    st.success("A geographical area was drawn on the map. Review its shape before running the comparison.")
else:
    st.warning("No area drawn yet. Use the polygon or rectangle tool on the map to mark the ADS-B position-loss area.")

st.divider()
st.subheader("3 · Compare with GNSS interference evidence")
st.write("Upload an evidence CSV from a trusted source. The app will compare each report's location and timestamp with your selected incident area and time window.")
with st.expander("Evidence CSV format"):
    st.code("timestamp,latitude,longitude,event_type,confidence,source\n2026-10-30T06:55:00Z,8.90,2.16,jamming,medium,Example provider", language="csv")
    st.caption("The example row above is illustrative only, not a real interference report. Use UTC timestamps and cite the original data provider.")
evidence_file = st.file_uploader("Upload interference evidence CSV", type=["csv"], key="evidence_csv")

if st.button("Run investigation", type="primary", use_container_width=True):
    if not selected_area:
        st.error("Please draw the affected area on the map first.")
    elif not evidence_file:
        st.warning("No evidence dataset supplied. The map selection is saved only in this session; no conclusion about interference can be made yet.")
    else:
        try:
            evidence = pd.read_csv(evidence_file)
            start_dt = datetime.combine(event_date, loss_start).replace(tzinfo=timezone.utc)
            end_dt = datetime.combine(event_date, loss_end).replace(tzinfo=timezone.utc)
            if end_dt < start_dt:
                end_dt += timedelta(days=1)
            matches, validation_errors = find_matching_reports(
                evidence, selected_area, start_dt, end_dt,
                radius_km=radius_km, time_window_minutes=time_window
            )
            if validation_errors:
                st.error("Evidence file validation failed: " + "; ".join(validation_errors))
            else:
                assessment = build_assessment(matches)
                st.markdown("### Investigation output")
                st.metric("Matching evidence records", len(matches))
                st.info(assessment)
                if not matches.empty:
                    st.dataframe(matches, use_container_width=True, hide_index=True)
                else:
                    st.write("No matching records were found in the uploaded dataset for the selected area and time window. This does not prove that interference was absent.")
                st.download_button(
                    "Download matching evidence CSV",
                    data=matches.to_csv(index=False).encode("utf-8"),
                    file_name="gnss_interference_matches.csv",
                    mime="text/csv",
                )
        except Exception as exc:
            st.error(f"Investigation could not be completed: {exc}")

st.divider()
st.caption("This tool is an investigative aid, not an aviation safety system or an authoritative determination of GNSS jamming/spoofing. Validate findings against original provider data and operational procedures.")
=======
from datetime import datetime
from pathlib import Path

import streamlit as st
from PIL import Image

from modules.map_view import render_investigation_map
from modules.screenshot_analysis import analyse_screenshot

st.set_page_config(
    page_title="GPS Jamming & Spoofing Map",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("🛰️ GPS Jamming & Spoofing Map")
st.caption("Upload a Mission Watch screenshot, review any extracted details, then mark the affected area on the map.")

# Keep the first version deliberately simple: one upload area and one map.
upload = st.file_uploader(
    "Upload Mission Watch flight screenshot",
    type=["png", "jpg", "jpeg", "webp"],
    help="The image is processed in this app session. Do not upload confidential operational data to a public deployment.",
)

analysis = None
if upload is not None:
    try:
        image = Image.open(upload).convert("RGB")
        with st.expander("View uploaded screenshot", expanded=False):
            st.image(image, use_container_width=True)

        with st.spinner("Reading visible text from the screenshot…"):
            analysis = analyse_screenshot(image)

        st.subheader("Screenshot reading (check before using)")
        c1, c2, c3 = st.columns(3)
        c1.metric("Possible flight", analysis.get("flight_id") or "Not detected")
        c2.metric("Coordinate text", "Detected" if analysis.get("coordinates_text") else "Not detected")
        c3.metric("OCR", analysis.get("ocr_status", "Not run"))

        if analysis.get("coordinates_text"):
            st.write(f"**Coordinate text found:** `{analysis['coordinates_text']}`")
        if analysis.get("text_excerpt"):
            with st.expander("Review other text extracted from screenshot"):
                st.text(analysis["text_excerpt"])
        for note in analysis.get("notes", []):
            st.caption(f"ℹ️ {note}")
    except Exception as exc:
        st.error(f"The screenshot could not be read: {exc}")

st.divider()
st.subheader("Mark the ADS-B position-loss area")
st.write(
    "Use the drawing tools on the map to mark the approximate area where the aircraft position disappeared. "
    "You can draw a circle, rectangle or polygon, then edit or delete it."
)

# The supplied example flight is LOS–ABV, so this is a useful starting view only.
# It is not an automatically detected aircraft position.
with st.expander("Adjust map starting point", expanded=False):
    left, right = st.columns(2)
    with left:
        map_lat = st.number_input("Map centre latitude", min_value=-90.0, max_value=90.0, value=8.5, step=0.1, format="%.4f")
    with right:
        map_lon = st.number_input("Map centre longitude", min_value=-180.0, max_value=180.0, value=5.3, step=0.1, format="%.4f")
    st.caption("The initial view is centred near the Lagos–Abuja example route. Change it for other flights.")

map_result = render_investigation_map(map_lat, map_lon)

if map_result and map_result.get("geometry"):
    st.success("Area marked on the map. Review its position and shape before using it in an investigation.")
    st.download_button(
        "Download marked area (GeoJSON)",
        data=__import__("json").dumps(map_result["geometry"], indent=2),
        file_name="position-loss-area.geojson",
        mime="application/geo+json",
    )
else:
    st.info("No area marked yet. Use the polygon, rectangle or circle drawing tool on the map.")

st.divider()
st.caption(
    "Current MVP: screenshot text extraction and manual area marking only. It does not yet detect an ADS-B gap "
    "or confirm GPS jamming/spoofing. Those require validated flight-position data and independent interference evidence."
)
>>>>>>> 63b90d1 (new changed)
