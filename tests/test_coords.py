"""Malformed `--do` arguments must teach, not crash.

Two shapes were observed live, both mid-walk against a running lab clock:

    --do scroll:400        # one coordinate where two are required
    --do "click:Not now"   # a button label where pixels are required

Both reached `int(...)` inside the action loop and raised a bare `IndexError`
or `ValueError`. The operator saw a traceback, which reads as "the tool broke",
and nothing in it said what the verb actually takes. The second is the more
insidious of the two: it is what someone reaches for after a week of DOM
automation, and the answer -- that the VM is a video frame with no DOM to
query -- is precisely the thing the message has to say.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _lab_step():
    spec = importlib.util.spec_from_file_location(
        "lab_step_coords", ROOT / "scripts" / "lab_step.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


STEP = _lab_step()


def test_a_well_formed_pair_parses():
    assert STEP.coords("click", "640,400", 2)[:2] == [640, 400]


def test_whitespace_around_coordinates_is_tolerated():
    assert STEP.coords("click", " 640 , 400 ", 2)[:2] == [640, 400]


def test_scroll_keeps_its_optional_third_value():
    assert STEP.coords("scroll", "610,400,-4000", 2) == [610, 400, -4000]


def test_one_coordinate_where_two_are_needed_is_refused_not_crashed():
    with pytest.raises(STEP.Stop) as caught:
        STEP.coords("scroll", "400", 2)
    message = str(caught.value)
    assert "scroll" in message, "the message must name the verb that refused"
    assert "x,y" in message, "the message must give the shape that would work"
    assert "example:" in message


def test_a_button_label_where_pixels_are_needed_explains_why():
    with pytest.raises(STEP.Stop) as caught:
        STEP.coords("click", "Not now", 2)
    message = str(caught.value)
    assert "coordinates, not text" in message
    assert "video frame" in message, (
        "the message must say why there is no click-by-text, or the operator "
        "will simply look for the flag that does it"
    )
    assert "shot" in message, "it must name the way that does work"


def test_a_partly_numeric_argument_is_still_refused():
    with pytest.raises(STEP.Stop):
        STEP.coords("click", "640,middle", 2)


@pytest.mark.parametrize("verb", ["click", "dblclick", "move", "scroll"])
def test_every_coordinate_verb_routes_through_the_guard(verb):
    """Not one of them may keep a bare `int(...)` on the argument."""
    with pytest.raises(STEP.Stop):
        STEP.coords(verb, "nope", 2)


def test_wait_refuses_a_non_number_rather_than_crashing():
    step = object()
    with pytest.raises(STEP.Stop) as caught:
        import asyncio

        asyncio.run(STEP.ACTIONS["wait"](step, "a while"))
    assert "milliseconds" in str(caught.value)


def test_page_refuses_a_non_number_rather_than_crashing():
    step = object()
    with pytest.raises(STEP.Stop) as caught:
        import asyncio

        asyncio.run(STEP.ACTIONS["page"](step, "three"))
    assert "page number" in str(caught.value)
