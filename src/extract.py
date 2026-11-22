import os
import json
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

kobo_api_token = os.getenv("KOBO_API_TOKEN")
kobo_asset_uid = os.getenv("KOBO_ASSET_UID")
kobo_base_url = os.getenv("KOBO_BASE_URL")

raw_data_folder = Path("data/raw")
raw_data_folder.mkdir(parents=True, exist_ok=True)


def fetch_all_submissions():
    """Pull every submission from the Kobo API, following pagination."""
    request_headers = {"Authorization": f"Token {kobo_api_token}"}
    next_page_url = f"{kobo_base_url}/api/v2/assets/{kobo_asset_uid}/data/?format=json"
    all_submissions = []

    while next_page_url:
        response = requests.get(next_page_url, headers=request_headers, timeout=30)
        response.raise_for_status()
        response_data = response.json()

        all_submissions.extend(response_data["results"])
        next_page_url = response_data.get("next")

    return all_submissions


if __name__ == "__main__":
    submissions_list = fetch_all_submissions()
    output_path = raw_data_folder / "submissions_raw.json"

    with open(output_path, "w", encoding="utf-8") as output_file:
        json.dump(submissions_list, output_file, indent=2)

    print(f"Saved {len(submissions_list)} submissions to {output_path}")