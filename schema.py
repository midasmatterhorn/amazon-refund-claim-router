"""Typed routing decision for Amazon A-to-z refund claims.

DESIGN DECISION — one claim CAN list more than one specialist.
The labeled 15-claim test set uses pipe-separated specialist sets and 7 of 15
claims carry two or three labels (e.g. "billing|shipping|stock" for a double
charge + missing shipment + oversold line), so `specialists` is a non-empty,
duplicate-free list restricted to the three allowed teams — not a single value.
"""
from enum import Enum
from typing import List

from pydantic import BaseModel, Field, field_validator


class Specialist(str, Enum):
    """The only specialist teams a claim may be routed to."""

    BILLING = "billing"
    SHIPPING = "shipping"
    STOCK = "stock"


class RoutingDecision(BaseModel):
    """The only shape the router is allowed to answer with."""

    specialists: List[Specialist] = Field(
        ...,
        min_length=1,
        description="Every specialist the claim needs; subset of billing/shipping/stock.",
    )
    reason: str = Field(
        ...,
        min_length=1,
        description="Short evidence-based justification drawn from the claim text.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="0.0 = guessing, 1.0 = certain of the specialist set.",
    )

    @field_validator("specialists")
    @classmethod
    def _no_duplicates(cls, value: List[Specialist]) -> List[Specialist]:
        if len(set(value)) != len(value):
            raise ValueError("specialists must not repeat a specialist")
        return value
