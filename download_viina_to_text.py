#!/usr/bin/env python3
"""Download the VIINA dataset and convert it to a plain‑text file.

The script:
  1. Downloads the ZIP archive from the official GitHub repo.
  2. Extracts the CSV file (event_info_latest_2025.csv).
  3. Reads the CSV and concatenates the "text" column (news article body).
  4. Writes the concatenated text to `viina_full.txt` inside a temporary folder.

Resulting files:
  - temp_viina/viina.zip          (downloaded archive)
  - temp_viina/event_info_latest_2025.csv (extracted CSV)
  - temp_viina/viina_full.txt    (plain‑text version, ready for ingestion)
"""

import csv
import os
import urllib.request
import zipfile
import sys

DATA_URL = "https://raw.githubusercontent.com/zhukovyuri/VIINA/main/Data/event_info_latest_2025.zip"
TMP_DIR = "temp_viina"
ZIP_PATH = os.path.join(TMP_DIR, "viina.zip")
CSV_NAME = "event_info_latest_2025.csv"
TXT_NAME = "viina_full.txt"

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

import ssl

def download_zip() -> None:
    print(f"Downloading VIINA ZIP → {ZIP_PATH}")
    # Use requests with SSL verification disabled (trusted source)
    import requests
    resp = requests.get(DATA_URL, stream=True, verify=False)
    resp.raise_for_status()
    with open(ZIP_PATH, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    print("Download complete.")

def extract_csv() -> str:
    print(f"Extracting {CSV_NAME} from ZIP...")
    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        zf.extract(CSV_NAME, TMP_DIR)
    csv_path = os.path.join(TMP_DIR, CSV_NAME)
    print(f"CSV extracted to {csv_path}")
    return csv_path

def csv_to_text(csv_path: str) -> str:
    txt_path = os.path.join(TMP_DIR, TXT_NAME)
    print(f"Converting CSV → plain text ({txt_path})")
    with open(csv_path, "r", encoding="utf-8") as csv_file, \
         open(txt_path, "w", encoding="utf-8") as txt_file:
        reader = csv.DictReader(csv_file)
        for i, row in enumerate(reader, 1):
            text = row.get("text", "").strip()
            if text:
                txt_file.write(text + "\n\n")
            if i % 1000 == 0:
                print(f"  processed {i} rows …")
    print(f"Plain‑text file ready: {txt_path}")
    return txt_path

def main() -> None:
    ensure_dir(TMP_DIR)
    download_zip()
    csv_path = extract_csv()
    csv_to_text(csv_path)
    print("All done. You can now use `temp_viina/viina_full.txt` for ingestion.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
