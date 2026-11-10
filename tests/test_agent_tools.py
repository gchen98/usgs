"""Checks for agent/tools.py. These run without the LLM server. Run: python -m pytest -q"""

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))
sys.path.insert(0, str(ROOT / "scripts"))
import tools  # noqa: E402
from langchain_core.utils.function_calling import convert_to_openai_tool  # noqa: E402

MAX_CHARS = 1200
ITEM_ID = re.compile(r"\b[0-9a-f]{24}\b")
KANSAS_2014 = "577537cae4b07dd077c70843"  # "Irrigation water use in Kansas, 2014", a data release


def run(tool, **args):
    out = tool.invoke(args)
    assert isinstance(out, str)
    assert len(out) <= MAX_CHARS, f"{tool.name} returned {len(out)} chars"
    return out


# --- descriptions: what the model sees on every call ---------------------------------

def test_every_tool_has_a_real_description():
    for t in tools.TOOLS:
        assert t.description.strip() not in ("", "✍"), t.name


def test_all_schemas_together_stay_small():
    # Sent (and, the first time, read at ~6 tokens/s) on every call.
    total = sum(len(json.dumps(convert_to_openai_tool(t))) for t in tools.TOOLS)
    assert total < 4000, f"tool schemas are {total} chars"


# --- behaviour --------------------------------------------------------------------------

def test_search_returns_k_hits_with_ids():
    out = run(tools.search_items, query="irrigation water use in Kansas", k=3)
    assert len(ITEM_ID.findall(out)) == 3
    assert "Kansas" in out


def test_search_clamps_k():
    out = run(tools.search_items, query="water use", k=50)
    assert len(ITEM_ID.findall(out)) <= 10


def test_item_details_known_item():
    out = run(tools.item_details, item_id=KANSAS_2014)
    assert "Kansas" in out and "doi" in out.lower()


def test_item_details_unknown_id_does_not_raise():
    out = run(tools.item_details, item_id="not-a-real-id")
    assert "not-a-real-id" in out


def test_score_summary_data_releases():
    out = run(tools.score_summary, group="data_release")
    assert "197" in out and "0.9" in out


def test_find_anomalies_missing_doi():
    out = run(tools.find_anomalies, check="data_release_missing_doi")
    assert re.search(r"\b4\b", out)


def test_find_anomalies_respects_limit():
    out = run(tools.find_anomalies, check="dup_titles", limit=2)
    assert len(ITEM_ID.findall(out)) <= 2


@pytest.mark.parametrize("bad", [{"check": "nonsense"}, {"group": "everything"}])
def test_bad_enum_values_are_rejected_by_schema(bad):
    t = tools.find_anomalies if "check" in bad else tools.score_summary
    with pytest.raises(Exception):
        t.invoke(bad)


# --- added Nov 8: cases the first tests missed -----------------------------------------

def test_score_summary_other_group():
    out = run(tools.score_summary, group="other")
    assert "303" in out


def test_score_summary_reports_rule_pass_rates():
    out = run(tools.score_summary, group="all")
    assert "has_doi" in out


def test_find_anomalies_total_is_not_the_limit():
    # 18 duplicate-title flags in the Phase 1 run; asking for 2 must still report 18.
    out = run(tools.find_anomalies, check="dup_titles", limit=2)
    assert re.search(r"\b18\b", out)


def test_item_details_shows_release_status_and_doi_link():
    out = run(tools.item_details, item_id=KANSAS_2014)
    assert "data release" in out.lower()
    assert "10.5066/" in out


def test_search_tags_data_releases():
    out = run(tools.search_items, query="irrigation water use in Kansas", k=5)
    assert "Data Release" in out


# --- added Nov 9: defaults and empty results --------------------------------------------

@pytest.mark.parametrize("check", ["data_release_missing_doi", "short_summary", "dup_titles"])
def test_find_anomalies_default_limit_fits(check):
    run(tools.find_anomalies, check=check)  # default limit, as the model will usually call it


def test_find_anomalies_with_nothing_flagged(monkeypatch):
    monkeypatch.setattr(tools.anomalies, "CHECKS", [("dup_titles", lambda name, items: [])])
    out = run(tools.find_anomalies, check="dup_titles")
    assert re.search(r"\b0\b", out)
