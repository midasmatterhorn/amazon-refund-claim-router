"""Router tests: structured output is requested first, prompt-only JSON is the fallback,
and an invalid answer is fed back to the model for one corrected retry."""
import json

import pytest
import requests

import router
from schema import Specialist


def test_json_schema_request_only_allows_the_three_specialists():
    props = router.JSON_SCHEMA["json_schema"]["schema"]["properties"]
    assert props["specialists"]["items"]["enum"] == ["billing", "shipping", "stock"]
    assert props["confidence"]["minimum"] == 0
    assert props["confidence"]["maximum"] == 1
    assert router.JSON_SCHEMA["json_schema"]["strict"] is True


def test_build_messages_put_claim_in_user_role_only():
    messages = router.build_messages("my claim text")
    assert [m["role"] for m in messages] == ["system", "user"]
    assert "my claim text" in messages[1]["content"]
    assert "my claim text" not in messages[0]["content"]


def test_route_claim_accepts_valid_reply(monkeypatch):
    reply = json.dumps(
        {
            "specialists": ["billing", "shipping"],
            "reason": "double charge, box never arrived",
            "confidence": 0.8,
        }
    )
    seen = {}

    def fake_chat(model, messages, api_key, use_json_schema):
        seen["use_json_schema"] = use_json_schema
        return reply

    monkeypatch.setattr(router, "_chat", fake_chat)
    decision = router.route_claim("claim text", api_key="k", model="test-model:free")
    assert seen["use_json_schema"] is True  # structured output tried first
    assert {s.value for s in decision.specialists} == {"billing", "shipping"}


def test_route_claim_falls_back_when_structured_output_rejected(monkeypatch):
    error = requests.HTTPError("400 Bad Request")
    error.response = type("FakeResponse", (), {"status_code": 400})()
    calls = []

    def fake_chat(model, messages, api_key, use_json_schema):
        calls.append(use_json_schema)
        if use_json_schema:
            raise error
        return json.dumps(
            {"specialists": ["stock"], "reason": "oversold line", "confidence": 0.7}
        )

    monkeypatch.setattr(router, "_chat", fake_chat)
    decision = router.route_claim("claim text", api_key="k", model="test-model:free")
    assert calls == [True, False]  # schema first, then prompt-only fallback
    assert decision.specialists == [Specialist.STOCK]


def test_route_claim_reprompts_on_invalid_answer(monkeypatch):
    bad_reply = '{"specialists": ["fraud"], "reason": "x", "confidence": 0.5}'
    good_reply = json.dumps(
        {"specialists": ["billing"], "reason": "double charge", "confidence": 0.6}
    )
    replies = iter([bad_reply, good_reply])
    role_shapes = []

    def fake_chat(model, messages, api_key, use_json_schema):
        role_shapes.append([m["role"] for m in messages])
        return next(replies)

    monkeypatch.setattr(router, "_chat", fake_chat)
    decision = router.route_claim("claim text", api_key="k", model="test-model:free")
    assert {s.value for s in decision.specialists} == {"billing"}
    assert role_shapes[1][-2:] == ["assistant", "user"]  # rejection fed back
