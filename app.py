import streamlit as st
import pandas as pd
import folium
import requests
from io import BytesIO
from streamlit_folium import st_folium

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="GNSS Interference Investigator",
    page_icon="🛰️",
    layout="wide"
)

st.title("🛰️ GNSS Interference Investigator")
st.caption("Historical Flight Search | Route Visualization | GNSS Investigation")

# --------------------------------------------------
# LOAD AIRPORT DATABASE
# --------------------------------------------------

AIRPORT_DATA_URL = (
    "https://raw.githubusercontent.com/"
    "davidmegginson/ourairports-data/main/airports.csv"
)


@st.cache_data(ttl=86400)
def load_airports():
    response = requests.get(AIRPORT_DATA_URL, timeout=30)
    response.raise_for_status()

    airports = pd.read_csv(BytesIO(response.content))

    airports = airports[
        airports["type"].isin(["large_airport", "medium_airport"])
        & airports["iata_code"].notna()
    ]

    return airports


def find_airport(code, airports):
    code = code.strip().upper()

    if not code:
        return None

    result = airports[
        (airports["iata_code"].str.upper() == code)
        | (airports["ident"].str.upper() == code)
    ]

    if result.empty:
        return None

    return result.iloc[0]


# --------------------------------------------------
# AIRPORT SEARCH
# --------------------------------------------------

st.subheader("Flight Route Search")

try:
    airports = load_airports()

    col1, col2 = st.columns(2)

    with col1:
        departure = st.text_input(
            "Departure Airport",
            placeholder="Enter IATA / ICAO code (e.g. DEL)"
        )

    with col2:
        destination = st.text_input(
            "Destination Airport",
            placeholder="Enter IATA / ICAO code (e.g. LHR)"
        )

    if st.button("Show Route", type="primary"):
        dep_airport = find_airport(departure, airports)
        dest_airport = find_airport(destination, airports)

        if not departure or not destination:
            st.error("Please enter both airport codes.")

        elif dep_airport is None:
            st.error(f"Departure airport '{departure}' not found.")

        elif dest_airport is None:
            st.error(f"Destination airport '{destination}' not found.")

        elif dep_airport["ident"] == dest_airport["ident"]:
            st.error("Departure and destination cannot be the same.")

        else:
            st.session_state["route"] = {
                "departure": dep_airport.to_dict(),
                "destination": dest_airport.to_dict()
            }

    # --------------------------------------------------
    # WORLD MAP
    # --------------------------------------------------

    st.subheader("Flight Route Map")

    route = st.session_state.get("route")

    if route:
        dep = route["departure"]
        dest = route["destination"]

        center_lat = (
            dep["latitude_deg"] + dest["latitude_deg"]
        ) / 2

        center_lon = (
            dep["longitude_deg"] + dest["longitude_deg"]
        ) / 2

        zoom = 3

    else:
        center_lat = 20
        center_lon = 0
        zoom = 2

    flight_map = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=zoom,
    tiles=None
    )

    folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
    attr="Esri",
    name="Esri World Street Map",
    overlay=False,
    control=True
    )  .add_to(flight_map)

    if route:
        dep = route["departure"]
        dest = route["destination"]

        dep_coords = [
            dep["latitude_deg"],
            dep["longitude_deg"]
        ]

        dest_coords = [
            dest["latitude_deg"],
            dest["longitude_deg"]
        ]

        folium.Marker(
            dep_coords,
            tooltip=f"Departure: {dep['name']}",
            popup=f"{dep['iata_code']} - {dep['name']}",
            icon=folium.Icon(color="green", icon="plane")
        ).add_to(flight_map)

        folium.Marker(
            dest_coords,
            tooltip=f"Destination: {dest['name']}",
            popup=f"{dest['iata_code']} - {dest['name']}",
            icon=folium.Icon(color="red", icon="plane")
        ).add_to(flight_map)

        folium.PolyLine(
            [dep_coords, dest_coords],
            color="#00BFFF",
            weight=3,
            opacity=0.9,
            tooltip="Estimated airport-to-airport connection"
        ).add_to(flight_map)

        flight_map.fit_bounds([dep_coords, dest_coords])

        st.success(
            f"Route: {dep['iata_code']} → {dest['iata_code']}"
        )

        st.caption(
            "This is an estimated airport-to-airport connection, "
            "not an actual historical aircraft track."
        )

    map_data = st_folium(
        flight_map,
        width=None,
        height=700,
        returned_objects=[],
        key="gnss_world_map"
    )

except requests.RequestException as exc:
    st.error(f"Unable to download airport database: {exc}")

except Exception as exc:
    st.error(f"Application error: {exc}")
