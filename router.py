"""Router: ask OpenRouter for a structured routing decision, validate with Pydantic.

Strategy:
1. Ask with OpenRouter structured output (`response_format: json_schema`, strict).
2. If the model/provider rejects structured output (HTTP 400), fall back to
   prompt-only JSON.
3. If an answer fails the checker, feed the complaint back for one corrected
   retry. Nothing invalid ever leaves this module.
"""
import json
from typing import List

import requests
from pydantic import ValidationError

from checker import check_decision
from schema import RoutingDecision

# Fixed https endpoint on a public API host; no user-supplied URL reaches this module.
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

ROUTER_SYSTEM_PROMPT = """You route Amazon A-to-z refund claims to specialist teams.

Specialists and their signals:
- billing: money problems — duplicate/double charges, a charge posted after a
  cancellation, fees or amounts that do not match the receipt, missing refunds
  or credits.
- shipping: delivery problems — package lost, tracking stalled or stopped,
  "delivered" but nothing arrived, items missing from the box.
- stock: inventory problems — item oversold or out of stock, seller cannot
  supply or has no restock date, an order line canceled for unavailability.

Rules:
- A claim may need one, two, or all three specialists; include every specialist
  whose problem the claim text actually describes.
- Judge only from the claim text; do not invent facts.
- reason: 1-2 sentences citing the exact signals you saw.
- confidence: 0.0-1.0 for how sure you are about the specialist set.
"""

JSON_ONLY_HINT = (
    " Reply with ONLY a JSON object: "
    '{"specialists": ["billing"], "reason": "...", "confidence": 0.0} '
    "where specialists is a non-empty array drawn from billing, shipping, stock "
    "and confidence is a number between 0 and 1."
)

JSON_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "routing_decision",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "specialists": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string", "enum": ["billing", "shipping", "stock"]},
                },
                "reason": {"type": "string", "minLength": 1},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["specialists", "reason", "confidence"],
            "additionalProperties": False,
        },
    },
}


def build_messages(claim_text: str, json_hint: bool = False) -> List[dict]:
    """Build the chat messages; the claim text only ever appears in the user role."""
    system = ROUTER_SYSTEM_PROMPT + (JSON_ONLY_HINT if json_hint else "")
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Route this A-to-z refund claim:\n\n{claim_text}"},
    ]


def _chat(model: str, messages: List[dict], api_key: str, use_json_schema: bool) -> str:
    """One OpenRouter chat completion; returns the reply content."""
    body = {"model": model, "messages": messages, "temperature": 0}
    if use_json_schema:
        body["response_format"] = JSON_SCHEMA
    response = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-Title": "amazon-refund-claim-router",
        },
        json=body,
        timeout=90,
    )
    response.raise_for_status()
    payload = response.json()
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected OpenRouter response shape: {payload}") from exc
    return content or ""


def route_claim(claim_text: str, api_key: str, model: str) -> RoutingDecision:
    """Route one claim (claim_text only) and return a validated RoutingDecision."""
    messages = build_messages(claim_text)
    use_json_schema = True
    last_error: Exception | None = None

    for _ in range(3):
        try:
            reply = _chat(model, messages, api_key, use_json_schema=use_json_schema)
            return check_decision(reply)
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status == 400 and use_json_schema:
                # Model/provider does not accept structured output — retry prompt-only.
                use_json_schema = False
                messages = build_messages(claim_text, json_hint=True)
                continue
            raise
        except (ValidationError, json.JSONDecodeError) as exc:
            last_error = exc
            messages = messages + [
                {"role": "assistant", "content": reply},
                {
                    "role": "user",
                    "content": (
                        "Your answer was rejected by the checker. "
                        f"Problem: {exc}. Reply again with ONLY the corrected JSON object."
                    ),
                },
            ]

    raise RuntimeError(f"No valid decision after retries; last checker error: {last_error}")
