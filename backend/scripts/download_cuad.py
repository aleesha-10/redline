"""
Downloads the CUAD (Contract Understanding Atticus Dataset) master clauses
file into data/cuad/.

CUAD is distributed by The Atticus Project. The canonical release is on
GitHub: https://github.com/TheAtticusProject/cuad

Usage:
    python backend/scripts/download_cuad.py
"""
import os
import zipfile

import requests

CUAD_ZIP_URL = "https://github.com/TheAtticusProject/cuad/raw/main/data.zip"
OUT_DIR = os.path.join("data", "cuad")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    zip_path = os.path.join(OUT_DIR, "cuad_data.zip")

    print(f"Downloading CUAD dataset from {CUAD_ZIP_URL} ...")
    resp = requests.get(CUAD_ZIP_URL, stream=True, timeout=60)
    resp.raise_for_status()
    with open(zip_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    print("Extracting ...")
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(OUT_DIR)

    print(f"Done. CUAD files are in {OUT_DIR}/")
    print(
        "If the URL above has moved, grab the dataset manually from "
        "https://github.com/TheAtticusProject/cuad or "
        "https://www.atticusprojectai.org/cuad and place the extracted "
        "CSV/JSON files in data/cuad/."
    )


if __name__ == "__main__":
    main()
