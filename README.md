# Amazon A-to-z Refund Claim Router

**Zero University assignment** — a router that reads one Amazon A-to-z refund
claim and decides which specialist team(s) should tackle it, instead of an
investigator checking by hand. Every specialist then branches on the router's
answer.

The decision is a **typed Pydantic object**, filled by an **OpenRouter model
with structured output**, and guarded by a **checker** that rejects bad answers.

## Design decision: can one claim list more than one specialist?

**Yes — a claim can route to multiple specialists.**

Evidence from the labeled 15-claim test set: 7 of 15 claims carry two or three
pipe-separated labels (e.g. `billing|shipping|stock` — a double charge *plus* a
missing shipment *plus* an oversold line). Real A-to-z claims routinely mix
problems in one buyer message, so `specialists` is a **non-empty set** of
specialists, not a single value:

```json
{
  "specialists": ["billing", "shipping", "stock"],
  "reason": "second charge settled; car seat line never shipped; page now says out of stock",
  "confidence": 0.91
}
```

- `specialists`: 1–3 unique values, only `billing`, `shipping`, `stock`
- `reason`: evidence-based, drawn from the claim text
- `confidence`: number in [0, 1]

## Layout

| File | Role |
|---|---|
| `schema.py` | `RoutingDecision` (Pydantic): enum-restricted specialists, ≥1, no duplicates, confidence 0–1 |
| `checker.py` | `check_decision()` — rejects bad model answers (raises `ValidationError` / `JSONDecodeError`) |
| `router.py` | OpenRouter structured output (`response_format: json_schema`, strict); falls back to prompt-only JSON for models without schema support; feeds checker complaints back for one corrected retry |
| `run_claim.py` | Runs the router on one claim's `claim_text` **only** and prints the validated decision next to the investigator's label |
| `tests/` | 35 pytest tests: checker rejections, router fallback/retry, label matching |

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env    # then paste your key + a :free model id into .env
.venv/bin/python -m pytest
```

## Secrets

The API key and model id are **never in code**. They are read from environment
variables (`OPENROUTER_API_KEY`, `OPENROUTER_MODEL`), optionally loaded from a
local `.env` file that git ignores (see `.gitignore`). `.env.example` shows the
shape. If a key ever leaks, revoke it at https://openrouter.ai/settings/keys.

## Run claim 1

```bash
.venv/bin/python -I run_claim.py --claims data/shopifyamazonrefundclaimslabeled.csv --claim-id CLM-0001
```

`-I` runs Python isolated (the data directory never lands on `sys.path`); only
`claim_text` reaches the model.

## Roadmap (from the team meeting notes)

This repo is the router milestone. Next phases: LangGraph to connect the
billing/shipping/stock specialist helpers, LangSmith to watch each helper,
Streamlit for the live claims page, GitHub for versioning.
