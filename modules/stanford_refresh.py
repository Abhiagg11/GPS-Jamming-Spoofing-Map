import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = PROJECT_ROOT / "downloaded_json_files"
CERTIFICATE_BUNDLE = PROJECT_ROOT / "certs" / "stanford-ca-bundle.pem"

STATUS_FILE = DATA_ROOT / ".stanford_refresh_status.json"

BASE_URL = "https://waas-nas.stanford.edu/data"

DATA_FILES = {
    "jamming": [
        "events.json",
        "heatmap.json",
    ],
    "spoofing": [
        "events.json",
        "heatmap.json",
        "beforeAndDuringSpoofing.json",
        "duringAndAfterSpoofing.json",
    ],
}


def read_status():
    if not STATUS_FILE.exists():
        return {}

    try:
        return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_status(status):
    DATA_ROOT.mkdir(parents=True, exist_ok=True)

    temporary_file = STATUS_FILE.with_suffix(".tmp")
    temporary_file.write_text(
        json.dumps(status, indent=2),
        encoding="utf-8",
    )
    temporary_file.replace(STATUS_FILE)


def refresh_stanford_data(force=False):
    """Refresh the latest seven UTC calendar days of Stanford data."""

    now = datetime.now(timezone.utc)
    status = read_status()

    last_attempt = status.get("last_attempt_utc")

    if not force and last_attempt:
        try:
            previous_attempt = datetime.fromisoformat(last_attempt)

            if previous_attempt.date() == now.date():
                status["skipped"] = True
                return status
        except ValueError:
            pass

    if not CERTIFICATE_BUNDLE.exists():
        raise FileNotFoundError(
            f"SSL certificate bundle not found: {CERTIFICATE_BUNDLE}"
        )

    session = requests.Session()
    session.verify = str(CERTIFICATE_BUNDLE)
    session.headers.update({
        "User-Agent": "GNSS-Interference-Investigator/1.0"
    })

    updated = 0
    unchanged = 0
    not_published = 0
    errors = []

    checked_dates = []

    try:
        for offset in range(7):
            day = (now.date() - timedelta(days=offset))
            date_path = day.strftime("%Y/%m/%d")
            checked_dates.append(day.isoformat())

            for data_type, filenames in DATA_FILES.items():
                for filename in filenames:

                    url = (
                        f"{BASE_URL}/{data_type}/"
                        f"{date_path}/{filename}"
                    )

                    local_folder = (
                        DATA_ROOT / data_type / date_path
                    )
                    local_file = local_folder / filename

                    try:
                        response = session.get(
                            url,
                            timeout=(10, 40),
                        )

                        if response.status_code == 404:
                            not_published += 1
                            continue

                        response.raise_for_status()

                        payload = response.json()

                        if not isinstance(payload, dict):
                            raise ValueError(
                                "Unexpected JSON structure"
                            )

                        new_content = json.dumps(
                            payload,
                            indent=2,
                            ensure_ascii=False,
                        )

                        if local_file.exists():
                            old_content = local_file.read_text(
                                encoding="utf-8"
                            )

                            try:
                                old_payload = json.loads(old_content)
                            except json.JSONDecodeError:
                                old_payload = None

                            if old_payload == payload:
                                unchanged += 1
                                continue

                        local_folder.mkdir(
                            parents=True,
                            exist_ok=True,
                        )

                        temporary_file = local_file.with_suffix(
                            local_file.suffix + ".tmp"
                        )

                        temporary_file.write_text(
                            new_content,
                            encoding="utf-8",
                        )

                        temporary_file.replace(local_file)
                        updated += 1

                    except (
                        requests.RequestException,
                        ValueError,
                        OSError,
                    ) as exc:
                        errors.append(
                            f"{data_type}/{date_path}/{filename}: {exc}"
                        )

    finally:
        session.close()

    result = {
        "last_attempt_utc": now.isoformat(),
        "last_success_utc": (
            now.isoformat()
            if not errors
            else status.get("last_success_utc")
        ),
        "checked_dates": checked_dates,
        "updated": updated,
        "unchanged": unchanged,
        "not_published": not_published,
        "errors": errors,
        "skipped": False,
    }

    save_status(result)

    return result
