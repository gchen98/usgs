"""Checks for Gary's recall@k and build_text. Run: python -m pytest -q"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import search  # noqa: E402

RANKED = ["a", "b", "c", "d", "e"]


def test_hit_at_rank_one():
    assert search.recall_at_k(RANKED, ["a"], 1) == 1.0


def test_hit_just_outside_k():
    assert search.recall_at_k(RANKED, ["c"], 2) == 0.0


def test_partial_recall_with_two_relevant():
    assert search.recall_at_k(RANKED, ["a", "z"], 5) == 0.5


def test_k_larger_than_list():
    assert search.recall_at_k(RANKED, ["e"], 100) == 1.0


def test_build_text_survives_missing_fields():
    assert isinstance(search.build_text({"id": "x"}), str)
