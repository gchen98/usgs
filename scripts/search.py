"""Embedding search over harvested ScienceBase items, plus a small recall@k evaluation.

Usage:
    python scripts/search.py "irrigation water use in Kansas"   # top 5 results
    python scripts/search.py --eval                              # recall@k on data/eval/queries.csv

Embeddings are computed locally with sentence-transformers (no API key) and cached in
data/derived/, keyed by model name and build_text(); delete the cache to force a rebuild.

GARY: fill in build_text() and recall_at_k(), and write data/eval/queries.csv.
"""

import argparse
import csv
import hashlib
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from score import load_items  # noqa: E402

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # max 256 tokens; longer text is cut off
CACHE_DIR = Path("data/derived")
QUERIES_PATH = Path("data/eval/queries.csv")
KS = (1, 5, 10)


# --- Gary writes these -------------------------------------------------------------

def build_text(item):
    """The text that represents one item in the search index."""
    return item.get("title", "") +". "+ item.get("summary","")  # placeholder: title only


def recall_at_k(ranked_ids, relevant_ids, k):
    """Fraction of relevant_ids that appear in the first k of ranked_ids."""
    assert len(relevant_ids)>0, "Cannot compute recall with no relevant IDs."
    overlap_size = len(set(ranked_ids[:k]) & set(relevant_ids))
    recall = overlap_size / len(relevant_ids)
    return recall

    # raise NotImplementedError


# --- Plumbing ----------------------------------------------------------------------

def get_model():
    from sentence_transformers import SentenceTransformer  # slow import; only when needed
    return SentenceTransformer(MODEL_NAME)


def build_index(items, model):
    """Return an (n_items, dim) array of unit-length embeddings, cached on disk."""
    texts = [build_text(i) for i in items]
    key = hashlib.sha256((MODEL_NAME + "\n".join(texts)).encode()).hexdigest()[:12]
    path = CACHE_DIR / f"embeddings_{key}.npy"
    if path.exists():
        return np.load(path)
    vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.save(path, vecs)
    return vecs


def search(query, items, index, model, k=5):
    """Cosine similarity = dot product, because every vector has length 1."""
    q = model.encode([query], normalize_embeddings=True)[0]
    sims = index @ q
    top = np.argsort(-sims)[:k]
    return [(items[i]["id"], float(sims[i]), items[i].get("title", "")) for i in top]


def load_queries(path=QUERIES_PATH):
    """CSV columns: query, relevant_ids (space-separated), kind (e.g. exact / vague)."""
    with open(path, newline="") as f:
        return [
            {"query": r["query"], "relevant": r["relevant_ids"].split(), "kind": r.get("kind", "")}
            for r in csv.DictReader(f)
        ]


def evaluate(items, index, model):
    queries = load_queries()
    rows = []
    for q in queries:
        ranked = [hit[0] for hit in search(q["query"], items, index, model, k=max(KS))]
        rows.append({"query": q["query"], "kind": q["kind"],
                     **{f"recall@{k}": recall_at_k(ranked, q["relevant"], k) for k in KS}})
    import pandas as pd
    df = pd.DataFrame(rows)
    print(df.to_string(index=False, max_colwidth=50))
    print(f"\nMean over {len(df)} hand-written queries:")
    print(df.groupby("kind")[[f"recall@{k}" for k in KS]].mean().round(2))
    print(df[[f"recall@{k}" for k in KS]].mean().round(2).to_string())


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("query", nargs="?")
    parser.add_argument("--eval", action="store_true")
    parser.add_argument("-k", type=int, default=5)
    args = parser.parse_args()

    items = load_items()
    model = get_model()
    index = build_index(items, model)
    if args.eval:
        evaluate(items, index, model)
    elif args.query:
        for item_id, sim, title in search(args.query, items, index, model, k=args.k):
            print(f"{sim:.3f}  https://www.sciencebase.gov/catalog/item/{item_id}  {title[:80]}")
    else:
        parser.error("give a query or --eval")


if __name__ == "__main__":
    main()
