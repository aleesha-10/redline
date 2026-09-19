"""
Builds the semantic search index used by backend/app/embeddings.py.

CUAD is distributed as a SQuAD-style JSON file (CUADv1.json), not a flat
CSV. Structure:
  { "data": [
      { "title": ..., "paragraphs": [
          { "context": "<full contract text>",
            "qas": [
              { "question": 'Highlight the parts (if any) of this contract
                              related to "Governing Law" that should be
                              reviewed by a lawyer...',
                "answers": [ { "text": "<clause text>", "answer_start": N } ],
                "is_impossible": false }
            ]
          }
      ]}
  ]}

The category name is embedded inside the question text (the quoted phrase).
This script pulls every non-impossible answer out as one (category,
clause_text) example, embeds each with a sentence-transformer, and writes:
  - data/index/embeddings.npy   (float32 matrix, one row per clause)
  - data/index/metadata.json    (parallel list of {category, snippet})

Usage:
    python backend/scripts/build_index.py
"""
import glob
import json
import os
import re

import numpy as np
from sentence_transformers import SentenceTransformer

CUAD_DIR = os.path.join("data", "cuad")
INDEX_DIR = os.path.join("data", "index")
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MAX_SNIPPET_LEN = 240

CATEGORY_PATTERN = re.compile(r'related to\s+"([^"]+)"')


def find_cuad_json() -> str:
    # Prefer the full CUADv1.json if present; fall back to any *.json that
    # looks like a CUAD release file.
    preferred = glob.glob(os.path.join(CUAD_DIR, "**", "CUADv1.json"), recursive=True)
    if preferred:
        return preferred[0]
    candidates = [
        f for f in glob.glob(os.path.join(CUAD_DIR, "**", "*.json"), recursive=True)
        if "train" not in os.path.basename(f).lower()
    ]
    if not candidates:
        raise FileNotFoundError(
            f"No CUAD JSON file found under {CUAD_DIR}. Run "
            "backend/scripts/download_cuad.py first."
        )
    return candidates[0]


def extract_category(question: str) -> str | None:
    match = CATEGORY_PATTERN.search(question)
    return match.group(1) if match else None


def load_examples(json_path: str) -> list[dict]:
    with open(json_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    examples = []
    for entry in raw.get("data", []):
        for paragraph in entry.get("paragraphs", []):
            for qa in paragraph.get("qas", []):
                if qa.get("is_impossible"):
                    continue
                category = extract_category(qa.get("question", ""))
                if not category:
                    continue
                for answer in qa.get("answers", []):
                    text = answer.get("text", "").strip()
                    if text:
                        examples.append({"category": category, "clause_text": text})
    return examples


def main():
    os.makedirs(INDEX_DIR, exist_ok=True)
    json_path = find_cuad_json()
    print(f"Loading {json_path} ...")
    examples = load_examples(json_path)

    if not examples:
        raise RuntimeError(
            "Parsed 0 examples from the CUAD JSON. The file format may have "
            "changed -- inspect a sample question/answers entry and adjust "
            "extract_category()/load_examples() accordingly."
        )

    print(f"Parsed {len(examples)} labeled clauses across "
          f"{len(set(e['category'] for e in examples))} categories.")
    print("Embedding clauses (this can take a few minutes on CPU) ...")

    model = SentenceTransformer(MODEL_NAME)
    texts = [e["clause_text"] for e in examples]
    embeddings = model.encode(
        texts, normalize_embeddings=True, show_progress_bar=True, batch_size=64
    )

    metadata = [
        {"category": e["category"], "snippet": e["clause_text"][:MAX_SNIPPET_LEN]}
        for e in examples
    ]

    np.save(os.path.join(INDEX_DIR, "embeddings.npy"), np.asarray(embeddings, dtype=np.float32))
    with open(os.path.join(INDEX_DIR, "metadata.json"), "w") as f:
        json.dump(metadata, f)

    print(f"Index built: {len(metadata)} clauses -> {INDEX_DIR}/")


if __name__ == "__main__":
    main()