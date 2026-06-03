import os
import json
import hashlib
# pyrefly: ignore [missing-import]
import faiss
import pandas as pd
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

# Setup paths relative to the script location
# scripts/ → backend/ → patent-kg/ → PROJECT_ROOT
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_SCRIPTS_DIR)))

# Input: canonical processed patents from the project root data layer
DATA_FILE = os.path.join(PROJECT_ROOT, "data", "processed", "patents.csv")

# Output: FAISS index stored inside patent-kg/ (co-located with the backend)
BASE_DIR = os.path.dirname(os.path.dirname(_SCRIPTS_DIR))  # → patent-kg/
INDEX_DIR = os.path.join(BASE_DIR, "data", "vector_store")
FAISS_INDEX_FILE = os.path.join(INDEX_DIR, "patents.index")
METADATA_FILE = os.path.join(INDEX_DIR, "metadata_mapping.json")

# Embedding model — PatentSBERTa (BERT-base backbone, 768-dim)
# Trained specifically on patent text; superior domain alignment vs MiniLM.
_MODEL_NAME = "AI-Growth-Lab/PatentSBERTa"

# Ensure the vector_store directory exists
os.makedirs(INDEX_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Deduplication helpers
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_field(text: str) -> str:
    """Lowercase, strip, and collapse repeated whitespace."""
    if not isinstance(text, str):
        return ""
    return " ".join(text.lower().split())


def _content_hash(title: str, abstract: str) -> str:
    """Return MD5 hex digest of normalised title + ' ' + abstract."""
    key = _normalize_field(title) + " " + _normalize_field(abstract)
    return hashlib.md5(key.encode("utf-8")).digest().hex()


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove patent records that are semantic duplicates of an earlier record.

    Strategy
    --------
    Compute content_hash = MD5(normalised_title + ' ' + normalised_abstract).
    Keep the FIRST occurrence of each hash; drop all subsequent ones.
    This targets patent-family members, jurisdiction variants, and re-publications
    that share the same title and abstract text.

    Family relationship data (patent_families.csv, Neo4j) is NOT affected.

    Returns
    -------
    pd.DataFrame
        Deduplicated DataFrame with a 'content_hash' column added.
    """
    original_count = len(df)

    df = df.copy()
    df["content_hash"] = df.apply(
        lambda row: _content_hash(row.get("title", ""), row.get("abstract", "")),
        axis=1,
    )

    df_dedup = df.drop_duplicates(subset="content_hash", keep="first").reset_index(drop=True)

    duplicate_count = original_count - len(df_dedup)
    final_count = len(df_dedup)

    print("\n" + "-" * 55)
    print("  DEDUPLICATION SUMMARY")
    print("-" * 55)
    print(f"  Original patents        : {original_count:>8,}")
    print(f"  Duplicate inventions    : {duplicate_count:>8,}  (removed)")
    print(f"  Final retrieval corpus  : {final_count:>8,}")
    print("-" * 55 + "\n")

    # Sanity check: no remaining duplicates
    remaining_dupes = df_dedup["content_hash"].duplicated().sum()
    assert remaining_dupes == 0, (
        f"BUG: {remaining_dupes} duplicate content_hash values remain after dedup!"
    )

    return df_dedup


# ─────────────────────────────────────────────────────────────────────────────
# Main builder
# ─────────────────────────────────────────────────────────────────────────────

def build_faiss_index():
    print(f"Loading embedding model ({_MODEL_NAME})...")
    model = SentenceTransformer(_MODEL_NAME)

    print(f"Loading patent data from {DATA_FILE}...")
    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(
            f"patents.csv not found at '{DATA_FILE}'.\n"
            "Run: python src/processing/process_patents.py  (from the project root)"
        )
    df = pd.read_csv(DATA_FILE)

    # Drop rows with no text to embed
    df = df.dropna(subset=["title", "abstract"])

    # ── Deduplication ─────────────────────────────────────────────────────────
    df = deduplicate(df)

    # ── Save deduplicated corpus to disk ─────────────────────────────────────
    DEDUPED_CSV = os.path.join(INDEX_DIR, "patents_deduped.csv")
    df.to_csv(DEDUPED_CSV, index=False)
    print(f"Deduplicated corpus saved to: {DEDUPED_CSV}")

    # ── Build text representations ────────────────────────────────────────────
    print(f"Generating semantic text representations for {len(df):,} patents...")
    texts = (df["title"] + ". " + df["abstract"]).tolist()
    patent_ids = df["patent_id"].tolist()

    # ── Encode ────────────────────────────────────────────────────────────────
    print("Computing embeddings with PatentSBERTa (this may take several minutes)...")
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        convert_to_numpy=True,
        batch_size=64,
    )

    # ── Auto-detect embedding dimension (never hardcode) ─────────────────────
    embedding_dim = embeddings.shape[1]
    print(f"\nEmbedding shape : {embeddings.shape}  (dim={embedding_dim})")

    # ── Alignment pre-check ───────────────────────────────────────────────────
    if len(embeddings) != len(patent_ids):
        raise ValueError(
            f"ALIGNMENT ERROR: {len(embeddings)} embedding rows != "
            f"{len(patent_ids)} patent_id rows. Aborting."
        )

    # ── Build FAISS index ─────────────────────────────────────────────────────
    print("Initializing FAISS Index (IndexFlatIP with L2 normalization)...")
    # L2-normalize so inner-product == cosine similarity (identical to original design)
    faiss.normalize_L2(embeddings)
    index = faiss.IndexFlatIP(embedding_dim)

    print(f"Adding {len(embeddings):,} vectors to FAISS...")
    index.add(embeddings)

    # ── Save index ────────────────────────────────────────────────────────────
    print("Saving FAISS index and metadata...")
    faiss.write_index(index, FAISS_INDEX_FILE)

    # FAISS row i → patent_id
    metadata_mapping = {i: str(pid) for i, pid in enumerate(patent_ids)}
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata_mapping, f)

    # ── Post-build validation ─────────────────────────────────────────────────
    print("\nRunning post-build validation...")
    loaded_index = faiss.read_index(FAISS_INDEX_FILE)
    with open(METADATA_FILE, "r") as f:
        loaded_metadata = json.load(f)

    assert loaded_index.ntotal == len(loaded_metadata), (
        f"VALIDATION FAILED: FAISS has {loaded_index.ntotal} vectors "
        f"but metadata has {len(loaded_metadata)} entries. Index is corrupt!"
    )
    assert loaded_index.ntotal == len(patent_ids), (
        f"VALIDATION FAILED: FAISS ntotal ({loaded_index.ntotal}) "
        f"!= deduplicated patent count ({len(patent_ids)})."
    )

    print("  [OK] FAISS vector count    == metadata entry count")
    print("  [OK] FAISS vector count    == deduplicated patent count")
    print(f"  [OK] Index dimension       == {loaded_index.d}")

    print(f"\n[DONE] Successfully built and saved the FAISS Index!")
    print(f"  Model          : {_MODEL_NAME}")
    print(f"  Dimension      : {embedding_dim}")
    print(f"  Vectors stored : {loaded_index.ntotal:,}")
    print(f"  Index location : {FAISS_INDEX_FILE}")
    print(f"  Metadata map   : {METADATA_FILE}")


if __name__ == "__main__":
    build_faiss_index()
