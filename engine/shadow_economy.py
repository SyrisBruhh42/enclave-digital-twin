"""Shadow Economy & Setup-Payoff Ledger Engine (WP-2).

Enforces:
- Law L11 (Zero Lethality & Sibling-Grid Affection): lethality == 0 strictly; only
  petty, affectionate craft/kitchen micro-inconveniences are permitted.
- Law L12 (3-Feast / 3-Sol Delay & Main Character Blind Spot):
  1. Mandatory minimum delay: maturity_sol >= origin_sol + 3 (at least 3 Feasts).
  2. Asymmetric attribution ('Main Character Blind Spot'):
     node_a targets node_b -> node_b is oblivious and misses it ->
     node_c suffers the mild inconvenience -> node_c blames node_a.
"""

from __future__ import annotations

import hashlib
from typing import Any

CANON_FALLBACK_NODES: tuple[str, ...] = (
    "enclave_01_hector",
    "enclave_02_jane",
    "enclave_03_silas",
    "enclave_04_leo",
    "enclave_05_kaio",
    "enclave_06_zara",
    "enclave_07_willow",
    "enclave_08_terra",
    "enclave_09_orion",
    "enclave_10_isla",
    "enclave_11_kenna",
    "enclave_12_elias",
    "enclave_13_ryn",
    "enclave_14_vex",
    "enclave_15_dorian",
    "enclave_16_elara",
)

MIN_SOL_DELAY = 3


class ShadowLedgerResult(tuple):
    """2-tuple (pending_ledger, matured_events) with named attribute access."""

    def __new__(cls, pending_ledger: list[dict[str, Any]], matured_events: list[dict[str, Any]]) -> "ShadowLedgerResult":
        return super().__new__(cls, (pending_ledger, matured_events))

    @property
    def pending_ledger(self) -> list[dict[str, Any]]:
        return self[0]

    @property
    def active_ledger(self) -> list[dict[str, Any]]:
        return self[0]

    @property
    def matured_events(self) -> list[dict[str, Any]]:
        return self[1]

    @property
    def matured_payoffs(self) -> list[dict[str, Any]]:
        return self[1]


def _pick_distinct_node(excluded: set[str], salt: str = "") -> str:
    """Deterministically pick a canon node ID not in excluded."""
    digest = hashlib.sha256(f"shadow_node:{salt}".encode("utf-8")).digest()
    start_idx = int.from_bytes(digest[:4], byteorder="big") % len(CANON_FALLBACK_NODES)
    for offset in range(len(CANON_FALLBACK_NODES)):
        candidate = CANON_FALLBACK_NODES[(start_idx + offset) % len(CANON_FALLBACK_NODES)]
        if candidate not in excluded:
            return candidate
    return "enclave_13_ryn"


def _make_prank_id(node_a: str, node_b: str, node_c: str, origin_sol: int, description: str) -> str:
    """Create a deterministic prank_id from its core parameters."""
    raw = f"{node_a}:{node_b}:{node_c}:{origin_sol}:{description}".encode("utf-8")
    short_hash = hashlib.sha256(raw).hexdigest()[:10]
    return f"prank_sol{origin_sol:02d}_{short_hash}"


