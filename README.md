# GNSS Interference Investigator

A personal learning/MVP project for investigating reported ADS-B position gaps against supplied GNSS interference evidence. It is not an operational aviation system and does not independently establish that jamming or spoofing occurred.

## MVP features

- Upload a Mission Watch screenshot.
- Attempt OCR extraction of visible flight identifiers and DMS coordinates (Tesseract required).
- Review extracted values and manually correct the map centre.
- Draw/edit a marker, circle, rectangle or polygon around the suspected position-loss area.
- Upload a CSV of GNSS interference reports and compare report time/location with the incident window and selected area.
- Export matching records for further investigation.

## Run in GitHub Codespaces

1. Create a **private** GitHub repository named `gps-jamming-spoofing-map`.
2. Add these project files to the repository (or upload the ZIP from the project starter package).
3. Open the repository and select **Code → Codespaces → Create codespace on main**.
4. In the Codespaces terminal, run:

   ```bash
   pip install -r requirements.txt
   streamlit run app.py --server.address 0.0.0.0
   ```

5. Open forwarded port **8501** when Codespaces prompts you.

The included devcontainer installs Tesseract OCR when the Codespace is created. If you create a Codespace before adding `.devcontainer/devcontainer.json`, rebuild the container after committing it.

## Evidence CSV schema

Required columns:

| Column | Meaning |
|---|---|
| `timestamp` | UTC timestamp, preferably ISO 8601 such as `2026-10-30T06:55:00Z` |
| `latitude` | Decimal latitude (-90 to 90) |
| `longitude` | Decimal longitude (-180 to 180) |
| `event_type` | Provider's event label, e.g. jamming / spoofing / GNSS anomaly |
| `confidence` | Provider's confidence or severity label |
| `source` | Original data provider or report identifier |

The app currently performs a basic time-and-distance comparison. For drawn polygons it includes points inside the polygon and points within the configured radius of the polygon centroid. This is a screening heuristic, not a geospatial risk model. Provider-specific schemas and methodology should be preserved and documented before relying on results.

## Privacy and security

- Use synthetic, public or explicitly approved data during development.
- Do not commit customer screenshots, aircraft operational data, credentials, exports or internal SITA information to a personal repository.
- The app does not intentionally write uploaded screenshots or evidence CSVs to disk. Streamlit runs in a cloud Codespace, so uploaded content is still processed in that cloud environment.
- Keep the repository private unless the project has been reviewed and all data, code and dependencies are safe to publish.

## Current limitations

- OCR may fail on small, rotated, low-contrast or cluttered labels. Extracted flight IDs and coordinates must be checked by a human.
- The screenshot analyser does not yet reconstruct the complete aircraft route or infer the exact ADS-B gap automatically.
- No live interference provider is connected. Results depend entirely on the evidence CSV supplied by the investigator.
- ADS-B position loss can have causes other than GNSS interference. A matching report is an investigative lead, not proof.
- Spoofing assessment needs richer evidence (e.g. navigation integrity, position jumps, impossible groundspeed/track changes, corroborating aircraft and trusted provider reports) and is not implemented as an automatic classifier.

## Next development steps

1. Improve OCR with selectable screenshot regions and user-confirmed extraction.
2. Add manual entry of gap start/end coordinates and time.
3. Add a documented, licensed data-provider adapter.
4. Add nearby-aircraft corroboration and an evidence timeline.
5. Generate a traceable investigation report with source links and uncertainty notes.
