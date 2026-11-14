"""Run the router on one labeled claim and print the validated decision.

The router only ever sees `claim_text` — no labels, no amounts, no investigator
notes. The label is compared only after the decision is printed.

Usage (from the project root):
    .venv/bin/python -I run_claim.py --claims data/claims.csv --claim-id CLM-0001
"""
import argparse
import csv
import json
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
# Explicit: only our own trusted project modules go on sys.path (run with python -I).
sys.path.insert(0, str(PROJECT_DIR))

from config import load_env, require_env  # noqa: E402
from router import route_claim  # noqa: E402


def label_match(routed_specialists: set, label: str) -> bool:
    """True when the routed set equals the investigator's pipe-separated label set."""
    return routed_specialists == set(label.split("|"))


def read_claims(csv_path: Path) -> list:
    with csv_path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser(description="Route one A-to-z claim via OpenRouter.")
    parser.add_argument(
        "--claims",
        type=Path,
        default=PROJECT_DIR / "data" / "shopifyamazonrefundclaimslabeled.csv",
    )
    parser.add_argument("--claim-id", default="CLM-0001")
    args = parser.parse_args()

    load_env()
    api_key = require_env("OPENROUTER_API_KEY")
    model = require_env("OPENROUTER_MODEL")

    claims = read_claims(args.claims)
    matches = [row for row in claims if row["claim_id"] == args.claim_id]
    if not matches:
        print(f"claim id {args.claim_id!r} not found in {args.claims}", file=sys.stderr)
        return 2
    claim = matches[0]

    decision = route_claim(claim["claim_text"], api_key=api_key, model=model)

    routed = {s.value for s in decision.specialists}
    result = {
        "claim_id": claim["claim_id"],
        "model": model,
        "decision": decision.model_dump(mode="json"),
        "label_specialists": claim["label_specialists"],
        "match": label_match(routed, claim["label_specialists"]),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
