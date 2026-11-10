"""Tools the agent can call. Each wraps Phase 1 code and returns a SHORT string.

Interface spec (Claude); bodies and descriptions (Gary).

Rules from the A0 benchmark:
- Return compact text, never raw JSON: every character the tool returns is read by the model
  at ~6 tokens/s. Tests cap each result at 1,200 characters (~300 tokens).
- Never raise on bad input (unknown id, k out of range). Return a short message the model can
  act on, e.g. "No item with id X. Use search_items to find ids."
- The docstring IS the description the model sees on every call. Keep it short and specific:
  what the tool does, when to use it, what each argument means.
"""

import sys
from pathlib import Path
from typing import Literal
from functools import lru_cache



from langchain_core.tools import tool

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT / "scripts"))
import search
import anomalies
import score


AnomalyCheck = Literal["data_release_missing_doi", "short_summary", "dup_titles"]

Group = Literal["all", "data_release", "other"]


@lru_cache(maxsize=1)
def _all_items():
    items = search.load_items()
    return items

@lru_cache(maxsize=1)
def _search_resources():
    items = _all_items()
    model = search.get_model()
    index = search.build_index(items,model)
    return items,model,index

@lru_cache(maxsize=1)
def _all_scores():
    items = _all_items()
    return score.score_all(items)


@lru_cache(maxsize=1)
def _items_by_id():
    items, _, _ = _search_resources()
    return {item["id"]: item for item in items}

@tool
def search_items(query: str, k: int = 5) -> str:
    """
    Call this when you only have a concept to query to get related items.
    Clamps results to a max of 10.
    Fields returned include :
    rank,id,similarity,title,is Data Release
    """
    # Use scripts/search.py. Clamp k to 1..10. One line per hit: rank, id, similarity,
    # [Data Release] tag, title (truncate long titles).
    items,model,index = _search_resources()
    by_id = _items_by_id()
    results = []
    rank = 0
    clamped_k = max(1,min(k,10))
    for item_id,sim,title in search.search(query = query,items=items,index=index,model=model,k=clamped_k):
        rank+=1
        item = by_id[item_id]
        is_data_release = "Data Release" in item.get("systemTypes", [])
        if len(title)>50:
            title = title[:50]+'...'
        results.append(f"rank:{rank},id:{item_id},similarity:{sim:.2f},title:{title},is Data Release:{is_data_release}")
    result_str =  "\n".join(results)
    # print(f"Result str {result_str}")
    return result_str
    # raise NotImplementedError


@tool
def item_details(item_id: str) -> str:
    """
    When you have an item id available, call this to get more details including its score
    (proportion of metadata rules it passes)
    Fields include:
    Title,is Data Release,doi link,parent ID,has_doi,has_non_image_files,
    has_good_boundingbox,has_keywords_with_type,has_weblinks_uri,score.
    """
    # Title, data release or not, DOI (or "none"), parent id, completeness score and which
    # rules it failed, ScienceBase link. Unknown id -> a helpful message, not an exception.
    by_id = _items_by_id()
    if item_id not in by_id:
        return f"This item {item_id} not found. Suggest using search_items to find IDs."

    item = by_id[item_id]
    title = item.get('title','')
    is_data_release = "Data Release" in item.get("systemTypes", [])
    doi_link = None
    for identifier in item.get("identifiers", []):
        if "type" in identifier and identifier['type']=='DOI':
            doi_link = identifier.get('key','')
            break
    parent_id = item.get('parentId',None)

    score_map = score.score_item(item)
    score_outlist=[]
    for k,v in score_map.items():
        score_outlist.append(f"{k}:{v}")
    score_out_str = ",".join(score_outlist)
    return f"Title:{title},is Data Release:{is_data_release},doi link:{doi_link},parent ID:{parent_id},{score_out_str}"


@tool
def score_summary(group: Group = "all") -> str:
    """
    When you want to get summary statistics for a group of interest like all items, data releases, or
    non data releases call this. Fields returned include
    items in group, mean score (each item's score is proportion of rules passing), pass rate for each
    rule (proportion of items passing that rule).
    """
    # Use scripts/score.py. Item count, mean score, pass rate per rule, for the group.
    df_scores = _all_scores()
    # filter down the rows
    if group == 'data_release':
        df_scores = df_scores[df_scores["is_data_release"]]
    elif group == 'other':
        df_scores = df_scores[~df_scores["is_data_release"]]
    # get the list of rule names which correspond to df columns
    rules = score.RULES
    rule_names = [rule[0] for rule in rules]
    rule_outlist = []
    for rule_name in rule_names:
        rule_outlist.append(rule_name + ":" + f"{df_scores[rule_name].mean():.2f}")
    rule_means = ",".join(rule_outlist)
    mean_score =  f"{df_scores['score'].mean():.2f}"
    total_results = len(df_scores)
    return f"Total items: {total_results} Mean score: {mean_score}  Rule means: {rule_means}"

@tool
def find_anomalies(check: AnomalyCheck, limit: int = 5) -> str:
    """
    To get the items where anomalies are found, call this function. It will
    return the total items found, and one line for each item.
    3 checks are available: if a data release is missing a DOI string,
    if the summary is less than 20 words, or if there are items with duplicate titles.
    Clamps the result to a max of parameter limit. Fields for each item include:
    item_id,title,detail
    """
    # Use scripts/anomalies.py. Total number flagged, then up to `limit` lines of id + title + detail.
    items = _all_items()
    by_id = _items_by_id()
    for check_name, check_func in anomalies.CHECKS:
        if check == check_name:
            item_checks = check_func(check_name,items)
            if len(item_checks)==0:
                return f"0 anomalies were found for {check_name}"
            clamped_limit = max(1, min(limit, len(item_checks)))
            output_list = []
            for i in range(clamped_limit):
                item_id,check_name,detail = item_checks[i]
                title = by_id[item_id].get('title','')
                if len(detail)>50:
                    detail = detail[:50]+'...'

                output_list.append(f"item_id:{item_id},title:{title},detail:{detail}")
            output_str = "\n".join(output_list)
            return f"Found {len(item_checks)} total items. Returning limited results:\n{output_str}"
    return f"Could not find a check with name {check}"

TOOLS = [search_items, item_details, score_summary, find_anomalies]

# def main():
#     print("Running main")
#     # print(f"search items:\n{search_items.invoke({'query':'water use','k':5})}")
#     # print(f"item details:\n{item_details.invoke({'item_id': '5e8de01382cee42d13468789'})}")
#     # print(f"score_summary:\n{score_summary.invoke({'group': 'other'})}")
#     test = find_anomalies.invoke({'check': 'dup_titles','limit':5})
#     print(f"find_anomalies:\n{test} with length {len(test)} ")
#
#
#
#
#
# if __name__=='__main__':
#     main()