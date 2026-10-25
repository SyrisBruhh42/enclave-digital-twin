#!/usr/bin/env python3
"""16-Law Constitutional Checker for The Enclave of the 16 (WP-5).

Validates both the repository state and any proposed event, scene segment,
context manifest, reflection, shadow prank, drift audit, budget state, or
Evening Dispatch bundle against all 16 Constitutional Laws (L01 through L16).

CLI Usage:
    python3 tools/check_enclave_constitutions.py --strict
    python3 tools/check_enclave_constitutions.py --proposal-file path/to/proposal.json
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Law L01: Forbidden real-world personal names, workplaces, and private identifiers
PII_FORBIDDEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Joseph", re.compile(r"\bJoseph\b", re.IGNORECASE)),
    ("Lewis", re.compile(r"\bLewis\b", re.IGNORECASE)),
    ("Larry", re.compile(r"\bLarry\b", re.IGNORECASE)),
    ("Caterpillar", re.compile(r"\bCaterpillar\b", re.IGNORECASE)),
    ("Facility 88", re.compile(r"\bFacility[\s_-]*88\b", re.IGNORECASE)),
    ("3500 Mainline", re.compile(r"\b3500[\s_-]*Mainline\b", re.IGNORECASE)),
    ("Kaz", re.compile(r"\bKaz\b", re.IGNORECASE)),
    ("Philosopher-Mechanic", re.compile(r"\bPhilosopher[\s_-]*Mechanic\b", re.IGNORECASE)),
)

# Law L02: Allowed worker proposal creation prefixes and protected paths
ALLOWED_WORKER_PREFIXES: tuple[str, ...] = (
    "events/",
    "story/segments/",
    "story/feasts/",
    "digests/",
    "qa/",
)

PROTECTED_SHARED_PREFIXES: tuple[str, ...] = (
    "canon/",
    "snapshots/",
    "relationships/",
    "ops/",
    "engine/",
    "tools/",
)

# Law L03: 16 Canonical MBTI types and 16 character IDs
CANONICAL_16_MBTI: frozenset[str] = frozenset(
    {
        "ISTJ",
        "ISFJ",
        "INFJ",
        "INTJ",
        "ISTP",
        "ISFP",
        "INFP",
        "INTP",
        "ESTP",
        "ESFP",
        "ENFP",
        "ENTP",
        "ESTJ",
        "ESFJ",
        "ENFJ",
        "ENTJ",
    }
)

CANONICAL_16_CHARACTER_IDS: tuple[str, ...] = (
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

# Law L11: Hostile / non-PvE keywords
HOSTILE_PVE_KEYWORDS: tuple[str, ...] = (
    "murder",
    "assassin",
    "betrayal",
    "backstab",
    "poison_crew",
    "homicide",
    "lethal_sabotage",
)

DAY_PHASES_ORDER: tuple[str, ...] = (
    "DAWN_SHIFT",
    "MIDDAY_EXPEDITION",
    "DUSK_CRAFT",
    "THE_FEAST",
)

BIG_FIVE_DIMS: tuple[str, ...] = (
    "openness",
    "conscientiousness",
    "extraversion",
    "agreeableness",
    "neuroticism",
)


def _resolve_root(repo_root: Path | str | None = None) -> Path:
    if repo_root is None:
        return REPO_ROOT
    return Path(repo_root).resolve()


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _load_canonical_cores(root: Path) -> dict[str, dict[str, Any]]:
    cores: dict[str, dict[str, Any]] = {}
    char_dir = root / "canon" / "characters"
    if not char_dir.is_dir():
        return cores
    for p in sorted(char_dir.glob("*.core.json")):
        data = _load_json(p)
        ident = data.get("agent_identity") or {}
        cid = str(ident.get("character_id") or data.get("character_id") or p.stem.replace(".core", ""))
        cores[cid] = data
    return cores


def _load_known_events(root: Path, proposal: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    events_by_id: dict[str, dict[str, Any]] = {}
    events_dir = root / "events"
    if events_dir.is_dir():
        for p in sorted(events_dir.glob("*.json")):
            try:
                ev = _load_json(p)
                if isinstance(ev, dict) and ev.get("event_id"):
                    events_by_id[str(ev["event_id"])] = ev
            except Exception:
                continue

    if isinstance(proposal, dict):
        for key in ("known_events", "events", "existing_events"):
            ev_list = proposal.get(key)
            if isinstance(ev_list, list):
                for ev in ev_list:
                    if isinstance(ev, dict) and ev.get("event_id"):
                        events_by_id[str(ev["event_id"])] = ev
        if isinstance(proposal.get("valid_events_by_id"), dict):
            for eid, ev in proposal["valid_events_by_id"].items():
                if isinstance(ev, dict):
                    events_by_id[str(eid)] = ev
        if isinstance(proposal.get("valid_event_ids"), list):
            for eid in proposal["valid_event_ids"]:
                if isinstance(eid, str) and eid not in events_by_id:
                    events_by_id[eid] = {"event_id": eid}

    return events_by_id


# ============================================================================
# LAW L01: Zero PII & Sanitization Gate
# ============================================================================
def check_zero_pii(
    proposal: dict[str, Any] | None = None,
    repo_root: Path | str | None = None,
) -> tuple[bool, list[str]]:
    """Law L01: Regex scan blocking real-world personal names and workplaces."""
    errors: list[str] = []
    root = _resolve_root(repo_root)

    if proposal is not None:
        serialized = json.dumps(proposal, ensure_ascii=False)
        for label, pattern in PII_FORBIDDEN_PATTERNS:
            if pattern.search(serialized):
                errors.append(f"Law L01 violation: forbidden real-world PII token '{label}' detected in proposal.")
        return len(errors) == 0, errors

    scan_dirs = ("canon", "relationships", "events", "story", "digests", "qa", "context")
    for dname in scan_dirs:
        target_dir = root / dname
        if not target_dir.is_dir():
            continue
        for file_path in sorted(target_dir.rglob("*.json")):
            try:
                content = file_path.read_text(encoding="utf-8")
            except Exception as exc:
                errors.append(f"Law L01 error reading {file_path}: {exc}")
                continue
            for label, pattern in PII_FORBIDDEN_PATTERNS:
                if pattern.search(content):
                    rel = file_path.relative_to(root)
                    errors.append(f"Law L01 violation: forbidden PII token '{label}' found in {rel}.")

    return len(errors) == 0, errors


# ============================================================================
# LAW L02: Single-File Append-Only Event Sourcing
# ============================================================================
def check_append_only_events(
    proposal: dict[str, Any] | None = None,
    repo_root: Path | str | None = None,
) -> tuple[bool, list[str]]:
    """Law L02: Worker session proposal may only create 1 new file in allowed prefix; zero M/D to canon/snapshots/ledgers."""
    errors: list[str] = []
    root = _resolve_root(repo_root)

    if proposal is not None:
        file_ops: list[tuple[str, str]] = []

        raw_ops = (
            proposal.get("file_operations")
            or proposal.get("changed_files")
            or proposal.get("diff_entries")
            or proposal.get("git_status")
        )
        if isinstance(raw_ops, list):
            for item in raw_ops:
                if isinstance(item, dict):
                    status = str(item.get("status") or item.get("op") or item.get("action") or "A").strip().upper()
                    path = str(item.get("path") or item.get("file") or item.get("target_path") or "").strip()
                    file_ops.append((status, path))
                elif isinstance(item, str):
                    parts = item.strip().split(maxsplit=1)
                    if len(parts) == 2 and parts[0].upper() in ("A", "M", "D", "R", "ADD", "MODIFY", "DELETE"):
                        file_ops.append((parts[0][0].upper(), parts[1].strip()))
                    else:
                        file_ops.append(("A", item.strip()))

        target_path = proposal.get("target_path") or proposal.get("output_path") or proposal.get("file_path")
        if isinstance(target_path, str) and target_path.strip():
            raw_top_op = str(proposal.get("operation") or "").strip().upper()
            raw_top_status = str(proposal.get("status") or "").strip().upper()
            if raw_top_op in ("A", "M", "D", "R", "ADD", "MODIFY", "DELETE"):
                op_code = raw_top_op[0]
            elif raw_top_status in ("A", "M", "D", "R", "ADD", "MODIFY", "DELETE"):
                op_code = raw_top_status[0]
            else:
                op_code = "A"
            if (op_code, target_path.strip()) not in file_ops:
                file_ops.append((op_code, target_path.strip()))

        if isinstance(proposal.get("mutated_shared_files"), list) and proposal["mutated_shared_files"]:
            for mp in proposal["mutated_shared_files"]:
                file_ops.append(("M", str(mp)))

        if file_ops:
            if len(file_ops) > 1:
                errors.append(
                    f"Law L02 violation: worker session proposal attempted {len(file_ops)} file operations "
                    f"(strictly 1 new append-only file allowed)."
                )
            for status, path in file_ops:
                norm_path = path.lstrip("./")
                if status != "A":
                    errors.append(
                        f"Law L02 violation: forbidden modification/deletion status '{status}' on '{norm_path}' "
                        f"(append-only creation 'A' required)."
                    )
                if any(norm_path.startswith(pref) for pref in PROTECTED_SHARED_PREFIXES):
                    errors.append(
                        f"Law L02 violation: worker session attempted to touch protected shared path '{norm_path}'."
                    )
                if not any(norm_path.startswith(pref) for pref in ALLOWED_WORKER_PREFIXES):
                    errors.append(
                        f"Law L02 violation: target path '{norm_path}' is outside allowed prefixes {ALLOWED_WORKER_PREFIXES}."
                    )
                existing_full = root / norm_path
                if status == "A" and existing_full.exists() and proposal.get("disallow_overwrite", True):
                    errors.append(
                        f"Law L02 violation: target file '{norm_path}' already exists; overwriting append-only records is prohibited."
                    )

        return len(errors) == 0, errors

    # Repository check: verify canon/ has no M/D modifications in git status if inside a git worktree
    try:
        proc = subprocess.run(
            [
                "git",
                "status",
                "--porcelain",
                "--",
                "canon/characters/",
                "canon/projects/",
                "canon/lore_cards/",
                "canon/schemas/world_state_v2.json",
                "relationships/initial_matrix_120.json",
            ],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            for line in proc.stdout.strip().splitlines():
                code = line[:2].strip()
                if code in ("M", "D", "MM", "MD"):
                    errors.append(f"Law L02 violation: canonical file modified or deleted in working tree: {line.strip()}")
    except Exception:
        pass

    return len(errors) == 0, errors


# ============================================================================
# LAW L03: 16-Node Cast & 16-MBTI Bijection
# ============================================================================
def check_16_cast_bijection(
    proposal: dict[str, Any] | None = None,
    repo_root: Path | str | None = None,
) -> tuple[bool, list[str]]:
    """Law L03: 16 characters, 16 unique MBTI types, 4 squads of 4 (2 Anchors + 2 Prodigies), 8 Grand Projects."""
    errors: list[str] = []
    root = _resolve_root(repo_root)

    if proposal is not None and any(
        k in proposal for k in ("roster_override", "cast_16_bijection_roster", "characters_override", "projects_override")
    ):
        roster = proposal.get("roster_override") or proposal.get("cast_16_bijection_roster") or {}
        squads = roster.get("squads") if isinstance(roster, dict) else None
        if isinstance(squads, dict):
            all_chars: list[dict[str, Any]] = []
            if len(squads) != 4:
                errors.append(f"Law L03 violation: expected 4 squads, got {len(squads)}.")
            for sq_name, members in squads.items():
                if not isinstance(members, list) or len(members) != 4:
                    errors.append(
                        f"Law L03 violation: squad '{sq_name}' must have 4 members, got {len(members) if isinstance(members, list) else 0}."
                    )
                    continue
                anchors = [m for m in members if str(m.get("role") or m.get("dialectic_role")) == "Anchor"]
                prodigies = [m for m in members if str(m.get("role") or m.get("dialectic_role")) == "Prodigy"]
                if len(anchors) != 2 or len(prodigies) != 2:
                    errors.append(
                        f"Law L03 violation: squad '{sq_name}' must have 2 Anchors and 2 Prodigies "
                        f"(got {len(anchors)} Anchors, {len(prodigies)} Prodigies)."
                    )
                all_chars.extend(members)
            if len(all_chars) != 16:
                errors.append(f"Law L03 violation: expected 16 characters, got {len(all_chars)}.")
            mbtis = [str(c.get("mbti") or "").strip().upper() for c in all_chars]
            if set(mbtis) != CANONICAL_16_MBTI or len(mbtis) != 16:
                dups = sorted({m for m in mbtis if mbtis.count(m) > 1})
                missing = sorted(CANONICAL_16_MBTI - set(mbtis))
                errors.append(
                    f"Law L03 violation: broken 16-MBTI bijection (duplicates={dups}, missing={missing})."
                )
        projects_list = proposal.get("projects_override")
        if isinstance(projects_list, list) and len(projects_list) != 8:
            errors.append(f"Law L03 violation: expected 8 Grand Projects, got {len(projects_list)}.")
        return len(errors) == 0, errors

    # Repository check
    ws_path = root / "canon" / "schemas" / "world_state_v2.json"
    gp_path = root / "canon" / "projects" / "grand_projects.json"
    cores = _load_canonical_cores(root)

    if len(cores) != 16:
        errors.append(f"Law L03 violation: expected 16 character core files in canon/characters/, found {len(cores)}.")

    core_mbtis: list[str] = []
    for cid, card in cores.items():
        lens = (card.get("tier_4_self_concept_and_narrative_arc") or {}).get("cognitive_lens") or {}
        mbti = str(lens.get("mbti_type") or "").strip().upper()
        core_mbtis.append(mbti)

    if set(core_mbtis) != CANONICAL_16_MBTI or len(core_mbtis) != 16:
        dups = sorted({m for m in core_mbtis if core_mbtis.count(m) > 1})
        missing = sorted(CANONICAL_16_MBTI - set(core_mbtis))
        errors.append(f"Law L03 violation: character cores fail 16-MBTI bijection (dups={dups}, missing={missing}).")

    if ws_path.is_file():
        ws = _load_json(ws_path)
        squads = (ws.get("cast_16_bijection_roster") or {}).get("squads") or {}
        if len(squads) != 4:
            errors.append(f"Law L03 violation: world_state_v2.json has {len(squads)} squads (expected 4).")
        ws_chars: list[dict[str, Any]] = []
        for sq_name, members in squads.items():
            if not isinstance(members, list) or len(members) != 4:
                errors.append(f"Law L03 violation: squad '{sq_name}' does not have 4 members.")
                continue
            anchors = [m for m in members if m.get("role") == "Anchor"]
            prodigies = [m for m in members if m.get("role") == "Prodigy"]
            if len(anchors) != 2 or len(prodigies) != 2:
                errors.append(f"Law L03 violation: squad '{sq_name}' must contain 2 Anchors and 2 Prodigies.")
            ws_chars.extend(members)
        ws_mbtis = [str(c.get("mbti") or "").upper() for c in ws_chars]
        if set(ws_mbtis) != CANONICAL_16_MBTI or len(ws_mbtis) != 16:
            errors.append("Law L03 violation: world_state_v2.json roster fails 16-MBTI bijection.")
    else:
        errors.append("Law L03 violation: missing canon/schemas/world_state_v2.json.")

    if gp_path.is_file():
        gp = _load_json(gp_path)
        projects = gp.get("projects") or []
        if len(projects) != 8:
            errors.append(f"Law L03 violation: expected 8 Grand Projects in grand_projects.json, found {len(projects)}.")
    else:
        errors.append("Law L03 violation: missing canon/projects/grand_projects.json.")

    return len(errors) == 0, errors


# ============================================================================
# LAW L04: Trait-to-Type Psychometric Alignment
# ============================================================================
def _verify_mbti_big5_alignment(char_label: str, mbti: str, o: float, c: float, e: float, a: float) -> list[str]:
    errs: list[str] = []
    if len(mbti) != 4 or mbti not in CANONICAL_16_MBTI:
        return [f"Law L04 violation: {char_label} has invalid MBTI '{mbti}'."]

    # E/I -> Extraversion
    if mbti[0] == "E" and not (e > 0.50):
        errs.append(f"Law L04 violation: {char_label} ({mbti}) requires E > 0.50, got E={e:.2f}.")
    elif mbti[0] == "I" and not (e < 0.50):
        errs.append(f"Law L04 violation: {char_label} ({mbti}) requires E < 0.50 for I, got E={e:.2f}.")

    # N/S -> Openness
    if mbti[1] == "N" and not (o > 0.50):
        errs.append(f"Law L04 violation: {char_label} ({mbti}) requires O > 0.50 for N, got O={o:.2f}.")
    elif mbti[1] == "S" and not (o < 0.50):
        errs.append(f"Law L04 violation: {char_label} ({mbti}) requires O < 0.50 for S, got O={o:.2f}.")

    # F/T -> Agreeableness
    if mbti[2] == "F" and not (a > 0.50):
        errs.append(f"Law L04 violation: {char_label} ({mbti}) requires A > 0.50 for F, got A={a:.2f}.")
    elif mbti[2] == "T" and not (a < 0.50):
        errs.append(f"Law L04 violation: {char_label} ({mbti}) requires A < 0.50 for T, got A={a:.2f}.")

    # J/P -> Conscientiousness
    if mbti[3] == "J" and not (c > 0.50):
        errs.append(f"Law L04 violation: {char_label} ({mbti}) requires C > 0.50 for J, got C={c:.2f}.")
    elif mbti[3] == "P" and not (c < 0.50):
        errs.append(f"Law L04 violation: {char_label} ({mbti}) requires C < 0.50 for P, got C={c:.2f}.")

    return errs


def check_trait_type_alignment(
    proposal: dict[str, Any] | None = None,
    repo_root: Path | str | None = None,
) -> tuple[bool, list[str]]:
    """Law L04: Big Five means in canon/characters/*.core.json match world_state_v2.json and align with MBTI axes."""
    errors: list[str] = []
    root = _resolve_root(repo_root)

    if proposal is not None and any(k in proposal for k in ("character_card", "trait_alignment_test", "character_override")):
        card = proposal.get("character_card") or proposal.get("trait_alignment_test") or proposal.get("character_override") or {}
        ident = card.get("agent_identity") or {}
        cid = str(ident.get("character_id") or card.get("id") or card.get("character_id") or "proposal_char")
        lens = (card.get("tier_4_self_concept_and_narrative_arc") or {}).get("cognitive_lens") or {}
        mbti = str(lens.get("mbti_type") or card.get("mbti") or "").strip().upper()
        b5 = (card.get("tier_1_causal_trait_distributions") or {}).get("big_five_distributions") or {}
        if b5:
            o = float((b5.get("openness") or {}).get("mean", 0.5))
            c = float((b5.get("conscientiousness") or {}).get("mean", 0.5))
            e = float((b5.get("extraversion") or {}).get("mean", 0.5))
            a = float((b5.get("agreeableness") or {}).get("mean", 0.5))
        elif isinstance(card.get("ocean_mean"), list) and len(card["ocean_mean"]) >= 4:
            o, c, e, a = (float(card["ocean_mean"][0]), float(card["ocean_mean"][1]), float(card["ocean_mean"][2]), float(card["ocean_mean"][3]))
        else:
            o = c = e = a = 0.5
        errors.extend(_verify_mbti_big5_alignment(cid, mbti, o, c, e, a))
        return len(errors) == 0, errors

    ws_path = root / "canon" / "schemas" / "world_state_v2.json"
    cores = _load_canonical_cores(root)
    ws_by_id: dict[str, dict[str, Any]] = {}
    if ws_path.is_file():
        ws = _load_json(ws_path)
        for members in ((ws.get("cast_16_bijection_roster") or {}).get("squads") or {}).values():
            for m in members:
                if isinstance(m, dict) and m.get("id"):
                    ws_by_id[str(m["id"])] = m

    for cid, card in cores.items():
        b5 = (card.get("tier_1_causal_trait_distributions") or {}).get("big_five_distributions") or {}
        o = float((b5.get("openness") or {}).get("mean", 0.5))
        c = float((b5.get("conscientiousness") or {}).get("mean", 0.5))
        e = float((b5.get("extraversion") or {}).get("mean", 0.5))
        a = float((b5.get("agreeableness") or {}).get("mean", 0.5))
        n = float((b5.get("neuroticism") or {}).get("mean", 0.5))
        lens = (card.get("tier_4_self_concept_and_narrative_arc") or {}).get("cognitive_lens") or {}
        mbti = str(lens.get("mbti_type") or "").strip().upper()

        errors.extend(_verify_mbti_big5_alignment(cid, mbti, o, c, e, a))

        if cid in ws_by_id:
            ws_entry = ws_by_id[cid]
            ws_mbti = str(ws_entry.get("mbti") or "").strip().upper()
            if ws_mbti != mbti:
                errors.append(f"Law L04 violation: {cid} MBTI mismatch between core ({mbti}) and world_state ({ws_mbti}).")
            ocean = ws_entry.get("ocean_mean") or []
            if len(ocean) == 5:
                for axis_name, core_val, ws_val in zip(BIG_FIVE_DIMS, (o, c, e, a, n), ocean):
                    if abs(float(core_val) - float(ws_val)) > 1e-4:
                        errors.append(
                            f"Law L04 violation: {cid} {axis_name} mean mismatch between core ({core_val}) and world_state ({ws_val})."
                        )

    return len(errors) == 0, errors


# ============================================================================
# LAW L05: Whole-Trait State Bounds & Trait Mean Immutability
# ============================================================================
def check_state_bounds_and_trait_immutability(
    proposal: dict[str, Any] | None = None,
    repo_root: Path | str | None = None,
) -> tuple[bool, list[str]]:
    """Law L05: Momentary states in [0, 1] and baseline trait means mu_i never mutate across ticks."""
    errors: list[str] = []
    root = _resolve_root(repo_root)
    cores = _load_canonical_cores(root)

    def _inspect_state_obj(obj: dict[str, Any], label: str) -> None:
        if obj.get("tier_1_mutation") or obj.get("mutate_baseline_traits") or obj.get("trait_mean_override") or obj.get("mu_delta"):
            errors.append(f"Law L05 violation: {label} attempted to mutate immutable Tier-1 baseline trait means.")

        if isinstance(obj.get("mutated_tier_1_means"), dict) and obj["mutated_tier_1_means"]:
            errors.append(f"Law L05 violation: {label} contains mutated_tier_1_means={obj['mutated_tier_1_means']}.")

        # Check if a core comparison is embedded
        cid = str(obj.get("character_id") or "")
        if cid in cores and isinstance(obj.get("tier_1_causal_trait_distributions"), dict):
            canon_b5 = (cores[cid].get("tier_1_causal_trait_distributions") or {}).get("big_five_distributions") or {}
            prop_b5 = (obj["tier_1_causal_trait_distributions"].get("big_five_distributions")) or {}
            for dim in BIG_FIVE_DIMS:
                if dim in canon_b5 and dim in prop_b5:
                    c_mu = float((canon_b5[dim] or {}).get("mean", 0.5))
                    p_mu = float((prop_b5[dim] or {}).get("mean", c_mu))
                    if abs(c_mu - p_mu) > 1e-6:
                        errors.append(
                            f"Law L05 violation: {label} mutated Tier-1 {dim} mean for {cid} ({c_mu} -> {p_mu})."
                        )

        state_containers = [obj]
        for subkey in ("momentary_state", "current_state_vector", "trait_states", "state_vector", "state_deltas"):
            if isinstance(obj.get(subkey), dict):
                state_containers.append(obj[subkey])

        bounded_keys = (
            "openness",
            "conscientiousness",
            "extraversion",
            "agreeableness",
            "neuroticism",
            "hexaco_honesty_humility",
            "openness_state",
            "conscientiousness_state",
            "extraversion_state",
            "agreeableness_state",
            "neuroticism_state",
            "stress",
            "fatigue",
            "sleep_debt_norm",
        )
        for container in state_containers:
            if container is obj.get("state_deltas"):
                # Deltas can be negative, but absolute state values inside state_deltas (or out-of-range > 1 / < -1) are invalid
                for k, v in container.items():
                    if isinstance(v, (int, float)):
                        if k in ("stress", "fatigue", "openness_state", "conscientiousness_state", "extraversion_state", "agreeableness_state", "neuroticism_state"):
                            if float(v) < 0.0 or float(v) > 1.0:
                                errors.append(f"Law L05 violation: {label} state value '{k}'={v} out of bounds [0.0, 1.0].")
                        elif abs(float(v)) > 1.0:
                            errors.append(f"Law L05 violation: {label} state delta '{k}'={v} exceeds unit bounds [-1.0, 1.0].")
                continue

            for k in bounded_keys:
                if k in container and isinstance(container[k], (int, float)):
                    val = float(container[k])
                    if val < 0.0 or val > 1.0:
                        errors.append(f"Law L05 violation: {label} has '{k}'={val} outside [0.0, 1.0].")

    if proposal is not None:
        _inspect_state_obj(proposal, "proposal")
        if isinstance(proposal.get("character_states"), dict):
            for cid, st in proposal["character_states"].items():
                if isinstance(st, dict):
                    _inspect_state_obj(st, f"character_states[{cid}]")
        return len(errors) == 0, errors

    for cid, card in cores.items():
        _inspect_state_obj(card, f"core[{cid}]")

    snapshots_dir = root / "snapshots"
    if snapshots_dir.is_dir():
        for sp in sorted(snapshots_dir.glob("*.json")):
            try:
                snap = _load_json(sp)
                for cid, st in (snap.get("character_states") or {}).items():
                    if isinstance(st, dict):
                        _inspect_state_obj(st, f"{sp.name}:{cid}")
            except Exception as exc:
                errors.append(f"Law L05 error reading {sp.name}: {exc}")

    return len(errors) == 0, errors


# ============================================================================
# LAW L06: Swap-Mode Single-POV Isolation
# ============================================================================
def check_single_pov_swap_isolation(
    proposal: dict[str, Any] | None = None,
    repo_root: Path | str | None = None,
) -> tuple[bool, list[str]]:
    """Law L06: Context manifests load full_cards_loaded_count == 1 and zero full cards for non-POV interlocutors."""
    errors: list[str] = []
    root = _resolve_root(repo_root)

    def _inspect_manifest(manifest: dict[str, Any], label: str) -> None:
        inner = manifest.get("manifest") if isinstance(manifest.get("manifest"), dict) else manifest
        count = inner.get("full_cards_loaded_count", manifest.get("full_cards_loaded_count", 1))
        if int(count) != 1:
            errors.append(
                f"Law L06 violation: {label} has full_cards_loaded_count={count} (must be strictly 1)."
            )
        loaded_ids = inner.get("loaded_full_card_ids", manifest.get("loaded_full_card_ids"))
        active_pov = inner.get("active_pov_id") or manifest.get("active_pov_id")
        if isinstance(loaded_ids, list):
            if len(loaded_ids) != 1:
                errors.append(
                    f"Law L06 violation: {label} loaded_full_card_ids={loaded_ids} (must contain strictly 1 active POV card)."
                )
            elif active_pov and loaded_ids[0] != active_pov:
                errors.append(
                    f"Law L06 violation: {label} loaded card '{loaded_ids[0]}' != active_pov_id '{active_pov}'."
                )
        if int(inner.get("interlocutor_full_cards_loaded", 0) or 0) > 0:
            errors.append(f"Law L06 violation: {label} loaded full private cards for non-POV interlocutors.")
        if bool(inner.get("leaked_interlocutor_private_cards") or manifest.get("leaked_interlocutor_private_cards")):
            errors.append(f"Law L06 violation: {label} leaked private interlocutor core card data into prompt.")

    if proposal is not None:
        if any(
            k in proposal
            for k in (
                "manifest",
                "context_manifest",
                "full_cards_loaded_count",
                "loaded_full_card_ids",
                "interlocutor_full_cards_loaded",
                "leaked_interlocutor_private_cards",
            )
        ):
            target = proposal.get("context_manifest") if isinstance(proposal.get("context_manifest"), dict) else proposal
            _inspect_manifest(target, "proposal_manifest")
        return len(errors) == 0, errors

    manifests_dir = root / "context" / "manifests"
    if manifests_dir.is_dir():
        for mp in sorted(manifests_dir.glob("*.json")):
            try:
                _inspect_manifest(_load_json(mp), mp.name)
            except Exception as exc:
                errors.append(f"Law L06 error reading {mp.name}: {exc}")

    return len(errors) == 0, errors


# ============================================================================
# LAW L07: 10-Block Context Budget Ceiling (<= 3,500 Tokens)
# ============================================================================
def check_context_token_budget(
    proposal: dict[str, Any] | None = None,
    repo_root: Path | str | None = None,
) -> tuple[bool, list[str]]:
    """Law L07: Context manifest total_tokens <= max_tokens (3500) and preserves block order 1..10."""
    errors: list[str] = []
    root = _resolve_root(repo_root)

    def _inspect_budget(manifest: dict[str, Any], label: str) -> None:
        inner = manifest.get("manifest") if isinstance(manifest.get("manifest"), dict) else manifest
        total_tokens = int(inner.get("total_tokens", manifest.get("total_tokens", 0)) or 0)
        max_tokens = int(inner.get("max_tokens", manifest.get("max_tokens", 3500)) or 3500)
        hard_cap = min(3500, max_tokens)

        if total_tokens > hard_cap or total_tokens > 3500:
            errors.append(
                f"Law L07 violation: {label} total_tokens ({total_tokens}) exceeds token budget ceiling ({hard_cap})."
            )

        blocks = inner.get("blocks")
        if isinstance(blocks, list):
            indices = [int(b.get("block_index", 0)) for b in blocks if isinstance(b, dict)]
            if indices != [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
                errors.append(
                    f"Law L07 violation: {label} block order {indices} violates mandatory 1..10 sequence."
                )
            for b in blocks:
                if isinstance(b, dict):
                    b_tok = int(b.get("tokens", 0) or 0)
                    b_cap = int(b.get("cap_tokens", b.get("max_tokens", 3500)) or 3500)
                    if b_tok > b_cap:
                        errors.append(
                            f"Law L07 violation: {label} block {b.get('block_id')} tokens ({b_tok}) > cap ({b_cap})."
                        )

    if proposal is not None:
        if any(k in proposal for k in ("manifest", "context_manifest", "total_tokens", "blocks")):
            target = proposal.get("context_manifest") if isinstance(proposal.get("context_manifest"), dict) else proposal
            _inspect_budget(target, "proposal_manifest")
        return len(errors) == 0, errors

    manifests_dir = root / "context" / "manifests"
    if manifests_dir.is_dir():
        for mp in sorted(manifests_dir.glob("*.json")):
            try:
                _inspect_budget(_load_json(mp), mp.name)
            except Exception as exc:
                errors.append(f"Law L07 error reading {mp.name}: {exc}")

    return len(errors) == 0, errors


# ============================================================================
# LAW L08: Evidence-Cited Reflections & Relationship Updates
# ============================================================================
def check_reflection_evidence_citations(
    proposal: dict[str, Any] | None = None,
    repo_root: Path | str | None = None,
) -> tuple[bool, list[str]]:
    """Law L08: Every reflection or mutable relationship update cites >= 1 valid event_id present in events/."""
    errors: list[str] = []
    root = _resolve_root(repo_root)
    known_events = _load_known_events(root, proposal)

    def _check_citations(obj: dict[str, Any], label: str) -> None:
        ev_type = str(obj.get("event_type") or "")
        mem_type = str(obj.get("memory_type") or "")
        has_rel_update = bool(obj.get("relationship_update") or obj.get("mutable_relationship_update"))
        is_reflection = (
            ev_type == "NIGHTLY_REFLECTION"
            or mem_type == "reflection"
            or "reflection" in obj
            or has_rel_update
        )
        if not is_reflection:
            return

        target = obj.get("reflection") if isinstance(obj.get("reflection"), dict) else obj
        citations = (
            target.get("cited_event_ids")
            if "cited_event_ids" in target
            else target.get("evidence_refs")
        )
        if not isinstance(citations, list) or len(citations) == 0:
            errors.append(
                f"Law L08 violation: {label} reflection/relationship update has zero cited_event_ids."
            )
            return

        for cid in citations:
            if not isinstance(cid, str) or not cid.strip():
                errors.append(f"Law L08 violation: {label} contains empty/non-string event citation {cid!r}.")
            elif cid not in known_events:
                errors.append(
                    f"Law L08 violation: {label} cites non-existent/hallucinated event_id '{cid}'."
                )

    if proposal is not None:
        _check_citations(proposal, "proposal")
        return len(errors) == 0, errors

    for ev_id, ev in known_events.items():
        if ev.get("event_type") == "NIGHTLY_REFLECTION":
            _check_citations(ev, f"event[{ev_id}]")

    return len(errors) == 0, errors


# ============================================================================
# LAW L09: Stress-Gated Polarity Inversion with 7-Feast Cooldown
# ============================================================================
def check_polarity_inversion_cooldown(
    proposal: dict[str, Any] | None = None,
    repo_root: Path | str | None = None,
) -> tuple[bool, list[str]]:
    """Law L09: polarity_inversion_active only true when stress >= 0.80, kp_exo >= 7.0, and prior cooldown_days == 0."""
    errors: list[str] = []
    root = _resolve_root(repo_root)

    def _inspect_inversion(obj: dict[str, Any], label: str) -> None:
        inv_active = bool(
            obj.get("polarity_inversion_active")
            or obj.get("event_type") == "POLARITY_INVERSION"
            or (isinstance(obj.get("momentary_state"), dict) and obj["momentary_state"].get("polarity_inversion_active"))
        )
        if not inv_active:
            return

        st = obj.get("momentary_state") if isinstance(obj.get("momentary_state"), dict) else obj
        stress = float(st.get("stress", obj.get("stress", 0.0)) or 0.0)
        kp_exo = float(st.get("kp_exo", obj.get("kp_exo", 0.0)) or 0.0)
        prior_cd = int(
            st.get(
                "prior_cooldown_days",
                obj.get(
                    "prior_cooldown_days",
                    st.get("polarity_inversion_cooldown_days_before", 0),
                ),
            )
            or 0
        )

        if stress < 0.80:
            errors.append(
                f"Law L09 violation: {label} activated Polarity Inversion with stress={stress:.2f} (< 0.80 threshold)."
            )
        if kp_exo < 7.0:
            errors.append(
                f"Law L09 violation: {label} activated Polarity Inversion with kp_exo={kp_exo:.2f} (< 7.0 threshold)."
            )
        if prior_cd > 0:
            errors.append(
                f"Law L09 violation: {label} activated Polarity Inversion while prior cooldown_days={prior_cd} (> 0)."
            )

    if proposal is not None:
        _inspect_inversion(proposal, "proposal")
        return len(errors) == 0, errors

    events_dir = root / "events"
    if events_dir.is_dir():
        for p in sorted(events_dir.glob("*.json")):
            try:
                _inspect_inversion(_load_json(p), p.name)
            except Exception as exc:
                errors.append(f"Law L09 error reading {p.name}: {exc}")

    return len(errors) == 0, errors


# ============================================================================
# LAW L10: Rashomon Relay Baton-Handoff Continuity
# ============================================================================
def check_baton_handoff_continuity(
    proposal: dict[str, Any] | None = None,
    repo_root: Path | str | None = None,
) -> tuple[bool, list[str]]:
    """Law L10: Segment k's active_pov_id equals segment k-1's next_pov_target."""
    errors: list[str] = []
    root = _resolve_root(repo_root)

    if proposal is not None:
        if "prev_next_pov_target" in proposal and "active_pov_id" in proposal:
            expected_pov = str(proposal["prev_next_pov_target"] or "").strip()
            actual_pov = str(proposal["active_pov_id"] or "").strip()
            if expected_pov and actual_pov != expected_pov:
                errors.append(
                    f"Law L10 violation: broken Rashomon baton handoff — segment active_pov_id '{actual_pov}' "
                    f"!= previous segment next_pov_target '{expected_pov}'."
                )

        seg_chain = proposal.get("segment_chain") or proposal.get("segments")
        if isinstance(seg_chain, list) and len(seg_chain) >= 2:
            for idx in range(1, len(seg_chain)):
                prev_seg = seg_chain[idx - 1]
                curr_seg = seg_chain[idx]
                if isinstance(prev_seg, dict) and isinstance(curr_seg, dict):
                    expected = str(prev_seg.get("next_pov_target") or "").strip()
                    actual = str(curr_seg.get("active_pov_id") or "").strip()
                    if expected != actual:
                        errors.append(
                            f"Law L10 violation: segment[{idx}] active_pov_id '{actual}' != "
                            f"segment[{idx - 1}] next_pov_target '{expected}'."
                        )
        return len(errors) == 0, errors

    seg_dir = root / "story" / "segments"
    if seg_dir.is_dir():
        seg_files = sorted(seg_dir.glob("*.json"))
        segments_by_sol: dict[int, list[dict[str, Any]]] = {}
        for sf in seg_files:
            try:
                seg = _load_json(sf)
                if isinstance(seg, dict):
                    sol = int(seg.get("colony_sol", 1) or 1)
                    segments_by_sol.setdefault(sol, []).append(seg)
            except Exception as exc:
                errors.append(f"Law L10 error reading {sf.name}: {exc}")

        for sol, segs in sorted(segments_by_sol.items()):
            segs.sort(key=lambda s: (int(s.get("tick_id", 0)), int(s.get("segment_index", 0))))
            for idx in range(1, len(segs)):
                prev_target = str(segs[idx - 1].get("next_pov_target") or "").strip()
                curr_pov = str(segs[idx].get("active_pov_id") or "").strip()
                if prev_target and curr_pov and prev_target != curr_pov:
                    errors.append(
                        f"Law L10 violation on Sol {sol}: segment {idx} active_pov_id '{curr_pov}' "
                        f"!= previous segment next_pov_target '{prev_target}'."
                    )

    return len(errors) == 0, errors


# ============================================================================
# LAW L11: PvE Conflict & No-Betrayal Invariant
# ============================================================================
def check_pve_no_betrayal_invariant(
    proposal: dict[str, Any] | None = None,
    repo_root: Path | str | None = None,
) -> tuple[bool, list[str]]:
    """Law L11: Zero human villains/betrayals; lethality == 0 on all interpersonal/shadow events."""
    errors: list[str] = []
    root = _resolve_root(repo_root)

    def _inspect_event_pve(obj: dict[str, Any], label: str) -> None:
        lethality = float(obj.get("lethality", 0) or 0)
        if lethality != 0.0:
            errors.append(f"Law L11 violation: {label} has lethality={lethality} (must be strictly 0).")
        if bool(obj.get("human_malice")) or bool(obj.get("betrayal")) or bool(obj.get("villain_arc")):
            errors.append(f"Law L11 violation: {label} flags forbidden human malice/betrayal/villainy.")

        text_blob = " ".join(
            str(obj.get(k) or "")
            for k in ("event_type", "summary", "description", "conflict_mode", "prank_description")
        ).lower()
        for kw in HOSTILE_PVE_KEYWORDS:
            if kw in text_blob:
                errors.append(f"Law L11 violation: {label} contains forbidden lethal/betrayal keyword '{kw}'.")

    if proposal is not None:
        _inspect_event_pve(proposal, "proposal")
        if isinstance(proposal.get("event"), dict):
            _inspect_event_pve(proposal["event"], "proposal.event")
        return len(errors) == 0, errors

    rel_path = root / "relationships" / "initial_matrix_120.json"
    if rel_path.is_file():
        rel_data = _load_json(rel_path)
        pairs = rel_data.get("pairs") or []
        if len(pairs) != 120:
            errors.append(f"Law L11 violation: expected 120 undirected pairs, found {len(pairs)}.")
        for p in pairs:
            bs = float(p.get("bond_strength", 0.0) or 0.0)
            if bs < 0.35:
                errors.append(f"Law L11 violation: pair {p.get('pair_id')} bond_strength {bs} < 0.35 PvE floor.")

    events_dir = root / "events"
    if events_dir.is_dir():
        for p in sorted(events_dir.glob("*.json")):
            try:
                _inspect_event_pve(_load_json(p), p.name)
            except Exception as exc:
                errors.append(f"Law L11 error reading {p.name}: {exc}")

    return len(errors) == 0, errors


# ============================================================================
# LAW L12: Shadow Economy 3-Feast Maturity Delay & Asymmetric Attribution
# ============================================================================
def check_shadow_economy_3_feast_delay(
    proposal: dict[str, Any] | None = None,
    repo_root: Path | str | None = None,
) -> tuple[bool, list[str]]:
    """Law L12: Shadow Economy prank maturity_sol >= origin_sol + 3 and asymmetric blind-spot attribution."""
    errors: list[str] = []
    root = _resolve_root(repo_root)

    def _inspect_prank(entry: dict[str, Any], label: str) -> None:
        ev_type = str(entry.get("event_type") or "")
        is_prank = (
            ev_type in ("SHADOW_ECONOMY_PRANK_SEEDED", "SHADOW_ECONOMY_PRANK_MATURED")
            or "prank_id" in entry
            or "origin_sol" in entry
            or "maturity_sol" in entry
            or "shadow_prank" in entry
        )
        if not is_prank:
            return

        target = entry.get("shadow_prank") if isinstance(entry.get("shadow_prank"), dict) else entry
        origin_sol = int(target.get("origin_sol", 1) or 1)
        maturity_sol = int(target.get("maturity_sol", origin_sol) or origin_sol)
        if maturity_sol < origin_sol + 3:
            errors.append(
                f"Law L12 violation: {label} maturity_sol ({maturity_sol}) < origin_sol ({origin_sol}) + 3 (3-Feast delay required)."
            )

        if bool(target.get("matured")) or ev_type == "SHADOW_ECONOMY_PRANK_MATURED":
            matured_sol = int(target.get("matured_on_sol", target.get("colony_sol", maturity_sol)) or maturity_sol)
            if matured_sol < origin_sol + 3:
                errors.append(
                    f"Law L12 violation: {label} matured on Sol {matured_sol} before 3-Feast delay (origin_sol={origin_sol})."
                )

        node_a = str(target.get("node_a") or target.get("instigator") or target.get("creditor") or "").strip()
        node_b = str(target.get("node_b") or target.get("intended_target") or target.get("debtor") or "").strip()
        node_c = str(target.get("node_c") or target.get("collateral_recipient") or target.get("victim") or "").strip()
        blamed = str(target.get("blamed_node") or target.get("attributed_to") or node_a).strip()

        if not (node_a and node_b and node_c) or len({node_a, node_b, node_c}) < 3:
            errors.append(
                f"Law L12 violation: {label} requires 3 distinct nodes (node_a, node_b, node_c) for Main Character Blind Spot triad, "
                f"got ({node_a!r}, {node_b!r}, {node_c!r})."
            )
        if target.get("target_b_missed") is False:
            errors.append(f"Law L12 violation: {label} target_b_missed is False (intended target B must miss the prank).")
        if blamed and node_a and blamed != node_a:
            errors.append(
                f"Law L12 violation: {label} asymmetric attribution broken (collateral C blamed '{blamed}' instead of instigator '{node_a}')."
            )

    if proposal is not None:
        _inspect_prank(proposal, "proposal")
        return len(errors) == 0, errors

    events_dir = root / "events"
    if events_dir.is_dir():
        for p in sorted(events_dir.glob("*.json")):
            try:
                _inspect_prank(_load_json(p), p.name)
            except Exception as exc:
                errors.append(f"Law L12 error reading {p.name}: {exc}")

    return len(errors) == 0, errors


# ============================================================================
# LAW L13: Daily Feast Convergence
# ============================================================================
def check_feast_daily_convergence(
    proposal: dict[str, Any] | None = None,
    repo_root: Path | str | None = None,
) -> tuple[bool, list[str]]:
    """Law L13: Every completed colony_sol includes a THE_FEAST_CONVERGENCE event with all 16 character IDs present."""
    errors: list[str] = []
    root = _resolve_root(repo_root)

    def _inspect_feast_events(sol_id: int, sol_events: list[dict[str, Any]], label: str) -> None:
        feast_events = [
            e
            for e in sol_events
            if isinstance(e, dict)
            and (e.get("event_type") == "THE_FEAST_CONVERGENCE" or e.get("day_phase") == "THE_FEAST")
            and e.get("event_type") == "THE_FEAST_CONVERGENCE"
        ]
        if not feast_events:
            errors.append(
                f"Law L13 violation: {label} completed Sol {sol_id} is missing mandatory THE_FEAST_CONVERGENCE event."
            )
            return

        for fev in feast_events:
            actors = set(fev.get("actors") or [])
            missing = sorted(set(CANONICAL_16_CHARACTER_IDS) - actors)
            if len(actors) < 16 or missing:
                errors.append(
                    f"Law L13 violation: {label} Sol {sol_id} THE_FEAST_CONVERGENCE has {len(actors)}/16 characters "
                    f"(missing={missing})."
                )

    if proposal is not None:
        if proposal.get("completed_sol") is not None or "sol_events" in proposal or proposal.get("event_type") == "THE_FEAST_CONVERGENCE":
            if proposal.get("event_type") == "THE_FEAST_CONVERGENCE" and "sol_events" not in proposal:
                _inspect_feast_events(int(proposal.get("colony_sol", 1)), [proposal], "proposal")
            else:
                sol_id = int(proposal.get("completed_sol", proposal.get("colony_sol", 1)))
                sol_events = proposal.get("sol_events") or []
                _inspect_feast_events(sol_id, sol_events, "proposal")
        return len(errors) == 0, errors

    events_dir = root / "events"
    if events_dir.is_dir():
        events_by_sol: dict[int, list[dict[str, Any]]] = {}
        for p in sorted(events_dir.glob("*.json")):
            try:
                ev = _load_json(p)
                if isinstance(ev, dict):
                    sol = int(ev.get("colony_sol", 1) or 1)
                    events_by_sol.setdefault(sol, []).append(ev)
            except Exception as exc:
                errors.append(f"Law L13 error reading {p.name}: {exc}")

        for sol, ev_list in sorted(events_by_sol.items()):
            phases_seen = {str(e.get("day_phase") or "") for e in ev_list}
            if DAY_PHASES_ORDER[3] in phases_seen or len(phases_seen & set(DAY_PHASES_ORDER)) == 4:
                _inspect_feast_events(sol, ev_list, f"repo_events[sol={sol}]")

    return len(errors) == 0, errors


# ============================================================================
# LAW L14: Jules-Only Rolling 24h Session Budget Guard (<= 270 / 300)
# ============================================================================
def check_jules_rolling_24h_budget(
    proposal: dict[str, Any] | None = None,
    repo_root: Path | str | None = None,
) -> tuple[bool, list[str]]:
    """Law L14: Rolling 24h session dispatch count <= 270 (225 scheduled + 30 retry reserve + 45 safety buffer)."""
    errors: list[str] = []
    root = _resolve_root(repo_root)

    def _inspect_budget_state(bobj: dict[str, Any], label: str) -> None:
        ceiling = int(bobj.get("plan_ceiling_rolling_24h", 300) or 300)
        hard_cap = int(bobj.get("hard_dispatch_ceiling", 270) or 270)
        dispatched = int(
            bobj.get(
                "rolling_24h_dispatched",
                bobj.get("sessions_dispatched_rolling_24h", bobj.get("dispatched_count", 0)),
            )
            or 0
        )
        requested = int(bobj.get("requested_sessions", 0) or 0)
        total_projected = dispatched + requested

        if hard_cap > 270 or (ceiling - hard_cap) < 30:
            errors.append(
                f"Law L14 violation: {label} hard_dispatch_ceiling={hard_cap} violates mandatory 30-session safety margin below {ceiling}."
            )
        if total_projected > 270:
            errors.append(
                f"Law L14 violation: {label} rolling 24h session count ({total_projected}) exceeds hard safety ceiling of 270/300."
            )
        scheduled = int(bobj.get("scheduled_productive_sessions", 225) or 225)
        if scheduled > 225:
            errors.append(
                f"Law L14 violation: {label} scheduled_productive_sessions ({scheduled}) exceeds 225/day allocation."
            )

    if proposal is not None:
        if any(
            k in proposal
            for k in (
                "jules_budget",
                "rolling_24h_dispatched",
                "sessions_dispatched_rolling_24h",
                "dispatched_count",
                "hard_dispatch_ceiling",
            )
        ):
            target = proposal.get("jules_budget") if isinstance(proposal.get("jules_budget"), dict) else proposal
            _inspect_budget_state(target, "proposal_budget")
        return len(errors) == 0, errors

    ws_path = root / "canon" / "schemas" / "world_state_v2.json"
    if ws_path.is_file():
        ws = _load_json(ws_path)
        alloc = ws.get("jules_only_300_session_allocation") or {}
        _inspect_budget_state(alloc, "world_state_v2.jules_allocation")
        buckets = alloc.get("task_buckets") or {}
        if buckets and sum(int(v) for v in buckets.values()) != 225:
            errors.append(
                f"Law L14 violation: world_state_v2 task_buckets sum to {sum(int(v) for v in buckets.values())} != 225."
            )

    budget_path = root / "ops" / "budget.json"
    if budget_path.is_file():
        _inspect_budget_state(_load_json(budget_path), "ops/budget.json")

    return len(errors) == 0, errors


# ============================================================================
# LAW L15: Evening Dispatch Faithfulness & 4-Block Coverage
# ============================================================================
def check_dispatch_claim_event_citations(
    proposal: dict[str, Any] | None = None,
    repo_root: Path | str | None = None,
) -> tuple[bool, list[str]]:
    """Law L15: Every Evening Dispatch story, gossip item, and block digest cites valid event_ids matching actors/location and covers all active day phases."""
    errors: list[str] = []
    root = _resolve_root(repo_root)
    known_events = _load_known_events(root, proposal)

    def _verify_claim_item(item: dict[str, Any], section_label: str) -> None:
        cited = item.get("cited_event_ids") or item.get("evidence_refs") or item.get("event_ids") or []
        if not isinstance(cited, list) or len(cited) == 0:
            errors.append(f"Law L15 violation: {section_label} is missing cited_event_ids.")
            return

        matched_events: list[dict[str, Any]] = []
        for eid in cited:
            if not isinstance(eid, str) or eid not in known_events:
                errors.append(
                    f"Law L15 violation: {section_label} cites non-existent/unverified event_id '{eid}'."
                )
            else:
                matched_events.append(known_events[eid])

        if not matched_events:
            return

        # Verify actor faithfulness if claim specifies actors
        claim_actors = item.get("actors")
        if isinstance(claim_actors, list) and claim_actors:
            valid_actors: set[str] = set()
            for mev in matched_events:
                valid_actors.update(str(a) for a in (mev.get("actors") or []))
            if valid_actors:
                unverified_actors = [a for a in claim_actors if str(a) not in valid_actors]
                if unverified_actors:
                    errors.append(
                        f"Law L15 violation: {section_label} claims actors {unverified_actors} not present in cited events {cited}."
                    )

        # Verify location faithfulness if claim specifies location
        claim_loc = item.get("location")
        if isinstance(claim_loc, str) and claim_loc.strip():
            valid_locs = {str(mev.get("location") or "").strip() for mev in matched_events if mev.get("location")}
            if valid_locs and claim_loc.strip() not in valid_locs:
                errors.append(
                    f"Law L15 violation: {section_label} claims location '{claim_loc}' not matching cited event locations {sorted(valid_locs)}."
                )

    def _inspect_dispatch(dobj: dict[str, Any], label: str) -> None:
        lead = dobj.get("lead_story")
        if not isinstance(lead, dict):
            errors.append(f"Law L15 violation: {label} is missing lead_story object.")
        else:
            _verify_claim_item(lead, f"{label}.lead_story")

        for idx, dev in enumerate(dobj.get("developing_stories") or []):
            if isinstance(dev, dict):
                _verify_claim_item(dev, f"{label}.developing_stories[{idx}]")

        gossip_list = (
            dobj.get("gossip_and_shadow_column")
            or dobj.get("gossip_items")
            or dobj.get("gossip_column")
            or dobj.get("shadow_rumors")
            or []
        )
        for idx, gos in enumerate(gossip_list):
            if isinstance(gos, dict):
                _verify_claim_item(gos, f"{label}.gossip[{idx}]")

        raw_digests = (
            dobj.get("four_block_digests")
            or dobj.get("block_digests")
            or dobj.get("phase_digests")
            or {}
        )
        covered_phases: set[str] = set()
        if isinstance(raw_digests, dict):
            for phase_key, dig in raw_digests.items():
                covered_phases.add(str(phase_key).strip().upper())
                if isinstance(dig, dict):
                    _verify_claim_item(dig, f"{label}.block_digests[{phase_key}]")
        elif isinstance(raw_digests, list):
            for idx, dig in enumerate(raw_digests):
                if isinstance(dig, dict):
                    ph = str(dig.get("day_phase") or dig.get("phase") or "").strip().upper()
                    if ph:
                        covered_phases.add(ph)
                    _verify_claim_item(dig, f"{label}.block_digests[{idx}]")

        if isinstance(dobj.get("covered_day_phases"), list):
            for ph in dobj["covered_day_phases"]:
                covered_phases.add(str(ph).strip().upper())

        sol_num = int(dobj.get("colony_sol", 1) or 1)
        active_phases = {
            str(e.get("day_phase") or "").strip().upper()
            for e in known_events.values()
            if int(e.get("colony_sol", sol_num) or sol_num) == sol_num
            and str(e.get("day_phase") or "").strip().upper() in DAY_PHASES_ORDER
        }
        if not active_phases and dobj.get("require_all_4_phases"):
            active_phases = set(DAY_PHASES_ORDER)

        missing_phases = sorted(active_phases - covered_phases)
        if missing_phases:
            errors.append(
                f"Law L15 violation: {label} failed to cover active day phases {missing_phases}."
            )

    if proposal is not None:
        if any(k in proposal for k in ("evening_dispatch", "dispatch", "lead_story", "developing_stories")):
            target = (
                proposal.get("evening_dispatch")
                or proposal.get("dispatch")
                or proposal
            )
            if isinstance(target, dict):
                _inspect_dispatch(target, "proposal_dispatch")
        return len(errors) == 0, errors

    digests_dir = root / "digests" / "daily"
    if digests_dir.is_dir():
        for dp in sorted(digests_dir.glob("*.json")):
            try:
                _inspect_dispatch(_load_json(dp), dp.name)
            except Exception as exc:
                errors.append(f"Law L15 error reading {dp.name}: {exc}")

    return len(errors) == 0, errors


# ============================================================================
# LAW L16: Psychometric Drift Z-Score Circuit Breaker (|z| > 2.0)
# ============================================================================
def check_drift_zscore_circuit_breaker(
    proposal: dict[str, Any] | None = None,
    repo_root: Path | str | None = None,
) -> tuple[bool, list[str]]:
    """Law L16: Any character drift |z| > 2.0 MUST have drift_alert == True and non-empty corrective_authors_note with re_anchor_ticks == 3."""
    errors: list[str] = []
    root = _resolve_root(repo_root)

    def _inspect_drift_record(rec: dict[str, Any], label: str) -> None:
        if isinstance(rec.get("audits"), list):
            for idx, item in enumerate(rec["audits"]):
                if isinstance(item, dict):
                    _inspect_drift_record(item, f"{label}.audits[{idx}]")
            return

        z_map = rec.get("axis_z_scores") or rec.get("z_scores") or {}
        max_abs_z = float(rec.get("max_abs_z", 0.0) or 0.0)
        if isinstance(z_map, dict) and z_map:
            max_abs_z = max(max_abs_z, max(abs(float(v)) for v in z_map.values() if isinstance(v, (int, float))))

        if max_abs_z > 2.0:
            drift_alert = bool(rec.get("drift_alert"))
            note = str(rec.get("corrective_authors_note") or "").strip()
            re_anchor_ticks = int(rec.get("re_anchor_ticks", 0) or 0)
            if not drift_alert:
                errors.append(
                    f"Law L16 violation: {label} has max_abs_z={max_abs_z:.2f} (> 2.0) but drift_alert is False."
                )
            if not note:
                errors.append(
                    f"Law L16 violation: {label} has max_abs_z={max_abs_z:.2f} (> 2.0) but corrective_authors_note is empty."
                )
            if re_anchor_ticks != 3:
                errors.append(
                    f"Law L16 violation: {label} has max_abs_z={max_abs_z:.2f} (> 2.0) but re_anchor_ticks={re_anchor_ticks} (must be 3)."
                )

    if proposal is not None:
        if any(k in proposal for k in ("drift_audit", "max_abs_z", "axis_z_scores", "audits")):
            target = proposal.get("drift_audit") if isinstance(proposal.get("drift_audit"), dict) else proposal
            _inspect_drift_record(target, "proposal_drift_audit")
        return len(errors) == 0, errors

    qa_dir = root / "qa"
    if qa_dir.is_dir():
        for qp in sorted(qa_dir.glob("*drift*.json")):
            try:
                _inspect_drift_record(_load_json(qp), qp.name)
            except Exception as exc:
                errors.append(f"Law L16 error reading {qp.name}: {exc}")

    return len(errors) == 0, errors


# ============================================================================
# SHOWRUNNER DM STORYTELLING & LPI CONTRACT VERIFIER (Mulligan / Mercer / Murphy)
# ============================================================================
def validate_showrunner_storytelling_contract(
    proposal: dict[str, Any],
) -> dict[str, Any]:
    """Validate a scene or campaign ledger against the AI Dungeon Master Storytelling Guide:
    - Living Playability Index (LPI >= 0.45, never 'Unplayable Draft')
    - Showrunner pacing_mode in {MERCER_EXPLORATION, MULLIGAN_CRISIS, MURPHY_TACTICAL, MA_NEGATIVE_SPACE}
    - Murph's Two-Fight Short-Rest Cadence (0 <= consequential_fights_since_short_rest <= 2)
    - Mercer's 3 Interactive Features with system_verb in {DEFEND, ATTRACT, CONSUME, CONCEAL}
    - Mulligan's 'Toys, Not Plots' reactive entities (pressure_index in 1..10)
    - CALYPSO Zero-Raw-Stat-Numbers rule in narrative prose.
    """
    from engine.local_ai_manager import verify_calypso_narrative_purity

    errors: list[str] = []
    ledger = proposal.get("showrunner_ledger") if isinstance(proposal.get("showrunner_ledger"), dict) else proposal

    meta = ledger.get("campaign_metadata")
    if isinstance(meta, dict):
        pmode = str(meta.get("pacing_mode") or "")
        if pmode not in ("MERCER_EXPLORATION", "MULLIGAN_CRISIS", "MURPHY_TACTICAL", "MA_NEGATIVE_SPACE"):
            errors.append(f"Showrunner contract violation: invalid pacing_mode '{pmode}'.")
        fights = int(meta.get("consequential_fights_since_short_rest", 0) or 0)
        if fights < 0 or fights > 2:
            errors.append(
                f"Showrunner contract violation (Murph Two-Fight Cadence): "
                f"consequential_fights_since_short_rest={fights} outside [0, 2]."
            )

    loc = ledger.get("active_location")
    if isinstance(loc, dict):
        features = loc.get("interactive_features")
        if not isinstance(features, list) or len(features) != 3:
            errors.append("Showrunner contract violation (Mercer 3-Feature Rule): active_location requires exactly 3 interactive_features.")
        else:
            for idx, feat in enumerate(features):
                verb = str((feat or {}).get("system_verb") or "")
                if verb not in ("DEFEND", "ATTRACT", "CONSUME", "CONCEAL"):
                    errors.append(
                        f"Showrunner contract violation: feature[{idx}] has invalid system_verb '{verb}'."
                    )

    toys = ledger.get("reactive_toys")
    if isinstance(toys, list):
        if len(toys) == 0:
            errors.append("Showrunner contract violation (Mulligan Toys-Not-Plots): reactive_toys cannot be empty.")
        for idx, toy in enumerate(toys):
            if not isinstance(toy, dict):
                continue
            p_idx = int(toy.get("pressure_index", 0) or 0)
            if p_idx < 1 or p_idx > 10:
                errors.append(
                    f"Showrunner contract violation: reactive_toys[{idx}] pressure_index={p_idx} outside [1, 10]."
                )
            for req_key in ("motivation_goal", "consistent_method", "immediate_complication", "uninterrupted_escalation"):
                if not str(toy.get(req_key) or "").strip():
                    errors.append(f"Showrunner contract violation: reactive_toys[{idx}] missing '{req_key}'.")

    lpi = ledger.get("lpi_metrics") or proposal.get("lpi_metrics")
    if isinstance(lpi, dict):
        comp = float(lpi.get("composite_lpi", 0.0) or 0.0)
        cls_name = str(lpi.get("classification") or "")
        if comp < 0.45 or cls_name == "Unplayable Draft":
            errors.append(
                f"Showrunner LPI Gate violation: composite_lpi={comp:.2f} ({cls_name}) rejected as Unplayable Draft (< 0.45)."
            )

    prose_candidates = [
        str(proposal.get(k) or "")
        for k in ("prose", "narrative_prose", "segment_text", "text", "body")
        if proposal.get(k)
    ]
    for ptext in prose_candidates:
        cal_ok, cal_errs = verify_calypso_narrative_purity(ptext)
        if not cal_ok:
            errors.extend(cal_errs)

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


# ============================================================================
# MASTER REGISTRY & VALIDATION ENTRYPOINTS
# ============================================================================
LAWS_REGISTRY: tuple[tuple[str, str, Any], ...] = (
    ("L01", "check_zero_pii", check_zero_pii),
    ("L02", "check_append_only_events", check_append_only_events),
    ("L03", "check_16_cast_bijection", check_16_cast_bijection),
    ("L04", "check_trait_type_alignment", check_trait_type_alignment),
    ("L05", "check_state_bounds_and_trait_immutability", check_state_bounds_and_trait_immutability),
    ("L06", "check_single_pov_swap_isolation", check_single_pov_swap_isolation),
    ("L07", "check_context_token_budget", check_context_token_budget),
    ("L08", "check_reflection_evidence_citations", check_reflection_evidence_citations),
    ("L09", "check_polarity_inversion_cooldown", check_polarity_inversion_cooldown),
    ("L10", "check_baton_handoff_continuity", check_baton_handoff_continuity),
    ("L11", "check_pve_no_betrayal_invariant", check_pve_no_betrayal_invariant),
    ("L12", "check_shadow_economy_3_feast_delay", check_shadow_economy_3_feast_delay),
    ("L13", "check_feast_daily_convergence", check_feast_daily_convergence),
    ("L14", "check_jules_rolling_24h_budget", check_jules_rolling_24h_budget),
    ("L15", "check_dispatch_claim_event_citations", check_dispatch_claim_event_citations),
    ("L16", "check_drift_zscore_circuit_breaker", check_drift_zscore_circuit_breaker),
)


def validate_proposal(
    proposal: dict[str, Any],
    repo_root: Path | str | None = None,
) -> dict[str, Any]:
    """Validate a candidate proposal bundle against all 16 Constitutional Laws (L01..L16)."""
    root = _resolve_root(repo_root)
    violated_laws: list[str] = []
    all_errors: list[str] = []
    law_results: dict[str, dict[str, Any]] = {}

    for law_id, func_name, checker_fn in LAWS_REGISTRY:
        passed, errs = checker_fn(proposal=proposal, repo_root=root)
        law_results[law_id] = {
            "law_id": law_id,
            "check_name": func_name,
            "passed": passed,
            "errors": errs,
        }
        if not passed:
            violated_laws.append(law_id)
            all_errors.extend(errs)

    return {
        "valid": len(violated_laws) == 0,
        "violated_laws": violated_laws,
        "law_results": law_results,
        "errors": all_errors,
    }


def validate_repository(
    repo_root: Path | str | None = None,
    strict: bool = True,
) -> dict[str, Any]:
    """Validate the repository state against all 16 Constitutional Laws (L01..L16)."""
    root = _resolve_root(repo_root)
    violated_laws: list[str] = []
    all_errors: list[str] = []
    law_results: dict[str, dict[str, Any]] = {}

    for law_id, func_name, checker_fn in LAWS_REGISTRY:
        passed, errs = checker_fn(proposal=None, repo_root=root)
        law_results[law_id] = {
            "law_id": law_id,
            "check_name": func_name,
            "passed": passed,
            "errors": errs,
        }
        if not passed:
            violated_laws.append(law_id)
            all_errors.extend(errs)

    return {
        "valid": len(violated_laws) == 0,
        "strict": strict,
        "laws_checked": len(LAWS_REGISTRY),
        "laws_passed": len(LAWS_REGISTRY) - len(violated_laws),
        "violated_laws": violated_laws,
        "law_results": law_results,
        "errors": all_errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Enclave of the 16 — 16-Law Constitutional Gate Checker (L01..L16)."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enforce strict repository-wide validation across all 16 Constitutional Laws.",
    )
    parser.add_argument(
        "--proposal-file",
        type=str,
        default=None,
        help="Path to a candidate proposal JSON file to validate against L01..L16.",
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        default=None,
        help="Optional override for repository root directory.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON output.",
    )
    args = parser.parse_args(argv)

    root = _resolve_root(args.repo_root)

    if args.proposal_file:
        prop_path = Path(args.proposal_file)
        if not prop_path.is_file():
            print(f"ERROR: Proposal file not found: {prop_path}", file=sys.stderr)
            return 2
        proposal_data = _load_json(prop_path)
        result = validate_proposal(proposal_data, repo_root=root)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result["valid"]:
                print(f"[CONSTITUTION PASS] Proposal '{prop_path.name}' passed 16/16 laws.")
            else:
                print(
                    f"[CONSTITUTION REJECT] Proposal '{prop_path.name}' violated {result['violated_laws']}: "
                    + "; ".join(result["errors"])
                )
        return 0 if result["valid"] else 1

    result = validate_repository(repo_root=root, strict=args.strict or True)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for law_id, func_name, _ in LAWS_REGISTRY:
            lr = result["law_results"][law_id]
            status = "PASS" if lr["passed"] else "FAIL"
            print(f"  [{status}] {law_id} ({func_name})")
            for err in lr["errors"]:
                print(f"         -> {err}")
        print(
            f"\nConstitutional Audit Summary: {result['laws_passed']}/{result['laws_checked']} laws passed."
        )
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
