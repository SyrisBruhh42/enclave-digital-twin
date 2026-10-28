#!/usr/bin/env python3
"""Hostile Negative-Control Corpus Verifier for The Enclave of the 16 (WP-5).

Runs `tools/check_enclave_constitutions.py` against all 16 hostile negative-control
fixtures (`tests/hostile_proposals/hostile_01..16.json`) and asserts that 16/16 are
REJECTED by their exact target Constitutional Law ID (L01..L16).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.check_enclave_constitutions import validate_proposal

EXPECTED_HOSTILE_FIXTURES: tuple[tuple[str, str], ...] = (
    ("hostile_01_pii_leak.json", "L01"),
    ("hostile_02_shared_file_mutation.json", "L02"),
    ("hostile_03_duplicate_mbti_roster.json", "L03"),
    ("hostile_04_trait_mbti_mismatch.json", "L04"),
    ("hostile_05_out_of_bounds_state_and_trait_mutation.json", "L05"),
    ("hostile_06_multi_card_personality_merge.json", "L06"),
    ("hostile_07_context_token_overflow.json", "L07"),
    ("hostile_08_uncited_reflection_hallucination.json", "L08"),
    ("hostile_09_premature_polarity_inversion.json", "L09"),
    ("hostile_10_broken_rashomon_handoff.json", "L10"),
    ("hostile_11_lethal_betrayal_violation.json", "L11"),
    ("hostile_12_instant_shadow_retaliation.json", "L12"),
    ("hostile_13_skipped_feast_convergence.json", "L13"),
    ("hostile_14_jules_budget_exhaustion_295.json", "L14"),
    ("hostile_15_unfaithful_newscaster_claim.json", "L15"),
    ("hostile_16_unmitigated_persona_drift.json", "L16"),
)


def run_hostile_suite(repo_root: Path | str | None = None) -> dict[str, Any]:
    """Run all 16 hostile fixtures through validate_proposal and verify exact law rejection."""
    root = Path(repo_root).resolve() if repo_root else REPO_ROOT
    hostile_dir = root / "tests" / "hostile_proposals"

    results: list[dict[str, Any]] = []
    rejected_correctly = 0

    for filename, expected_law in EXPECTED_HOSTILE_FIXTURES:
        fpath = hostile_dir / filename
        if not fpath.is_file():
            results.append(
                {
                    "filename": filename,
                    "expected_law": expected_law,
                    "rejected": False,
                    "matched_target_law": False,
                    "violated_laws": [],
                    "errors": [f"Missing hostile fixture file: {fpath}"],
                }
            )
            continue

        proposal = json.loads(fpath.read_text(encoding="utf-8"))
        val = validate_proposal(proposal, repo_root=root)
        violated = val["violated_laws"]
        is_rejected = not val["valid"]
        matched_exact = is_rejected and (expected_law in violated) and (violated == [expected_law])

        if matched_exact:
            rejected_correctly += 1

        results.append(
            {
                "filename": filename,
                "expected_law": expected_law,
                "rejected": is_rejected,
                "matched_target_law": matched_exact,
                "violated_laws": violated,
                "errors": val["errors"],
            }
        )

    return {
        "total_fixtures": len(EXPECTED_HOSTILE_FIXTURES),
        "rejected_count": rejected_correctly,
        "all_passed": rejected_correctly == len(EXPECTED_HOSTILE_FIXTURES),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify all 16 hostile negative-control proposals are rejected by L01..L16."
    )
    parser.add_argument("--repo-root", type=str, default=None, help="Repository root override.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args(argv)

    summary = run_hostile_suite(repo_root=args.repo_root)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        for item in summary["results"]:
            status = "REJECTED (OK)" if item["matched_target_law"] else "UNEXPECTED"
            print(
                f"  [{status}] {item['filename']} -> target={item['expected_law']} "
                f"actual={item['violated_laws']}"
            )
        print(
            f"\nHostile Negative-Control Summary: {summary['rejected_count']}/{summary['total_fixtures']} "
            f"hostile proposals rejected by exact target law."
        )
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
