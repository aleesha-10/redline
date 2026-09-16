"""
Builds the semantic search index used by backend/app/embeddings.py.

Reads clause examples out of the CUAD master clauses CSV (data/cuad/), embeds
each clause with a sentence-transformer, and writes:
  - data/index/embeddings.npy   (float32 matrix, one row per clause)
  - data/index/metadata.json    (parallel list of {category, snippet})

Usage:
    python backend/scripts/build_index.py

NOTE: The exact CUAD file layout can vary by release. This script expects a
CSV with at least these columns: `category`, `clause_text` (adjust
CATEGORY_COL / TEXT_COL below to match whatever file you actually
downloaded -- CUAD's master clauses CSV column names have changed across
versions).
"""
import glob
import json
import os

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

CUAD_DIR = os.path.join("data", "cuad")
INDEX_DIR = os.path.join("data", "index")
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

CATEGORY_COL = "category"
TEXT_COL = "clause_text"
MAX_SNIPPET_LEN = 240


def find_master_csv() -> str:
    candidates = glob.glob(os.path.join(CUAD_DIR, "**", "*master*clauses*.csv"), recursive=True)
    if not candidates:
        raise FileNotFoundError(
            f"No CUAD master clauses CSV found under {CUAD_DIR}. "
            "Run backend/scripts/download_cuad.py first, or verify column "
            "names match CATEGORY_COL/TEXT_COL in this script."
        )
    return candidates[0]


def main():
    os.makedirs(INDEX_DIR, exist_ok=True)
    csv_path = find_master_csv()
    print(f"Loading {csv_path} ...")
    df = pd.read_csv(csv_path)

    if CATEGORY_COL not in df.columns or TEXT_COL not in df.columns:
        raise KeyError(
            f"Expected columns '{CATEGORY_COL}' and '{TEXT_COL}' not found. "
            f"Available columns: {list(df.columns)}. Update CATEGORY_COL / "
            "TEXT_COL at the top of this script to match your CUAD release."
        )

    df = df.dropna(subset=[TEXT_COL]).reset_index(drop=True)
    print(f"Embedding {len(df)} clauses ...")

    model = SentenceTransformer(MODEL_NAME)
    texts = df[TEXT_COL].astype(str).tolist()
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)

    metadata = [
        {
            "category": str(row[CATEGORY_COL]),
            "snippet": str(row[TEXT_COL])[:MAX_SNIPPET_LEN],
        }
        for _, row in df.iterrows()
    ]

    np.save(os.path.join(INDEX_DIR, "embeddings.npy"), np.asarray(embeddings, dtype=np.float32))
    with open(os.path.join(INDEX_DIR, "metadata.json"), "w") as f:
        json.dump(metadata, f)

    print(f"Index built: {len(metadata)} clauses -> {INDEX_DIR}/")


if __name__ == "__main__":
    main()
