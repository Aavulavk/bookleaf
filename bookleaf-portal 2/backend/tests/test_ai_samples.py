"""Checks the AI against the 7 sample queries from the assignment.
Offline tests always run; live tests need ANTHROPIC_API_KEY (set it in your shell and
run `pytest tests/test_ai_samples.py -m live`)."""
import os
from datetime import date

import pytest

from app.ai import service as ai
from app.ai.service import _parse_json, heuristic_classify, payout_cycle
from app.ai.client import LLMError

SAMPLES = [
    ("Royalty not received", "I published my book 4 months ago and still haven't received any royalty. What's going on?", "Royalty & Payments"),
    ("Royalty too low", "My royalty amount seems too low. I sold 200 copies but only received Rs 3,000.", "Royalty & Payments"),
    ("ISBN mismatch", "My book is showing a different ISBN on Amazon than what's on the physical copy.", "ISBN & Metadata Issues"),
    ("Print quality", "I received my author copies and the print quality is terrible. Images are blurry and pages are misaligned.", "Printing & Quality"),
    ("Unavailable on Amazon", "My book is published but it's showing as Currently Unavailable on Amazon.", "Distribution & Availability"),
    ("Still in typesetting", "It's been 3 weeks and my book is still in typesetting. When will it be done?", "Book Status & Production Updates"),
    ("Update description", "Can I update the description of my book on Amazon after it's already live?", "General Inquiry"),
]


def test_parse_json_accepts_wrapped_output():
    assert _parse_json('Sure! {"category":"General Inquiry","priority":"Low","reason":"x"}')["priority"] == "Low"


def test_parse_json_rejects_invalid_values():
    with pytest.raises(LLMError):
        _parse_json('{"category":"Nonsense","priority":"Low","reason":"x"}')


def test_isbn_fallback_is_at_least_high():
    assert heuristic_classify(*SAMPLES[2][:2])["priority"] in ("High", "Critical")


def test_payout_cycle_is_quarter_end_plus_45_days():
    last, deadline = payout_cycle(date(2026, 10, 27))
    assert last == date(2026, 9, 30) and deadline == date(2026, 11, 14)


@pytest.mark.live
@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="needs ANTHROPIC_API_KEY")
@pytest.mark.parametrize("subject,body,expected", SAMPLES)
def test_live_classification(subject, body, expected):
    assert ai.classify(subject, body)["category"] == expected
