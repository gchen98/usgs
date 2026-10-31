"""Small hand-made items for the anomaly checks. Run: python -m pytest -q"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import anomalies  # noqa: E402

GOOD_DOI = {"type": "DOI", "key": "doi:10.5066/F7V9868K"}


def release(item_id, identifiers):
    return {"id": item_id, "systemTypes": ["Data Release"], "identifiers": identifiers}


def flagged_ids(check, items):
    return {row[0] for row in check("check", items)}


def test_release_with_doi_is_not_flagged():
    assert flagged_ids(anomalies.data_release_missing_doi, [release("a", [GOOD_DOI])]) == set()


def test_release_without_identifiers_is_flagged():
    assert flagged_ids(anomalies.data_release_missing_doi, [release("a", [])]) == {"a"}


def test_non_release_without_doi_is_not_flagged():
    assert flagged_ids(anomalies.data_release_missing_doi, [{"id": "a"}]) == set()


def test_valid_doi_after_a_malformed_one_is_not_flagged():
    # One good DOI should be enough, wherever it appears in the list.
    bad = {"type": "DOI", "key": "10.5066/F7V9868K"}
    assert flagged_ids(anomalies.data_release_missing_doi, [release("a", [bad, GOOD_DOI])]) == set()


def test_short_summary_flagged_and_long_one_not():
    items = [{"id": "a", "summary": "A"}, {"id": "b", "summary": "Water use by county " * 10}]
    assert flagged_ids(anomalies.short_summary, items) == {"a"}


def test_duplicate_titles_flagged():
    items = [{"id": "a", "title": "Water Use"}, {"id": "b", "title": "Water Use"},
             {"id": "c", "title": "Something else"}]
    flagged = flagged_ids(anomalies.dup_titles, items)
    assert "c" not in flagged
    assert flagged & {"a", "b"}
