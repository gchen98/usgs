"""Per-item metadata completeness score (a heuristic inspired by FAIR, not an audit).

Usage:
    python scripts/score.py            # writes data/derived/scores.csv

GARY: fill in RULES. Each rule is (name, FAIR letter, function(item) -> bool).
A rule should mean something to a person trying to find or reuse the data, and it
should actually vary across items (the tests check this against the harvest).
"""

import glob
import json
from pathlib import Path

import pandas as pd

RAW_GLOB = "data/raw/water_use/*.json"
OUT_PATH = Path("data/derived/scores.csv")


# --- Gary writes these -------------------------------------------------------------

def has_good_boundingbox(item):
    if 'spatial' in item and 'boundingBox' in item['spatial']:
        boundingBox = item['spatial']['boundingBox']
        if {'minX','maxX','minY','maxY'} == boundingBox.keys():
            return boundingBox['maxX'] > boundingBox['minX'] and boundingBox['maxY'] > boundingBox['minY']
    return False



def has_non_image_files(item):
    previewCount = 0
    if 'files' in item:
        files = item['files']
        for file in files:
            if 'previewImage' in file:
                previewCount+=1
        if previewCount==len(files):
            # this is only previews
            return False
        else:
            # there are actual useful files
            return True
    # no files attached
    return False


def has_doi(item):
    for identifier in item.get("identifiers", []):
        if "type" in identifier and identifier['type']=='DOI':
            return True
    return False


def has_weblinks_uri(item):
    return any(link.get("uri") for link in item.get("webLinks", []))

def has_keywords_with_type(item):
    return any(tag.get('type') for tag in item.get("tags",[]))



RULES = [
    ("has_doi", "F", has_doi),
    ("has_non_image_files", "A", has_non_image_files),
    ("has_good_boundingbox", "I", has_good_boundingbox),
    ("has_keywords_with_type", "I", has_keywords_with_type),
    ("has_weblinks_uri", "R", has_weblinks_uri),


    # ...
]


# --- Plumbing ----------------------------------------------------------------------

def score_item(item):
    """Return {rule_name: bool, ..., "score": fraction of rules passed}."""
    # print("scoring")
    result = {name: bool(rule(item)) for name, _, rule in RULES}
    result["score"] = sum(result.values()) / len(RULES)
    return result


def load_items(pattern=RAW_GLOB):
    return [i for f in sorted(glob.glob(pattern)) for i in json.loads(Path(f).read_text())["items"]]


def score_all(items):
    rows = []

    for item in items:
        row = {
            "id": item["id"],
            "title": item.get("title", ""),
            "is_data_release": "Data Release" in item.get("systemTypes", []),
            "url": item["link"]["url"],
        }
        row.update(score_item(item))
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    df = score_all(load_items())
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(df)} rows to {OUT_PATH}")
    print(df.groupby("is_data_release")["score"].describe())


if __name__ == "__main__":
    main()
