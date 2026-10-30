"""Harvest public ScienceBase items for one search query and cache raw JSON pages.

Usage:
    python scripts/harvest.py                      # "water use", 500 items
    python scripts/harvest.py --query "streamflow" --target 500

Each page of results is saved to data/raw/<slug>/offset_<NNNNN>.json as soon as it
arrives. Rerunning skips pages already on disk, so a crash only costs the page in flight.

API notes (checked against the live API and the public ScienceBase docs, Oct 29 2026):
- Search endpoint: https://www.sciencebase.gov/catalog/items?q=...&format=json
- Paging: `max` (page size) + `offset`; the response has `total` and a `nextlink`
  that is absent on the last page. Docs say max/offset should be multiples of 5.
- `fields=` limits which item fields come back; without it you get id/title/link only.
- Data releases can be filtered with `filter=systemType=Data Release`; we do NOT filter
  here (option A: mixed sample) but keep `systemTypes` so M2 can compare the groups.
"""

import argparse
import json
import re
import time
from pathlib import Path

import requests

BASE_URL = "https://www.sciencebase.gov/catalog/items"
USER_AGENT = "usgs-fair-learning-project (personal study; polite harvester)"
PAGE_SIZE = 100
PAUSE_SECONDS = 1.0  # between requests, to be polite
MAX_RETRIES = 4

# Top-level fields seen on a full ScienceBase item; enough for M2 scoring and M3 search.
FIELDS = [
    "title", "summary", "body", "purpose", "citation", "identifiers", "provenance",
    "contacts", "webLinks", "browseCategories", "browseTypes", "systemTypes", "tags",
    "dates", "spatial", "files", "distributionLinks", "parentId", "hasChildren",
    "maintenanceUpdateFrequency",
]


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def fetch_page(session, query, offset):
    """GET one page, retrying on network errors, 429 and 5xx with exponential backoff."""
    params = {
        "q": query,
        "format": "json",
        "max": PAGE_SIZE,
        "offset": offset,
        "fields": ",".join(FIELDS),
    }
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = session.get(BASE_URL, params=params, timeout=60)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise requests.HTTPError(f"HTTP {resp.status_code}", response=resp)
            resp.raise_for_status()  # other 4xx: a real bug, fail immediately
            return resp.json()
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as err:
            retryable = not isinstance(err, requests.HTTPError) or (
                err.response is not None
                and (err.response.status_code == 429 or err.response.status_code >= 500)
            )
            if not retryable or attempt == MAX_RETRIES:
                raise
            wait = 2 ** attempt * 5  # 5, 10, 20, 40 s
            print(f"  offset {offset}: {err}; retrying in {wait}s")
            time.sleep(wait)


def harvest(query, target, out_root):
    out_dir = out_root / slugify(query)
    out_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    n_items = 0
    for offset in range(0, target, PAGE_SIZE):
        path = out_dir / f"offset_{offset:05d}.json"
        if path.exists():
            page = json.loads(path.read_text())
            print(f"offset {offset}: cached ({len(page['items'])} items)")
        else:
            page = fetch_page(session, query, offset)
            path.write_text(json.dumps(page, indent=1))
            print(f"offset {offset}: fetched {len(page['items'])} items (total {page['total']})")
            time.sleep(PAUSE_SECONDS)
        n_items += len(page["items"])
        if "nextlink" not in page:
            break
    if n_items < target:
        print(f"Warning! Did not fetch the requested number of items {target}!")

    print(f"Done: {n_items} items in {out_dir}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--query", default="water use")
    parser.add_argument("--target", type=int, default=500)
    parser.add_argument("--out", type=Path, default=Path("data/raw"))
    args = parser.parse_args()
    harvest(args.query, args.target, args.out)


if __name__ == "__main__":
    main()
