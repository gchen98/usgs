"""Checks for Gary's passage splitting and picking. Run: python -m pytest -q"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cite  # noqa: E402


def test_split_two_sentences():
    passages = cite.split_passages("Water use is estimated by county. Data are updated every five years.")
    assert len(passages) == 2


def test_split_keeps_all_words():
    text = "Irrigation is the largest use. Public supply is second. Thermoelectric is third."
    assert " ".join(cite.split_passages(text)).split() == text.split()


def test_split_empty_text():
    assert [p for p in cite.split_passages("") if p.strip()] == []


def test_split_does_not_break_on_abbreviations():
    # "U.S." should not end a sentence. Decide if you care; delete this test if not.
    passages = cite.split_passages("The U.S. Geological Survey estimates water use. It does so every five years.")
    assert len(passages) == 2


def test_pick_includes_best_passage():
    passages = ["A low match.", "The best match.", "Another low one."]
    chosen = cite.pick_passage(passages, np.array([0.1, 0.9, 0.2]))
    assert "The best match." in chosen


def test_doi_link():
    item = {"identifiers": [{"type": "DOI", "key": "doi:10.5066/F7V9868K"}]}
    assert cite.doi_of(item) == "https://doi.org/10.5066/F7V9868K"
