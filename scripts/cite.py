"""Show search results as evidence: the best-matching passage of each item, with links.

Usage:
    python scripts/cite.py "how much water do farms in Kansas use"
    python scripts/cite.py "groundwater in New Jersey" -k 3

Step 1 (search.py) picks the items; step 2 (here) picks the passage inside each item that is
most similar to the query, so the user can check the claim against the source.

GARY: fill in split_passages() and pick_passage().
"""

import nltk
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from search import build_index, get_model, load_items, search  # noqa: E402

ITEM_URL = "https://www.sciencebase.gov/catalog/item/{}"


# --- Gary writes these -------------------------------------------------------------

def split_passages(text):
    """Split an item's text into passages (e.g. sentences). Return a list of strings."""
    sentences = nltk.sent_tokenize(text)
    return sentences



def pick_passage(passages, sims):
    """Given passages and their similarity to the query (same order), return the text to show."""
    best_passage = passages[np.argmax(sims)]
    return best_passage


# --- Plumbing ----------------------------------------------------------------------

def doi_of(item):
    for ident in item.get("identifiers", []):
        if ident.get("type") == "DOI" and ident.get("key"):
            return "https://doi.org/" + ident["key"].removeprefix("doi:").removeprefix("DOI:")
    return None


def best_evidence(query_vec, item, model):
    text = item.get("summary") or item.get("title", "")
    passages = [p for p in split_passages(text) if p.strip()] or [item.get("title", "")]
    vecs = model.encode(passages, normalize_embeddings=True)
    sims = vecs @ query_vec
    return pick_passage(passages, sims), float(np.max(sims))


def cite(query, k=5):
    items = load_items()
    model = get_model()
    index = build_index(items, model)
    by_id = {i["id"]: i for i in items}
    query_vec = model.encode([query], normalize_embeddings=True)[0]

    print(f'Query: "{query}"\n')
    for rank, (item_id, item_sim, title) in enumerate(search(query, items, index, model, k=k), 1):
        item = by_id[item_id]
        passage, passage_sim = best_evidence(query_vec, item, model)
        release = " [Data Release]" if "Data Release" in item.get("systemTypes", []) else ""
        print(f"[{rank}] {title}{release}")
        print(f"    item {item_sim:.3f} | passage {passage_sim:.3f}")
        print(f'    "{passage}"')
        print(f"    {ITEM_URL.format(item_id)}")
        if doi_of(item):
            print(f"    {doi_of(item)}")
        print()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("query")
    parser.add_argument("-k", type=int, default=5)
    args = parser.parse_args()
    cite(args.query, args.k)


if __name__ == "__main__":
    main()
