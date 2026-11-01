
from datetime import datetime, timedelta
from pathlib import Path
import requests

BASE_URL = "https://waas-nas.stanford.edu/data"
OUTPUT = Path("downloaded_json_files")
CA_BUNDLE = Path("certs/stanford-ca-bundle.pem")


def download_file(url):
    relative_path = Path(*url.split("/")[4:])
    destination = OUTPUT / relative_path

    if destination.exists():
        print(f"Already exists: {destination}")
        return

    destination.parent.mkdir(parents=True, exist_ok=True)

    try:
        response = requests.get(
            url,
            verify=str(CA_BUNDLE),
            timeout=30,
        )
        response.raise_for_status()

        # Validate JSON before saving.
        data = response.json()

        import json
        destination.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )

        print(f"Downloaded: {destination}")

    except requests.RequestException as error:
        print(f"Download failed: {url} — {error}")

    except ValueError as error:
        print(f"Invalid JSON: {url} — {error}")


def download_dates(start, end, data_type):
    current = datetime.strptime(start, "%Y/%m/%d")
    last = datetime.strptime(end, "%Y/%m/%d")

    while current <= last:
        date_path = current.strftime("%Y/%m/%d")

        if data_type == "jamming":
            files = ["events.json", "heatmap.json"]
        elif data_type == "spoofing":
            files = [
                "events.json",
                "heatmap.json",
                "beforeAndDuringSpoofing.json",
                "duringAndAfterSpoofing.json",
            ]
        else:
            raise ValueError(f"Unsupported data type: {data_type}")

        for filename in files:
            url = f"{BASE_URL}/{data_type}/{date_path}/{filename}"
            download_file(url)

        current += timedelta(days=1)


if __name__ == "__main__":
    if not CA_BUNDLE.exists():
        raise FileNotFoundError(f"Certificate bundle not found: {CA_BUNDLE}")

    download_dates("2026/10/29", "2026/10/30", "jamming")
    download_dates("2026/10/29", "2026/10/30", "spoofing")
