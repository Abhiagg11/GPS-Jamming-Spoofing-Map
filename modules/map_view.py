
import folium
import streamlit as st
from folium.plugins import Draw, Fullscreen, MousePosition
from streamlit_folium import st_folium


def render_investigation_map(latitude=9.0, longitude=7.0):

    # Create map centred around the investigation area
    m = folium.Map(
        location=[latitude, longitude],
        zoom_start=6,
        min_zoom=3,
        max_zoom=18,
        control_scale=True,
        tiles=None,
        prefer_canvas=True,
    )

    # Street map
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attr="© OpenStreetMap contributors © CARTO",
        name="Street Map",
        subdomains=["a", "b", "c", "d"],
        max_zoom=20,
        no_wrap=True,
        overlay=False,
        control=True,
    ).add_to(m)

    # Satellite imagery
    folium.TileLayer(
        tiles=(
            "https://server.arcgisonline.com/ArcGIS/rest/services/"
            "World_Imagery/MapServer/tile/{z}/{y}/{x}"
        ),
        attr="Tiles © Esri",
        name="Satellite View",
        max_zoom=19,
        no_wrap=True,
        overlay=False,
        control=True,
    ).add_to(m)

    # Investigation centre marker
    folium.Marker(
        location=[latitude, longitude],
        tooltip="Investigation area",
        popup=(
            f"Latitude: {latitude:.5f}<br>"
            f"Longitude: {longitude:.5f}"
        ),
        icon=folium.Icon(
            color="blue",
            icon="info-sign",
        ),
    ).add_to(m)

    # Drawing tools
    Draw(
        export=False,
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

    # Fullscreen
    Fullscreen(
        position="topright",
    ).add_to(m)

    # Coordinates
    MousePosition(
        position="bottomleft",
        separator=" | ",
        prefix="Lat/Lon:",
        num_digits=5,
    ).add_to(m)

    # Map layer selector
    folium.LayerControl(
        position="topright",
        collapsed=True,
    ).add_to(m)

    # Render map
    result = st_folium(
        m,
        height=650,
        use_container_width=True,
        returned_objects=[
            "last_active_drawing",
            "all_drawings",
        ],
        key="position_loss_map",
    )

    # Capture manually selected area
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