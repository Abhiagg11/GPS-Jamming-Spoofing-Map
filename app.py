import json
from io import BytesIO

import streamlit as st
from PIL import Image

from modules.map_view import render_investigation_map
from modules.screenshot_analysis import analyse_screenshot


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="GNSS Interference Investigator",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================================================
# PAGE STYLING
# =========================================================

st.markdown(
    """
    <style>
        .stApp {
            background-color: #0b111b;
        }

        .block-container {
            max-width: 100%;
            padding: 1.2rem 2.2rem 2rem 2.2rem;
        }

        .main-header {
            padding: 10px 0 18px 0;
            border-bottom: 1px solid #26384c;
            margin-bottom: 22px;
        }

        .header-kicker {
            color: #60c5e8;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 2px;
            margin-bottom: 7px;
        }

        .section-label {
            color: #e8eef6;
            font-size: 17px;
            font-weight: 650;
            margin-bottom: 5px;
        }

        .section-hint {
            color: #91a4b9;
            font-size: 12px;
            margin-bottom: 12px;
        }

        .footer-note {
            color: #91a4b9;
            font-size: 11px;
            border-top: 1px solid #26384c;
            padding-top: 14px;
            margin-top: 25px;
        }

        div[data-testid="stFileUploader"] {
            background: #162438;
            border: 1px dashed #42617e;
            border-radius: 10px;
            padding: 12px;
        }

        div[data-testid="stAlert"] {
            border-radius: 9px;
        }

        div[data-testid="stMetric"] {
            background: #141f2d;
            border: 1px solid #26384c;
            border-radius: 9px;
            padding: 12px;
        }

        hr {
            border-color: #26384c;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# HEADER
# =========================================================

st.markdown(
    """
    <div class="main-header">
        <div class="header-kicker">
            FLIGHT SURVEILLANCE AND GNSS ANALYSIS
        </div>
        <h1 style="margin:0; color:#f1f5f9;">
            🛰️ GNSS Interference Investigator
        </h1>
        <p style="color:#a8bacb; margin-top:8px; font-size:13px;">
            Investigate ADS-B position loss, identify affected geographical
            areas and examine potential GNSS interference evidence.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# DEFAULT MAP CENTRE
# =========================================================

# These coordinates only control the initial map view.
# They are not extracted aircraft positions.

map_lat = 8.5
map_lon = 5.3


# =========================================================
# 01 — SCREENSHOT UPLOAD
# =========================================================

st.markdown(
    '<div class="section-label">01 — Upload Flight Screenshot</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-hint">'
    'Upload a Mission Watch screenshot to extract visible flight details.'
    '</div>',
    unsafe_allow_html=True,
)

upload = st.file_uploader(
    "Upload Mission Watch screenshot",
    type=["png", "jpg", "jpeg", "webp"],
    help=(
        "Supported formats: PNG, JPG, JPEG and WEBP. "
        "Avoid uploading confidential operational data "
        "to a public deployment."
    ),
)


# =========================================================
# 02 — SCREENSHOT ANALYSIS
# =========================================================

if upload is not None:

    try:
        image = Image.open(
            BytesIO(upload.getvalue())
        ).convert("RGB")

        with st.expander(
            "Preview uploaded screenshot",
            expanded=False,
        ):
            st.image(
                image,
                use_container_width=True,
            )

        with st.spinner("Analysing flight screenshot..."):

            analysis = analyse_screenshot(image)

        if not isinstance(analysis, dict):
            raise ValueError(
                "Screenshot analysis returned an unexpected result."
            )

        flight_id = (
            analysis.get("flight_id") or "Not detected"
        )

        coordinates_text = analysis.get("coordinates_text")

        ocr_status = (
            analysis.get("ocr_status") or "Completed"
        )

        st.markdown(
            '<div class="section-label">02 — Screenshot Analysis</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="section-hint">'
            'Review the information extracted from the screenshot. '
            'Verify all details before using them.'
            '</div>',
            unsafe_allow_html=True,
        )

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Possible Flight",
            flight_id,
        )

        col2.metric(
            "Coordinates",
            "Detected" if coordinates_text else "Not detected",
        )

        col3.metric(
            "OCR Status",
            ocr_status,
        )

        if coordinates_text:

            st.markdown("**Coordinate text identified**")

            st.code(coordinates_text)

        text_excerpt = analysis.get("text_excerpt")

        if text_excerpt:

            with st.expander("View extracted screenshot text"):

                st.text(text_excerpt)

        for note in analysis.get("notes", []):

            st.caption(f"ℹ️ {note}")

    except Exception as exc:

        st.error(
            f"Screenshot analysis failed: {exc}"
        )


# =========================================================
# 03 — FLIGHT INVESTIGATION MAP
# =========================================================

st.divider()

st.markdown(
    '<div class="section-label">03 — Flight Investigation Map</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-hint">'
    'Explore the global map, switch between light and dark map styles, '
    'and mark the approximate area where aircraft position was lost.'
    '</div>',
    unsafe_allow_html=True,
)


# =========================================================
# 04 — FULL WIDTH INTERACTIVE MAP
# =========================================================

map_result = None

try:

    map_result = render_investigation_map(
        map_lat,
        map_lon,
    )

except Exception as exc:

    st.error(
        f"The investigation map could not be loaded: {exc}"
    )


# =========================================================
# 05 — INVESTIGATION AREA OUTPUT
# =========================================================

if isinstance(map_result, dict) and map_result.get("geometry"):

    st.success(
        "Investigation area marked successfully."
    )

    st.download_button(
        label="⬇ Download Investigation Area (GeoJSON)",
        data=json.dumps(
            map_result["geometry"],
            indent=2,
        ),
        file_name="position-loss-area.geojson",
        mime="application/geo+json",
    )

elif map_result is not None:

    st.info(
        "No investigation area selected. "
        "Use the circle, rectangle or polygon tools on the map."
    )


# =========================================================
# FOOTER
# =========================================================

st.markdown(
    """
    <div class="footer-note">
        <b>Investigation limitations:</b>
        This MVP currently supports screenshot text extraction and
        manual geographical area marking. It does not independently
        detect ADS-B position gaps or confirm GPS jamming or spoofing.
        Reliable assessment requires validated flight-position data,
        timestamps and independent GNSS interference evidence.
    </div>
    """,
    unsafe_allow_html=True,
)