"""Data anomaly checker for science base items.

Usage:
    python scripts/anomalies.py            # writes data/derived/anomalies.csv

"""

import glob
import json
from pathlib import Path
from collections import defaultdict

import pandas as pd

RAW_GLOB = "data/raw/water_use/*.json"
OUT_PATH = Path("data/derived/anomalies.csv")
MIN_SUMMARY = 20 # 20 words in summary

def data_release_missing_doi(check_name,items):
    anomalies = []
    # print(f"checking missing doi on {len(items)}")
    for item in items:
        id =  item.get('id', '')
        # if 'systemTypes' in item:
        #     print(f"systemtypes {item['systemTypes']}")
        is_data_release =  any(systemType=='Data Release' for systemType in item.get("systemTypes", []))
        # now check if this data release has doi
        if is_data_release:
            # print(f"Found a data release")
            is_valid = False
            detail = "No DOI type identifier"
            for identifier in item.get('identifiers',[]):
                if identifier.get('type','')=='DOI' and len(identifier.get('key',''))>4:
                    # print(f"Got DOI")
                    if identifier['key'][:4] in ['DOI:','doi:']:
                        # print(f"got DOI prefix")
                        is_valid = True
                    else:
                        detail = "DOI ID was not prefixed correctly"

            if not is_valid:
                # print(f"detail {detail}")
                anomalies.append((id,check_name,detail))
    return anomalies

def short_summary(check_name,items):
    anomalies = []
    for item in items:
        id =  item.get('id', '')
        if 'summary' in item:
            summary_words = item['summary'].split()
            if len(summary_words) < MIN_SUMMARY:
                detail = f"Short summary of only length {len(summary_words)} words: {item['summary']}"
                anomalies.append((id,check_name,detail))
    return anomalies

def dup_titles(check_name,items):
    anomalies = []
    title_clusters = defaultdict(list)
    title_set = set()
    for item in items:
        id =  item.get('id', '')
        if 'title' in item:
            title = item['title']
            title_clusters[title].append(id)
            if title in title_set:
                detail = f'Duplicate title of {title}, ids so far are {title_clusters[title]}'
                anomalies.append((id,check_name,detail))
            else:
                title_set.add(title)
    return anomalies

CHECKS = [
    ("data_release_missing_doi",data_release_missing_doi),
    ("short_summary",short_summary),
    ("dup_titles",dup_titles),
]


# --- Plumbing ----------------------------------------------------------------------


def load_items(pattern=RAW_GLOB):
    return [i for f in sorted(glob.glob(pattern)) for i in json.loads(Path(f).read_text())["items"]]


def check_all(items):
    anomalies = []
    for check_name, check_func in CHECKS:
        item_checks = check_func(check_name,items)
        anomalies.extend(list(item_checks))

    headers = ['id','check_func','detail']
    df = pd.DataFrame(anomalies,columns=headers)
    return df

    #
    # for item in items:
    #     row = {
    #         "id": item["id"],
    #         "title": item.get("title", ""),
    #         "is_data_release": "Data Release" in item.get("systemTypes", []),
    #         "url": item["link"]["url"],
    #     }
    #     row.update(score_item(item))
    #     rows.append(row)
    # return pd.DataFrame(rows)


def main():

    df = check_all(load_items())
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(df)} rows to {OUT_PATH}")



if __name__ == "__main__":
    main()
