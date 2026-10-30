import re
from typing import Optional, Tuple
from PIL import Image, ImageOps, ImageEnhance, ImageFilter

COORD_PATTERNS = [
    re.compile(r"""(?P<lat_deg>\d{1,3})\s*[°º]\s*(?P<lat_min>\d{1,2})\s*['′]\s*(?P<lat_sec>\d{1,2}(?:\.\d+)?)\s*[\"']?\s*(?P<lat_dir>[NS])\s*[,;·• ]+\s*(?P<lon_deg>\d{1,3})\s*[°º]\s*(?P<lon_min>\d{1,2})\s*['′]\s*(?P<lon_sec>\d{1,2}(?:\.\d+)?)\s*[\"']?\s*(?P<lon_dir>[EW])""", re.I),
    re.compile(r"""(?P<lat_deg>\d{1,3})\s+(?P<lat_min>\d{1,2})\s+(?P<lat_sec>\d{1,2}(?:\.\d+)?)\s+(?P<lat_dir>[NS])\s*[,;·• ]+\s*(?P<lon_deg>\d{1,3})\s+(?P<lon_min>\d{1,2})\s+(?P<lon_sec>\d{1,2}(?:\.\d+)?)\s+(?P<lon_dir>[EW])""", re.I),
]

def _dms_to_decimal(deg: str, minute: str, second: str, direction: str) -> float:
    value = float(deg) + float(minute) / 60 + float(second) / 3600
    return -value if direction.upper() in {"S", "W"} else value

def _extract_coordinate(text: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    normalized = text.replace("’", "'").replace("‘", "'").replace("′", "'").replace("″", '"')
    for pattern in COORD_PATTERNS:
        match = pattern.search(normalized)
        if match:
            g = match.groupdict()
            lat = _dms_to_decimal(g["lat_deg"], g["lat_min"], g["lat_sec"], g["lat_dir"])
            lon = _dms_to_decimal(g["lon_deg"], g["lon_min"], g["lon_sec"], g["lon_dir"])
            if 0 <= float(g["lat_min"]) < 60 and 0 <= float(g["lat_sec"]) < 60 and 0 <= float(g["lon_min"]) < 60 and 0 <= float(g["lon_sec"]) < 60 and -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon, match.group(0)
    return None, None, None

def analyse_screenshot(image: Image.Image) -> dict:
    """Try OCR using Tesseract if installed; never treats OCR output as verified data."""
    notes = ["OCR can misread digits, symbols and hemisphere letters. Verify all extracted values manually."]
    text = ""
    status = "OCR unavailable"
    try:
        import pytesseract
        prepared = ImageOps.grayscale(image)
        prepared = ImageEnhance.Contrast(prepared).enhance(1.8)
        prepared = prepared.resize((prepared.width * 2, prepared.height * 2))
        prepared = prepared.filter(ImageFilter.SHARPEN)
        text = pytesseract.image_to_string(prepared, config="--psm 11")
        status = "OCR completed (review required)"
    except ImportError:
        notes.append("Install Tesseract OCR and pytesseract to enable automatic text extraction. Manual map marking remains available.")
    except Exception as exc:
        status = f"OCR error: {exc}"
        notes.append("Automatic extraction did not complete. Continue with manual entry.")
    coord_lat, coord_lon, coord_text = _extract_coordinate(text)
    flight_match = re.search(r"\b([A-Z]{2,4}\s?\d{1,5})\b", text.upper())
    flight_id = flight_match.group(1).replace(" ", "") if flight_match else None
    excerpt = "\n".join(line.strip() for line in text.splitlines() if line.strip())[:900]
    first_coordinate = (coord_lat, coord_lon) if coord_lat is not None and coord_lon is not None else None
    if not text:
        notes.append("No OCR text was returned. You can enter the map centre manually and draw the affected area.")
    return {"flight_id": flight_id, "coordinates_text": coord_text, "first_coordinate": first_coordinate,
            "ocr_status": status, "text_excerpt": excerpt, "notes": notes}
