import requests
import streamlit as st
import folium

from branca.element import Element
from folium.plugins import Draw, Fullscreen, MousePosition
from streamlit_folium import st_folium


# =========================================================
# MAP TILE SOURCES
# =========================================================

LIGHT_BASE = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
)

LIGHT_LABELS = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}"
)

DARK_BASE = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
)

DARK_LABELS = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}"
)


# Zoom settings
MIN_TILE_ZOOM = 2.8
MAX_TILE_ZOOM = 19
MAX_NATIVE_TILE_ZOOM = 16


# =========================================================
# LOCATION SEARCH
# =========================================================

@st.cache_data(ttl=86400, show_spinner=False)
def search_location(query):

    response = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={
            "q": query,
            "format": "jsonv2",
            "limit": 1,
        },
        headers={
            "User-Agent": "GNSS-Interference-Investigator/1.0"
        },
        timeout=15,
    )

    response.raise_for_status()
    results = response.json()

    if not results:
        return None

    return {
        "latitude": float(results[0]["lat"]),
        "longitude": float(results[0]["lon"]),
        "name": results[0].get("display_name", query),
    }


def parse_coordinates(query):

    try:
        parts = [part.strip() for part in query.split(",")]

        if len(parts) != 2:
            return None

        latitude = float(parts[0])
        longitude = float(parts[1])

        if not -90 <= latitude <= 90:
            return None

        if not -180 <= longitude <= 180:
            return None

        return latitude, longitude

    except (ValueError, TypeError):
        return None


# =========================================================
# MAIN MAP FUNCTION
# =========================================================

