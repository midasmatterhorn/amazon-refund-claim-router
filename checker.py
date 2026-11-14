"""Checker: rejects bad router answers before anything downstream sees them.

Only billing, shipping and stock are allowed; at least one specialist; no
duplicates; confidence within [0, 1]; a non-empty reason. Anything else raises
pydantic.ValidationError (or json.JSONDecodeError for unparseable replies).
"""
import json
from typing import Any, Union

from pydantic import ValidationError

from schema import RoutingDecision


def _extract_json(text: str) -> str:
    """Tolerate markdown fences or prose around the JSON object."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise json.JSONDecodeError("no JSON object found in model reply", text, 0)
    return text[start : end + 1]


def check_decision(raw: Union[str, dict, Any]) -> RoutingDecision:
    """Validate a raw model reply (JSON string, fenced JSON, or dict).

    Raises json.JSONDecodeError for replies without a JSON object and
    pydantic.ValidationError for answers outside the allowed shape.
    """
    if isinstance(raw, str):
        raw = json.loads(_extract_json(raw))
    return RoutingDecision.model_validate(raw)


__all__ = ["check_decision", "ValidationError"]
