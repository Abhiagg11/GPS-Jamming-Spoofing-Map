
import json
import streamlit as st
import pandas as pd

from modules.map_view import render_investigation_map
from modules.airport_lookup import search_airport
from modules.adsb_provider import (
    search_by_route,
    search_by_callsign,
    get_flight_track,
    detect_position_gaps,
    ADSBProviderError,
)

# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="GNSS Interference Investigator",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# CUSTOM STYLING
# ---------------------------------------------------------

st.markdown(
    """
    <style>
        .stApp {
            background-color: #0b111b;
        }

        .block-container {
            max-width: 100%;
            padding: 2rem 0.9rem 0.4rem 0.9rem !important;
        }

        [data-testid="stSidebar"] {
            background-color: #111c2a;
            border-right: 1px solid #26384c;
            min-width: 255px;
            max-width: 255px;
        }

        [data-testid="stSidebar"] .block-container {
            padding: 0.8rem 0.8rem;
        }

        .main-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid #26384c;
            padding-bottom: 10px;
            margin-bottom: 12px;
        }

        .main-header h1 {
            color: #f1f5f9;
            font-size: 21px;
            margin: 0;
        }

        .subtitle {
            color: #91a4b9;
            font-size: 12px;
            margin-top: 3px;
        }

        .sidebar-heading {
            color: #f1f5f9;
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 3px;
        }

        .sidebar-hint {
            color: #91a4b9;
            font-size: 12px;
            margin-bottom: 15px;
        }

        .map-caption {
            color: #91a4b9;
            font-size: 11px;
            padding-top: 5px;
        }

        div[data-testid="stForm"] {
            background: #172333;
            border: 1px solid #26384c;
            border-radius: 9px;
            padding: 12px;
        }

        div[data-testid="stTextInput"] input,
        div[data-testid="stDateInput"] input {
            min-height: 2.4rem;
        }

        div[data-testid="stVerticalBlock"] > div {
            gap: 0.38rem;
        }

        .map-frame {
            background: #111c2a;
            border: 1px solid #26384c;
            border-radius: 10px;
            padding: 8px;
        }

        div[data-testid="stAlert"] {
            padding: 0.65rem 0.9rem;
        }

        hr {
            border-color: #26384c;
        }

        footer {
            visibility: hidden;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# CACHED ADS-B PROVIDER CALLS
# ---------------------------------------------------------

@st.cache_data(ttl=900, show_spinner=False)
def cached_route_search(departure, destination, flight_date):
    return search_by_route(departure, destination, flight_date)


@st.cache_data(ttl=900, show_spinner=False)
def cached_callsign_search(callsign, flight_date):
    return search_by_callsign(callsign, flight_date)


@st.cache_data(ttl=900, show_spinner=False)
def cached_flight_track(flight_id):
    return get_flight_track(flight_id)


# ---------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------

if "flight_search" not in st.session_state:
    st.session_state.flight_search = None

if "search_message" not in st.session_state:
    st.session_state.search_message = None

if "search_error" not in st.session_state:
    st.session_state.search_error = None

if "selected_flight_id" not in st.session_state:
    st.session_state.selected_flight_id = None


# ---------------------------------------------------------
# SIDEBAR — FLIGHT SEARCH
# ---------------------------------------------------------

with st.sidebar:

    st.markdown(
        '<div class="sidebar-heading">🔎 Flight Search</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sidebar-hint">'
        'Find a historical flight to investigate (latest 7 calendar days).'
        '</div>',
        unsafe_allow_html=True,
    )

    search_method = st.radio(
        "Search method",
        ["By Route", "By Flight Number"],
        key="search_method",
    )

    st.divider()

    # SEARCH BY ROUTE

    if search_method == "By Route":

        with st.form("route_search_form"):

            st.markdown("**Airport Details**")

            departure = st.text_input(
                "Departure Airport",
                placeholder="DEL",
                max_chars=4,
            )

            destination = st.text_input(
                "Destination Airport",
                placeholder="LHR",
                max_chars=4,
            )

            route_date = st.date_input(
                "Flight Date",
                key="route_flight_date",
            )

            route_submit = st.form_submit_button(
                "Search Flights",
                use_container_width=True,
                type="primary",
            )

        if route_submit:

            dep = departure.strip().upper()
            dest = destination.strip().upper()

            st.session_state.search_error = None
            st.session_state.search_message = None
            st.session_state.flight_search = None
            st.session_state.selected_flight_id = None

            if not dep or not dest:
                st.session_state.search_error = (
                    "Enter both departure and destination airport codes."
                )

            elif dep == dest:
                st.session_state.search_error = (
                    "Departure and destination cannot be the same."
                )

            elif search_airport(dep).empty:
                st.session_state.search_error = (
                    f"Departure airport '{dep}' was not found."
                )

            elif search_airport(dest).empty:
                st.session_state.search_error = (
                    f"Destination airport '{dest}' was not found."
                )

            else:
                try:
                    with st.spinner("Searching historical ADS-B records..."):

                        flights = cached_route_search(
                            dep,
                            dest,
                            route_date.isoformat(),
                        )

                    # Keep airport coordinates even when ADS-B returns no flights.
                    dep_airport = search_airport(dep).iloc[0]
                    dest_airport = search_airport(dest).iloc[0]

                    estimated_route_points = [
                        {
                            "name": f"{dep} — {dep_airport['name']}",
                            "latitude": float(dep_airport["latitude_deg"]),
                            "longitude": float(dep_airport["longitude_deg"]),
                        },
                        {
                            "name": f"{dest} — {dest_airport['name']}",
                            "latitude": float(dest_airport["latitude_deg"]),
                            "longitude": float(dest_airport["longitude_deg"]),
                        },
                    ]

                    st.session_state.flight_search = {
                        "search_type": "route",
                        "departure": dep,
                        "destination": dest,
                        "date": route_date.isoformat(),
                        "flights": flights,
                        "estimated_route_points": estimated_route_points,
                    }

                    st.session_state.search_message = (
                        f"{dep} → {dest} | {route_date.isoformat()} | "
                        f"{len(flights)} matching record(s)"
                    )

                except (ADSBProviderError, ValueError) as exc:
                    st.session_state.search_error = str(exc)

                except Exception as exc:
                    st.session_state.search_error = (
                        f"Flight search failed: {exc}"
                    )

    # SEARCH BY FLIGHT NUMBER

    else:

        with st.form("flight_number_search_form"):

            st.markdown("**Flight Details**")

            flight_number = st.text_input(
                "Flight Number / Callsign",
                placeholder="BAW395",
            )

            flight_date = st.date_input(
                "Flight Date",
                key="flight_number_date",
            )

            flight_submit = st.form_submit_button(
                "Search Flight",
                use_container_width=True,
                type="primary",
            )

        if flight_submit:

            callsign = flight_number.strip().upper()

            st.session_state.search_error = None
            st.session_state.search_message = None
            st.session_state.flight_search = None
            st.session_state.selected_flight_id = None

            if not callsign:
                st.session_state.search_error = (
                    "Enter a flight number or callsign."
                )

            else:
                try:
                    with st.spinner("Searching historical ADS-B records..."):

                        flights = cached_callsign_search(
                            callsign,
                            flight_date.isoformat(),
                        )

                    st.session_state.flight_search = {
                        "search_type": "flight_number",
                        "flight_number": callsign,
                        "date": flight_date.isoformat(),
                        "flights": flights,
                    }

                    st.session_state.search_message = (
                        f"{callsign} | {flight_date.isoformat()} | "
                        f"{len(flights)} matching record(s)"
                    )

                except (ADSBProviderError, ValueError) as exc:
                    st.session_state.search_error = str(exc)

                except Exception as exc:
                    st.session_state.search_error = (
                        f"Flight search failed: {exc}"
                    )

    # SEARCH FEEDBACK

    if st.session_state.search_error:
        st.error(st.session_state.search_error)

    if st.session_state.search_message:
        st.success(st.session_state.search_message)


# ---------------------------------------------------------
# MAIN HEADER
# ---------------------------------------------------------

st.markdown(
    """
    <div class="main-header">
        <div>
            <h1>🛰️ GNSS Interference Investigator</h1>
            <div class="subtitle">
                Historical flight routes · ADS-B position gaps ·
                Potential GNSS interference
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# FLIGHT SEARCH RESULTS
# ---------------------------------------------------------

search = st.session_state.flight_search

selected_flight = None
track = pd.DataFrame()
gaps = pd.DataFrame()
flight_metadata = None

if search:

    flights = search.get("flights", [])

    if not flights:

        st.warning(
            "No matching ADS-B records were returned. The map will show "
            "an estimated airport-to-airport connection, not an actual flight path."
        )

    else:

        def flight_label(flight):

            callsign = flight.get("callsign") or "Unknown callsign"
            origin = flight.get("start_airport_ident") or "Unknown origin"
            destination = flight.get("end_airport_ident") or "Unknown destination"
            start = flight.get("start_ts") or "Time unavailable"

            return (
                f"{callsign} | {origin} → {destination} | {start}"
            )

        options = {
            flight.get("flight_id"): flight
            for flight in flights
            if flight.get("flight_id")
        }

        if options:

            labels = {
                flight_label(f): fid
                for fid, flight in options.items()
            }

            label_list = list(labels.keys())

            current_id = st.session_state.selected_flight_id
            default_index = 0

            if current_id in options:

                for idx, label in enumerate(label_list):

                    if labels[label] == current_id:
                        default_index = idx
                        break

            selected_label = st.selectbox(
                "Select the matching historical flight",
                label_list,
                index=default_index,
                key=(
                    f"flight_choice_{search['date']}_"
                    f"{search.get('flight_number', search.get('departure', 'route'))}"
                ),
            )

            selected_id = labels[selected_label]

            st.session_state.selected_flight_id = selected_id
            selected_flight = options[selected_id]

            try:

                with st.spinner("Retrieving historical aircraft positions..."):

                    flight_metadata, track = cached_flight_track(
                        selected_id
                    )

                gaps = detect_position_gaps(
                    track,
                    threshold_seconds=60,
                )

            except Exception as exc:

                st.error(
                    f"Could not retrieve this flight track: {exc}"
                )

                track = pd.DataFrame()
                gaps = pd.DataFrame()

            if not track.empty:

                st.caption(
                    f"{len(track)} ADS-B positions · "
                    f"{len(gaps)} observation gaps (>60 sec) · "
                    "Gaps do not confirm GNSS interference."
                )

            else:

                st.warning(
                    "The selected flight record has no usable historical track points."
                )


# ---------------------------------------------------------
# INVESTIGATION MAP
# ---------------------------------------------------------

st.markdown("### Investigation Map")

map_lat, map_lon = 8.5, 5.3
map_result = None

with st.container(border=True):

    try:

        estimated_route_points = (
            search.get("estimated_route_points", [])
            if search and search.get("search_type") == "route"
            else []
        )

        if estimated_route_points and track.empty:
            map_lat = sum(p["latitude"] for p in estimated_route_points) / 2
            map_lon = sum(p["longitude"] for p in estimated_route_points) / 2

        map_result = render_investigation_map(
            map_lat,
            map_lon,
            flight_route_points=estimated_route_points,
            flight_track=track,
            position_gaps=gaps,
        )

    except Exception as exc:

        st.error(
            f"The investigation map could not be loaded: {exc}"
        )


# ---------------------------------------------------------
# GEOJSON DOWNLOAD
# ---------------------------------------------------------

if isinstance(map_result, dict) and map_result.get("geometry"):

    st.download_button(
        label="⬇ Download Investigation Area (GeoJSON)",
        data=json.dumps(
            map_result["geometry"],
            indent=2,
        ),
        file_name="investigation-area.geojson",
        mime="application/geo+json",
    )


# ---------------------------------------------------------
# COLLAPSED FLIGHT DETAILS
# ---------------------------------------------------------

if not track.empty:

    with st.expander(
        "Flight data and detected gaps",
        expanded=False,
    ):

        col1, col2, col3 = st.columns(3)

        col1.metric("ADS-B positions", len(track))
        col2.metric("Gaps over 60 sec", len(gaps))

        col3.metric(
            "Callsign",
            str(
                (flight_metadata or {}).get("callsign") or "Unknown"
            ),
        )

        if gaps.empty:

            st.write(
                "No gaps above 60 seconds were detected."
            )

        else:

            display_gaps = gaps.copy()

            for col in ["previous_timestamp", "timestamp"]:
                display_gaps[col] = display_gaps[col].astype(str)

            st.dataframe(
                display_gaps,
                use_container_width=True,
                hide_index=True,
            )


# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------

st.markdown(
    """
    <div class="map-caption">
        Data source: ADS-B historical provider. Track geometry represents
        received ADS-B positions; lines are not interpolated across detected
        observation gaps. ADS-B gaps are not proof of GNSS interference.
    </div>
    """,
    unsafe_allow_html=True,
)
