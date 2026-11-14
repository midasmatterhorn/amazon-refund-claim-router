"""Checker tests: a router answer is only accepted if it fits the routing shape.

Allowing only billing / shipping / stock; at least one specialist; no duplicates;
confidence within [0, 1]; a non-empty reason. Everything else must be rejected.
"""
import pytest
from pydantic import ValidationError

from checker import check_decision
from schema import Specialist


def test_valid_single_specialist_passes():
    decision = check_decision(
        {"specialists": ["billing"], "reason": "double charge", "confidence": 0.9}
    )
    assert decision.specialists == [Specialist.BILLING]
    assert decision.confidence == 0.9


def test_all_three_specialists_pass():
    decision = check_decision(
        {
            "specialists": ["shipping", "stock", "billing"],
            "reason": "lost box, double charge and oversold line",
            "confidence": 0.75,
        }
    )
    assert {s.value for s in decision.specialists} == {"billing", "shipping", "stock"}


@pytest.mark.parametrize("bad", ["fraud", "Billing", "SHIPPING", "", "stock_team"])
def test_disallowed_specialist_rejected(bad):
    with pytest.raises(ValidationError):
        check_decision({"specialists": [bad], "reason": "r", "confidence": 0.5})


def test_empty_specialists_rejected():
    with pytest.raises(ValidationError):
        check_decision({"specialists": [], "reason": "r", "confidence": 0.5})


def test_duplicate_specialists_rejected():
    with pytest.raises(ValidationError):
        check_decision(
            {"specialists": ["billing", "billing"], "reason": "r", "confidence": 0.5}
        )


@pytest.mark.parametrize("bad", [1.5, -0.1, 2, 100, "high"])
def test_confidence_outside_0_1_rejected(bad):
    with pytest.raises(ValidationError):
        check_decision({"specialists": ["billing"], "reason": "r", "confidence": bad})


@pytest.mark.parametrize("good", [0, 1, 0.0, 1.0, 0.42])
def test_confidence_boundaries_pass(good):
    decision = check_decision(
        {"specialists": ["shipping"], "reason": "tracking stalled", "confidence": good}
    )
    assert 0.0 <= decision.confidence <= 1.0


def test_missing_reason_rejected():
    with pytest.raises(ValidationError):
        check_decision({"specialists": ["billing"], "confidence": 0.5})


def test_empty_reason_rejected():
    with pytest.raises(ValidationError):
        check_decision({"specialists": ["billing"], "reason": "", "confidence": 0.5})


def test_missing_confidence_rejected():
    with pytest.raises(ValidationError):
        check_decision({"specialists": ["billing"], "reason": "r"})


def test_json_string_reply_passes():
    raw = '{"specialists": ["stock"], "reason": "oversold line", "confidence": 0.8}'
    assert check_decision(raw).specialists == [Specialist.STOCK]


def test_markdown_fenced_json_reply_passes():
    raw = '```json\n{"specialists": ["stock"], "reason": "oversold line", "confidence": 0.8}\n```'
    assert check_decision(raw).specialists == [Specialist.STOCK]


def test_prose_wrapped_json_reply_passes():
    raw = (
        "Here is my answer:\n"
        '{"specialists": ["billing", "stock"], '
        '"reason": "charged twice and line canceled", "confidence": 0.66}\n'
        "Thanks!"
    )
    decision = check_decision(raw)
    assert {s.value for s in decision.specialists} == {"billing", "stock"}


def test_plain_text_reply_rejected():
    with pytest.raises((ValidationError, ValueError)):
        check_decision("I think billing is right")


def test_garbage_json_rejected():
    with pytest.raises((ValidationError, ValueError)):
        check_decision('{"specialists": ["billing",] oops')