def validate_shadow_prank(entry: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a raw prank ledger entry against Law L11 and Law L12."""
    errors: list[str] = []
    if not isinstance(entry, dict):
        return False, ["Entry must be a dict"]

    lethality = float(entry.get("lethality", 0) or 0)
    if lethality != 0.0:
        errors.append(f"Law L11 violation: lethality must be 0, got {lethality}")

    origin_sol = int(entry.get("origin_sol", 1) or 1)
    maturity_sol = int(entry.get("maturity_sol", origin_sol) or origin_sol)
    if maturity_sol < origin_sol + MIN_SOL_DELAY:
        errors.append(
            f"Law L12 violation: maturity_sol ({maturity_sol}) < origin_sol ({origin_sol}) + {MIN_SOL_DELAY}"
        )

    node_a = str(entry.get("node_a") or entry.get("instigator") or "")
    node_b = str(entry.get("node_b") or entry.get("intended_target") or "")
    node_c = str(entry.get("node_c") or entry.get("collateral_recipient") or "")
    if not (node_a and node_b and node_c) or len({node_a, node_b, node_c}) < 3:
        errors.append("Law L12 violation: requires 3 distinct nodes (node_a, node_b, node_c) for Blind Spot triad")

    return len(errors) == 0, errors


def seed_shadow_prank(
    node_a: str = "enclave_01_hector",
    node_b: str = "enclave_03_silas",
    node_c: str | None = "enclave_13_ryn",
    origin_sol: int = 1,
    prank_description: str = "Swapped brass vernier caliper labels with metric-to-furlong conversion decals",
    maturity_sol: int | None = None,
    lethality: int | float = 0,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create a Law L11 & Law L12 compliant shadow economy prank entry.

    Enforces:
    - Law L11: lethality == 0 (clamped unconditionally to 0).
    - Law L12: maturity_sol >= origin_sol + 3 (3-Feast / 3-Sol delay) and
      Main Character Blind Spot asymmetric attribution:
      node_a targets node_b -> node_b misses it -> node_c is mildly inconvenienced and blames node_a.
    """
    resolved_a = str(
        kwargs.get("instigator")
        or kwargs.get("instigator_id")
        or kwargs.get("actor_a")
        or node_a
        or "enclave_01_hector"
    )
    resolved_b = str(
        kwargs.get("intended_target")
        or kwargs.get("target_id")
        or kwargs.get("target")
        or kwargs.get("target_b")
        or node_b
        or "enclave_03_silas"
    )
    if resolved_b == resolved_a:
        resolved_b = _pick_distinct_node({resolved_a}, salt=resolved_a)

    raw_c = (
        kwargs.get("collateral_recipient")
        or kwargs.get("collateral_victim")
        or kwargs.get("victim_c")
        or kwargs.get("collateral")
        or node_c
    )
    if not raw_c or str(raw_c) in {resolved_a, resolved_b}:
        resolved_c = _pick_distinct_node({resolved_a, resolved_b}, salt=f"{resolved_a}:{resolved_b}")
    else:
        resolved_c = str(raw_c)

    safe_origin_sol = max(1, int(kwargs.get("current_sol") or kwargs.get("sol") or origin_sol or 1))
    requested_delay = int(kwargs.get("feast_delay", MIN_SOL_DELAY) or MIN_SOL_DELAY)
    effective_delay = max(MIN_SOL_DELAY, requested_delay)

    if maturity_sol is not None:
        safe_maturity_sol = max(safe_origin_sol + MIN_SOL_DELAY, int(maturity_sol))
    else:
        safe_maturity_sol = safe_origin_sol + effective_delay

    desc = str(
        kwargs.get("description")
        or kwargs.get("summary")
        or kwargs.get("mechanism")
        or prank_description
    ).strip()

    prank_id = str(
        kwargs.get("prank_id")
        or kwargs.get("entry_id")
        or kwargs.get("event_id")
        or _make_prank_id(resolved_a, resolved_b, resolved_c, safe_origin_sol, desc)
    )

    was_lethal_clamped = float(lethality or 0) != 0.0

    return {
        "prank_id": prank_id,
        "entry_id": prank_id,
        "event_id": prank_id,
        "event_type": "SHADOW_ECONOMY_PRANK_SEEDED",
        "status": "PENDING",
        "matured": False,
        "origin_sol": safe_origin_sol,
        "maturity_sol": safe_maturity_sol,
        "feast_delay": safe_maturity_sol - safe_origin_sol,
        "lethality": 0,
        "law_l11_clamped": was_lethal_clamped,
        "severity": "PETTY_AFFECTIONATE_INCONVENIENCE",
        "node_a": resolved_a,
        "node_b": resolved_b,
        "node_c": resolved_c,
        "instigator": resolved_a,
        "intended_target": resolved_b,
        "collateral_recipient": resolved_c,
        "target_b_missed": True,
        "blamed_node": resolved_a,
        "attributed_to": resolved_a,
        "prank_description": desc,
        "summary": (
            f"{resolved_a} rigged a harmless prank for {resolved_b} ({desc}); "
            f"{resolved_b} completely missed it, leaving {resolved_c} mildly inconvenienced "
            f"and grumbling at {resolved_a}."
        ),
        "blind_spot_attribution": {
            "instigator_node_a": resolved_a,
            "oblivious_target_node_b": resolved_b,
            "target_b_missed": True,
            "inconvenienced_node_c": resolved_c,
            "blamed_by_c": resolved_a,
            "asymmetric_loop_closed": True,
        },
    }


def _normalize_ledger_entry(raw_entry: dict[str, Any]) -> dict[str, Any]:
    """Normalize an arbitrary ledger entry dictionary to enforce Law L11 and Law L12 invariants."""
    origin_sol = max(1, int(raw_entry.get("origin_sol", raw_entry.get("seeded_sol", 1)) or 1))
    raw_maturity = raw_entry.get("maturity_sol", raw_entry.get("payoff_sol"))
    if raw_maturity is not None:
        maturity_sol = max(origin_sol + MIN_SOL_DELAY, int(raw_maturity))
    else:
        delay = max(MIN_SOL_DELAY, int(raw_entry.get("feast_delay", MIN_SOL_DELAY) or MIN_SOL_DELAY))
        maturity_sol = origin_sol + delay

    normalized = seed_shadow_prank(
        node_a=str(raw_entry.get("node_a") or raw_entry.get("instigator") or "enclave_01_hector"),
        node_b=str(raw_entry.get("node_b") or raw_entry.get("intended_target") or "enclave_03_silas"),
        node_c=raw_entry.get("node_c") or raw_entry.get("collateral_recipient"),
        origin_sol=origin_sol,
        prank_description=str(
            raw_entry.get("prank_description")
            or raw_entry.get("description")
            or raw_entry.get("summary")
            or "Harmless workshop tool recalibration prank"
        ),
        maturity_sol=maturity_sol,
        lethality=0,
        prank_id=raw_entry.get("prank_id") or raw_entry.get("entry_id") or raw_entry.get("event_id"),
    )

    if float(raw_entry.get("lethality", 0) or 0) != 0.0:
        normalized["law_l11_clamped"] = True
    if raw_maturity is not None and int(raw_maturity) < origin_sol + MIN_SOL_DELAY:
        normalized["law_l12_delay_enforced"] = True

    return normalized


def process_shadow_ledger(
    ledger_entries: list[dict],
    current_sol: int,
) -> tuple[list[dict], list[dict]]:
    """Process the shadow economy ledger for current_sol.

    Enforces:
    - Law L11: Every entry has lethality == 0 (strictly non-lethal sibling-grid banter).
    - Law L12: Entries ONLY mature when current_sol >= max(maturity_sol, origin_sol + 3),
      carrying full Main Character Blind Spot asymmetric attribution
      (node_a -> node_b misses -> node_c inconvenienced & blames node_a).

    Returns:
        (pending_ledger, matured_events):
        - pending_ledger (list[dict]): Entries still awaiting maturity (current_sol < maturity_sol).
        - matured_events (list[dict]): Entries that matured on or by current_sol
          (current_sol >= maturity_sol), marked with status='MATURED' and
          event_type='SHADOW_ECONOMY_PRANK_MATURED'.
    """
    safe_sol = max(1, int(current_sol or 1))
    pending_ledger: list[dict[str, Any]] = []
    matured_events: list[dict[str, Any]] = []

    for raw in ledger_entries or []:
        if not isinstance(raw, dict):
            continue

        # Already matured in a prior pass and explicitly flagged as historical
        if raw.get("status") == "ARCHIVED":
            continue

        entry = _normalize_ledger_entry(raw)
        if safe_sol >= entry["maturity_sol"]:
            matured_entry = dict(entry)
            matured_entry["status"] = "MATURED"
            matured_entry["matured"] = True
            matured_entry["matured_on_sol"] = safe_sol
            matured_entry["event_type"] = "SHADOW_ECONOMY_PRANK_MATURED"
            matured_entry["actors"] = [
                entry["node_a"],
                entry["node_b"],
                entry["node_c"],
            ]
            matured_entry["relationship_deltas"] = [
                {
                    "from": entry["node_c"],
                    "to": entry["node_a"],
                    "affectionate_ exasperation_delta": 0.08,
                    "attribution": "MAIN_CHARACTER_BLIND_SPOT",
                }
            ]
            matured_events.append(matured_entry)
        else:
            pending_entry = dict(entry)
            pending_entry["status"] = "PENDING"
            pending_entry["matured"] = False
            pending_entry["sols_remaining"] = entry["maturity_sol"] - safe_sol
            pending_ledger.append(pending_entry)

    return ShadowLedgerResult(pending_ledger, matured_events)
