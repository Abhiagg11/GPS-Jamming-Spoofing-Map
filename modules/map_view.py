
import streamlit as st
import folium

from branca.element import MacroElement, Template, Element
from folium.plugins import Draw, Fullscreen, MousePosition
from streamlit_folium import st_folium


# ---------------------------------------------------------
# MAP SOURCES
# ---------------------------------------------------------

WORLD_STREET = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Street_Map/MapServer/tile/{z}/{y}/{x}"
)

WORLD_IMAGERY = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/tile/{z}/{y}/{x}"
)

IMAGERY_LABELS = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
)


# ---------------------------------------------------------
# AUTOMATIC BASEMAP SWITCH
# ---------------------------------------------------------

class BasemapSwitcher(MacroElement):

    def __init__(self, street, imagery, labels, switch_zoom=5):
        super().__init__()

        self.street = street.get_name()
        self.imagery = imagery.get_name()
        self.labels = labels.get_name()
        self.switch_zoom = switch_zoom

        self._template = Template("""
        {% macro script(this, kwargs) %}

        var map = {{ this._parent.get_name() }};

        var street = {{ this.street }};
        var imagery = {{ this.imagery }};
        var labels = {{ this.labels }};

        function updateBasemap() {

            var detailed = map.getZoom() >= {{ this.switch_zoom }};

            if (detailed) {

                if (map.hasLayer(street)) {
                    map.removeLayer(street);
                }

                if (!map.hasLayer(imagery)) {
                    map.addLayer(imagery);
                }

                if (!map.hasLayer(labels)) {
                    map.addLayer(labels);
                }

            } else {

                if (map.hasLayer(imagery)) {
                    map.removeLayer(imagery);
                }

                if (map.hasLayer(labels)) {
                    map.removeLayer(labels);
                }

                if (!map.hasLayer(street)) {
                    map.addLayer(street);
                }
            }
        }

        map.whenReady(updateBasemap);
        map.on("zoomend", updateBasemap);

        {% endmacro %}
        """)


# ---------------------------------------------------------
# MAIN MAP FUNCTION
# ---------------------------------------------------------

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

    # Create map
    m = folium.Map(
        location=[15, 0],
        zoom_start=2.7,
        min_zoom=2.7,
        max_zoom=19,
        zoom_snap=0.1,
        tiles=None,
        control_scale=True,
        prefer_canvas=True,
    )

    # Map styling
    css = """
    <style>
    .leaflet-container {
        background: #dce8ed !important;
        font-family: Arial, sans-serif;
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
    # GLOBAL STREET MAP
    # -----------------------------------------------------

    street = folium.TileLayer(
        tiles=WORLD_STREET,
        attr="© Esri, HERE, Garmin, USGS and contributors",
        name="Global Street Map",
        overlay=False,
        control=True,
        show=True,
        min_zoom=2,
        max_zoom=19,
        no_wrap=False,
    ).add_to(m)

    # -----------------------------------------------------
    # SATELLITE IMAGERY
    # -----------------------------------------------------

    imagery = folium.TileLayer(
        tiles=WORLD_IMAGERY,
        attr="Imagery © Esri, Maxar, Earthstar Geographics",
        name="Satellite Imagery",
        overlay=False,
        control=True,
        show=False,
        min_zoom=2,
        max_zoom=19,
        no_wrap=True,
    ).add_to(m)

    # -----------------------------------------------------
    # PLACE NAMES AND BOUNDARIES
    # -----------------------------------------------------

    labels = folium.TileLayer(
        tiles=IMAGERY_LABELS,
        attr="Labels © Esri and contributors",
        name="Place Names & Boundaries",
        overlay=True,
        control=True,
        show=False,
        opacity=1.0,
        max_zoom=19,
        no_wrap=True,
    ).add_to(m)

    # -----------------------------------------------------
    # INVESTIGATION MARKER
    # -----------------------------------------------------

    folium.CircleMarker(
        location=[latitude, longitude],
        radius=8,
        color="white",
        weight=3,
        fill=True,
        fill_color="#1677d2",
        fill_opacity=1,
        tooltip="Investigation Centre",
        popup=folium.Popup(
            f"""
            <b>Investigation Centre</b><br>
            Latitude: {latitude:.5f}<br>
            Longitude: {longitude:.5f}
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

    # Manual layer selector
    folium.LayerControl(
        position="topright",
        collapsed=True,
    ).add_to(m)

    # Automatic switching
    m.add_child(
        BasemapSwitcher(
            street=street,
            imagery=imagery,
            labels=labels,
            switch_zoom=5,
        )
    )

    # -----------------------------------------------------
    # DISPLAY
    # -----------------------------------------------------

    st.caption(
        "GLOBAL MAP  |  SATELLITE IMAGERY AT REGIONAL ZOOM  |  "
        "DRAW TO SELECT AN INVESTIGATION AREA"
    )

    result = st_folium(
        m,
        height=680,
        use_container_width=True,
        returned_objects=[
            "last_active_drawing",
            "all_drawings",
        ],
        key="position_loss_map",
    )

    # -----------------------------------------------------
    # RETURN DRAWN GEOMETRY
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
