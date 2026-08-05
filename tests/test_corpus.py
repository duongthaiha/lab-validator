"""Tests for anchor resolution against a lab's parsed instructions.

The subject here is a specific, expensive mistake. A judgement recorded against
an anchor that names no heading is not rejected and not flagged: it is written,
it appears in the section report, and the only trace is a coverage count that
says a task is unjudged without saying which. The walk then looks finished.

The anchors themselves invite it. A heading titled "Foundry - Overview page"
becomes ``foundry---overview-page``, because the spaced dash contributes a
hyphen of its own on each side, and one hyphen is the natural guess.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lab_validator.corpus import Heading, Outline  # noqa: E402


def make_outline() -> Outline:
    heads = [
        Heading(
            order=0, level=3,
            id="1-ensure-that-you-are-on-the-microsoft-foundry---overview-page",
            text="1. Ensure that you are on the Microsoft Foundry - Overview page",
        ),
        Heading(order=1, level=3, id="2-deploy-a-model", text="2. Deploy a model"),
        Heading(order=2, level=1, id="setup", text="Setup"),
    ]
    return Outline(title="Demo", headings=heads, ids=[h.id for h in heads])


def test_a_correct_anchor_resolves() -> None:
    outline = make_outline()
    assert outline.by_id("2-deploy-a-model") is not None
    assert outline.by_id("#2-deploy-a-model") is not None


def test_the_collapsed_hyphen_guess_does_not_resolve() -> None:
    # The premise of the whole fix: this is a plausible anchor that is wrong.
    outline = make_outline()
    assert outline.by_id(
        "1-ensure-that-you-are-on-the-microsoft-foundry-overview-page"
    ) is None


def test_a_collapsed_hyphen_is_suggested_first() -> None:
    outline = make_outline()
    near = outline.suggest("1-ensure-that-you-are-on-the-microsoft-foundry-overview-page")
    assert near[0] == "1-ensure-that-you-are-on-the-microsoft-foundry---overview-page"


def test_punctuation_differences_alone_are_an_exact_match() -> None:
    # Stripped to alphanumerics these are the same key, so the fuzzy ranker is
    # never consulted -- it could otherwise put a similarly-long stranger first.
    outline = make_outline()
    assert outline.suggest("2_deploy_a_model") == ["2-deploy-a-model"]


def test_a_near_miss_is_suggested() -> None:
    outline = make_outline()
    assert outline.suggest("2-deploy-a-modle") == ["2-deploy-a-model"]


def test_nothing_is_suggested_for_an_unrelated_anchor() -> None:
    outline = make_outline()
    assert outline.suggest("zzzzzzzzzzzzzzzzzzzz") == []


def test_an_empty_anchor_suggests_nothing() -> None:
    assert make_outline().suggest("") == []
    assert make_outline().suggest("#") == []


def test_suggestions_are_capped() -> None:
    heads = [
        Heading(order=i, level=3, id=f"{i}-deploy-a-model", text=f"{i}. Deploy a model")
        for i in range(10)
    ]
    outline = Outline(title="Demo", headings=heads, ids=[h.id for h in heads])
    assert len(outline.suggest("3-deploy-a-modelx", limit=3)) <= 3


def test_headings_are_searched_even_when_ids_was_not_populated() -> None:
    # `ids` is a separate field on the dataclass and older run folders may not
    # carry it. Suggestions must not silently go quiet in that case.
    heads = [Heading(order=0, level=3, id="2-deploy-a-model", text="2. Deploy a model")]
    outline = Outline(title="Demo", headings=heads)
    assert outline.suggest("2-deploy-a-modle") == ["2-deploy-a-model"]
