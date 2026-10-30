import folium
import streamlit as st
from folium.plugins import Draw, Fullscreen, MousePosition
from streamlit_folium import st_folium


def render_investigation_map(latitude: float, longitude: float):
    """Render a simple map with drawing tools for manually marking a position-loss area."""
    m = folium.Map(
        location=[latitude, longitude],
        zoom_start=6,
        control_scale=True,
        tiles=None,
    )

    # CARTO basemap avoids the OpenStreetMap standard tile endpoint that was
    # returning 403 errors in the user's Codespaces preview.
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        name="Light map",
        subdomains="abcd",
        max_zoom=20,
        control=True,
    ).add_to(m)

    folium.Marker(
        [latitude, longitude],
        tooltip="Map starting point — adjust if needed",
        popup=f"Map centre: {latitude:.4f}, {longitude:.4f}",
        icon=folium.Icon(color="blue", icon="info-sign"),
    ).add_to(m)

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
        edit_options={"edit": True, "remove": True},
    ).add_to(m)

    Fullscreen(position="topright").add_to(m)
    MousePosition(
        position="bottomleft",
        separator=" | ",
        prefix="Lat/Lon:",
        num_digits=5,
    ).add_to(m)
    folium.LayerControl(position="topright", collapsed=True).add_to(m)

    result = st_folium(
        m,
        height=620,
        use_container_width=True,
        returned_objects=["last_active_drawing", "all_drawings"],
        key="position_loss_map",
    )

    drawing = None
    if result:
        drawing = result.get("last_active_drawing")
        if not drawing:
            drawings = result.get("all_drawings") or []
            if drawings:
                drawing = drawings[-1]

    if drawing:
        geometry = drawing.get("geometry")
        if geometry:
            return {"geometry": geometry, "properties": drawing.get("properties", {})}

    return None
