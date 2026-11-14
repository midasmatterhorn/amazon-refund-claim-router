# Build Notes — Claim 1 Routing Run

**Date:** 2026-11-14
**Model:** `baidu/ernie-5.5-flash-preview:free` — read from `OPENROUTER_MODEL` in a git-ignored `.env`.
The API key (`OPENROUTER_API_KEY`) lives in the same ignored file and never appears in code, chat, or this repo.

## Command

```bash
.venv/bin/python -I run_claim.py --claims data/claims.csv --claim-id CLM-0001
```

The router received **claim 1's `claim_text` only** — no labels, no amounts, no
investigator notes. The OpenRouter request used structured output
(`response_format: json_schema`, strict) and the reply was validated by the
Pydantic checker before anything was printed.

## Printed decision (verbatim from the run)

```json
{
  "claim_id": "CLM-0001",
  "model": "baidu/ernie-5.5-flash-preview:free",
  "decision": {
    "specialists": [
      "billing",
      "shipping",
      "stock"
    ],
    "reason": "The claim describes a duplicate charge (“card was charged twice for the whole order”), a missing item from the delivery (“only one box showed up with the stroller”), and an inventory problem (“car seat is out of stock”).",
    "confidence": 0.95
  },
  "label_specialists": "billing|shipping|stock",
  "match": true
}
```

## How the specialists match `label_specialists`

| Router says | Investigator label | Verdict |
|---|---|---|
| `["billing", "shipping", "stock"]` | `billing\|shipping\|stock` | **Exact match — 3/3** |

- **billing** ↔ duplicate charge ("my card was charged twice for the whole order")
- **shipping** ↔ missing shipment ("Only one box showed up with the stroller")
- **stock** ↔ oversold line ("the seller page says the car seat is out of stock")

This also demonstrates the design decision recorded in the README: one claim
*can* list more than one specialist, so `specialists` is a set of 1–3 values.

## Key prompt excerpt

> "You route Amazon A-to-z refund claims to specialist teams.
> Specialists and their signals: **billing**: money problems — duplicate/double
> charges, a charge posted after a cancellation…; **shipping**: delivery problems
> — package lost, tracking stalled…, 'delivered' but nothing arrived…;
> **stock**: inventory problems — item oversold or out of stock… A claim may
> need one, two, or all three specialists; include every specialist whose
> problem the claim text actually describes. Judge only from the claim text…"

Full prompt: `router.py::ROUTER_SYSTEM_PROMPT`. JSON shape sent to OpenRouter:
`router.py::JSON_SCHEMA` (strict, `additionalProperties: false`).

## What I checked

The reply passed the Pydantic checker (`check_decision`) before printing, and
the printed model id comes straight from `OPENROUTER_MODEL`
(`baidu/ernie-5.5-flash-preview:free`) — the same id to verify on the OpenRouter
Activity page for this request.

## Test suite

35 pytest tests passing — checker rejections (only billing/shipping/stock,
confidence 0–1, no duplicates/empties), router structured-output fallback and
reprompt paths, and label matching.