def render_investigation_map(latitude=9.0, longitude=7.0):

    # Validate coordinates

    try:
        latitude = float(latitude)
        longitude = float(longitude)

        if not -90 <= latitude <= 90:
            latitude = 9.0

        if not -180 <= longitude <= 180:
            longitude = 7.0

    except (TypeError, ValueError):
        latitude = 9.0
        longitude = 7.0

    # Session state

    if "investigation_map_center" not in st.session_state:
        st.session_state.investigation_map_center = [
            latitude, longitude
        ]

    if "investigation_map_zoom" not in st.session_state:
        st.session_state.investigation_map_zoom = 2.7

    if "investigation_map_search_name" not in st.session_state:
        st.session_state.investigation_map_search_name = ""

    if "investigation_map_theme" not in st.session_state:
        st.session_state.investigation_map_theme = "Light"

    if "investigation_show_labels" not in st.session_state:
        st.session_state.investigation_show_labels = True

    # -----------------------------------------------------
    # MAP TOOLBAR
    # -----------------------------------------------------

    st.markdown("##### Map controls")

    theme_col, labels_col, global_col, reset_col, search_col = (
        st.columns([1.0, 1.5, 1.0, 0.8, 3.0], gap="small")
    )

    with theme_col:

        map_theme = st.selectbox(
            "Map appearance",
            ["Light", "Dark"],
            key="investigation_map_theme",
        )

    with labels_col:

        show_labels = st.checkbox(
            "Show country and city labels",
            key="investigation_show_labels",
        )

    with global_col:

        st.write("")

        if st.button("🌍 Global view", use_container_width=True):

            st.session_state.investigation_map_center = [15.0, 0.0]
            st.session_state.investigation_map_zoom = 2.7
            st.session_state.investigation_map_search_name = ""

            st.rerun()

    with reset_col:

        st.write("")

        if st.button("↺ Reset", use_container_width=True):

            st.session_state.investigation_map_center = [
                latitude, longitude
            ]

            st.session_state.investigation_map_zoom = 2.7
            st.session_state.investigation_map_search_name = ""

            st.rerun()

    with search_col:

        with st.form("investigation_location_search"):

            search_col1, search_col2 = st.columns(
                [4, 1],
                gap="small",
            )

            with search_col1:

                location_query = st.text_input(
                    "Search location",
                    placeholder="City, country or latitude, longitude",
                    label_visibility="collapsed",
                )

            with search_col2:

                search_submitted = st.form_submit_button(
                    "🔎 Search",
                    use_container_width=True,
                )

        if search_submitted:

            if not location_query.strip():

                st.warning("Enter a location to search.")

            else:

                coordinates = parse_coordinates(
                    location_query.strip()
                )

                try:

                    if coordinates:

                        new_latitude, new_longitude = coordinates
                        location_name = "Entered coordinates"

                    else:

                        with st.spinner("Searching location..."):

                            location = search_location(
                                location_query.strip()
                            )

                        if not location:

                            st.error("Location not found. Try another search.")
                            location_name = None

                        else:

                            new_latitude = location["latitude"]
                            new_longitude = location["longitude"]
                            location_name = location["name"]

                    if location_name:

                        st.session_state.investigation_map_center = [
                            new_latitude,
                            new_longitude,
                        ]

                        st.session_state.investigation_map_zoom = 7

                        st.session_state.investigation_map_search_name = (
                            location_name
                        )

                        st.rerun()

                except requests.RequestException as exc:

                    st.error(f"Location search failed: {exc}")

    # -----------------------------------------------------
    # CURRENT MAP POSITION
    # -----------------------------------------------------

    map_lat, map_lon = (
        st.session_state.investigation_map_center
    )

    map_zoom = st.session_state.investigation_map_zoom

    map_zoom = max(
        MIN_TILE_ZOOM,
        min(MAX_TILE_ZOOM, float(map_zoom)),
    )

    # -----------------------------------------------------
    # CREATE MAP
    # -----------------------------------------------------

    m = folium.Map(
        location=[map_lat, map_lon],
        zoom_start=map_zoom,
        min_zoom=MIN_TILE_ZOOM,
        max_zoom=MAX_TILE_ZOOM,
        zoom_snap=0.1,
        tiles=None,
        control_scale=True,
        prefer_canvas=True,
    )

    # -----------------------------------------------------
    # MAP STYLING
    # -----------------------------------------------------

    css = """
    <style>
        .leaflet-container {
            font-family: Arial, sans-serif;
            background: #dce4ec !important;
        }

        .leaflet-control {
            border-radius: 7px !important;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2) !important;
        }

        .leaflet-control-mouseposition {
            background: rgba(255,255,255,0.95);
            padding: 5px 9px;
            border-radius: 5px;
            font-size: 12px;
            color: #263746;
        }
    </style>
    """

    m.get_root().header.add_child(Element(css))

    # -----------------------------------------------------
    # SELECT LIGHT OR DARK BASEMAP
    # -----------------------------------------------------

    if map_theme == "Light":

        base_tiles = LIGHT_BASE
        label_tiles = LIGHT_LABELS

    else:

        base_tiles = DARK_BASE
        label_tiles = DARK_LABELS

    base_attribution = (
        "Sources: Esri, HERE, Garmin, "
        "© OpenStreetMap contributors, GIS community"
    )

    label_attribution = (
        "Labels: Esri, HERE, Garmin and contributors"
    )

    # -----------------------------------------------------
    # BASE MAP
    # -----------------------------------------------------

    folium.TileLayer(
        tiles=base_tiles,
        attr=base_attribution,
        name=f"{map_theme} Map",
        overlay=False,
        control=False,
        show=True,
        min_zoom=MIN_TILE_ZOOM,
        max_zoom=MAX_TILE_ZOOM,
        max_native_zoom=MAX_NATIVE_TILE_ZOOM,
        no_wrap=True,
    ).add_to(m)

    # -----------------------------------------------------
    # COUNTRY AND CITY LABELS
    # -----------------------------------------------------

    if show_labels:

        folium.TileLayer(
            tiles=label_tiles,
            attr=label_attribution,
            name="Country and City Labels",
            overlay=True,
            control=False,
            show=True,
            opacity=1.0,
            min_zoom=MIN_TILE_ZOOM,
            max_zoom=MAX_TILE_ZOOM,
            max_native_zoom=MAX_NATIVE_TILE_ZOOM,
            no_wrap=False,
        ).add_to(m)

    # -----------------------------------------------------
    # INVESTIGATION CENTRE MARKER
    # -----------------------------------------------------

    folium.CircleMarker(
        location=[map_lat, map_lon],
        radius=7,
        color="white",
        weight=3,
        fill=True,
        fill_color="#1677d2",
        fill_opacity=1,
        tooltip="Map Focus",
        popup=folium.Popup(
            f"""
            <b>Map Focus</b><br>
            Latitude: {map_lat:.5f}<br>
            Longitude: {map_lon:.5f}
            """,
            max_width=250,
        ),
    ).add_to(m)

    # -----------------------------------------------------
    # DRAWING TOOLS
    # -----------------------------------------------------

    Draw(
        export=False,
        position="topleft",
        draw_options={
            "polyline": False,
            "marker": True,
            "circle": True,
            "circlemarker": False,
            "rectangle": True,
            "polygon": True,
        },
        edit_options={
            "edit": True,
            "remove": True,
        },
    ).add_to(m)

    # -----------------------------------------------------
    # MAP CONTROLS
    # -----------------------------------------------------

    Fullscreen(position="topright").add_to(m)

    MousePosition(
        position="bottomleft",
        separator=" | ",
        prefix="Coordinates:",
        num_digits=5,
    ).add_to(m)

    # -----------------------------------------------------
    # LOCATION INFORMATION
    # -----------------------------------------------------

    if st.session_state.investigation_map_search_name:

        st.caption(
            "Map location: "
            f"{st.session_state.investigation_map_search_name}"
        )

    # -----------------------------------------------------
    # DISPLAY MAP
    # -----------------------------------------------------

    result = st_folium(
        m,
        height=760,
        use_container_width=True,
        returned_objects=[
            "last_active_drawing",
            "all_drawings",
        ],
        key="position_loss_map",
    )

    # -----------------------------------------------------
    # RETURN DRAWN AREA
    # -----------------------------------------------------

    drawing = None

    if result:

        drawing = result.get("last_active_drawing")

        if not drawing:

            drawings = result.get("all_drawings") or []

            if drawings:
                drawing = drawings[-1]

    if drawing and drawing.get("geometry"):

        return {
            "geometry": drawing["geometry"],
            "properties": drawing.get("properties", {}),
        }

    return None