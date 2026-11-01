
import h3


def build_hex_cells(reports, resolution=5):
    """
    Group real GNSS interference reports into global H3 cells.

    Cell density represents the number of reports,
    NOT measured RF interference strength.
    """

    if reports is None or reports.empty:
        return []

    required = {
        "latitude",
        "longitude",
        "event_type",
        "timestamp",
        "confidence",
        "source",
    }

    if not required.issubset(reports.columns):
        raise ValueError("GNSS report data is missing required columns.")

    data = reports.copy()

    # Exclude synthetic/demo records.
    synthetic = data["source"].astype(str).str.contains(
        "synthetic|demo",
        case=False,
        na=False,
    )
    data = data[~synthetic]

    if data.empty:
        return []

    cells = {}

    for row in data.itertuples(index=False):
        lat = float(row.latitude)
        lon = float(row.longitude)

        # Assign report to a global H3 cell.
        cell_id = h3.latlng_to_cell(lat, lon, resolution)

        if cell_id not in cells:
            boundary = h3.cell_to_boundary(cell_id)

            cells[cell_id] = {
                "cell_id": cell_id,
                "latitude": h3.cell_to_latlng(cell_id)[0],
                "longitude": h3.cell_to_latlng(cell_id)[1],
                "boundary": [
                    [point[0], point[1]]
                    for point in boundary
                ],
                "reports": [],
            }

        cells[cell_id]["reports"].append(row)

    output = []

    for cell in cells.values():
        cell_reports = cell["reports"]

        output.append({
            "cell_id": cell["cell_id"],
            "latitude": cell["latitude"],
            "longitude": cell["longitude"],
            "boundary": cell["boundary"],
            "report_count": len(cell_reports),
            "event_types": sorted({
                str(r.event_type).lower()
                for r in cell_reports
            }),
            "sources": sorted({
                str(r.source)
                for r in cell_reports
            }),
            "timestamps": sorted({
                str(r.timestamp)
                for r in cell_reports
            }),
            "confidence": sorted({
                str(r.confidence)
                for r in cell_reports
            }),
        })

    return output
