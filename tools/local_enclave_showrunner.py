#!/usr/bin/env python3
"""100% Local Oasis Showrunner & Post-Jules Autonomous Cutover Engine (Nov 11 Ready).

Unites:
1. 16-Character Rashomon Scalpel POV rotation (`get_rashomon_scalpel_pov_pair`).
2. Local Ollama Showrunner (`LocalContextAwareManager` -> `gemma4:e4b-it-q4_K_M` / `qwen3.5:4b-q4_K_M`)
   with deterministic high-competence fallback.
3. 17th-Node Autonomous Offline Arc Evolution (`ReaderCharacterLearner.advance_autonomous_offline_arc`).
4. Live Atlas Kinetic Book compilation (`compile_enclave_atlas_bundle`).
5. Oasis Twin Bridge save-lineage synchronization (`sync_enclave_oasis_save_and_bridge`).
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

from engine.local_ai_manager import LocalContextAwareManager
from engine.oasis_twin_bridge import sync_enclave_oasis_save_and_bridge
from engine.reader_character_learner import ReaderCharacterLearner
from tools.check_enclave_constitutions import (
    get_rashomon_scalpel_pov_pair,
    validate_repository,
)
from tools.compile_enclave_to_atlas import compile_enclave_atlas_bundle
from tools.run_sol_simulation import run_simulation


def run_local_oasis_cycle(
    *,
    repo_root: Path | None = None,
    advance_sim_sols: int = 0,
    evolve_17th_node: bool = True,
    compile_atlas: bool = True,
    with_audio: bool = False,
) -> dict[str, Any]:
    """Execute a complete local Oasis Showrunner cycle without requiring cloud VMs."""
    root = Path(repo_root).resolve() if repo_root else REPO_ROOT
    ai_mgr = LocalContextAwareManager(repo_root=root)
    sympathy = ai_mgr.evaluate_hardware_sympathy()

    sim_result: dict[str, Any] | None = None
    if advance_sim_sols > 0:
        sim_result = run_simulation(
            sols=int(advance_sim_sols),
            verify_dispatch=True,
            repo_root=root,
        )

    latest_snap_path = root / "snapshots" / "latest.json"
    current_sol = 22
    current_tick = 85
    if latest_snap_path.is_file():
        try:
            snap = json.loads(latest_snap_path.read_text(encoding="utf-8"))
            current_sol = int(snap.get("colony_sol", 22) or 22)
            current_tick = int(snap.get("tick_id", 85) or 85)
        except Exception:
            pass

    active_pov, next_pov = get_rashomon_scalpel_pov_pair(current_tick, current_sol)
    sci_card = ai_mgr.select_grand_project_science_vegetable(current_sol, current_tick, active_pov)

    learner = ReaderCharacterLearner(repo_root=root)
    player_state = learner.load_state()
    if evolve_17th_node and player_state.get("initialized"):
        player_state = learner.advance_autonomous_offline_arc(
            sols_elapsed=max(1, int(advance_sim_sols or 1)),
            current_sol=current_sol,
        )

    atlas_res: dict[str, Any] = {}
    if compile_atlas:
        atlas_res = compile_enclave_atlas_bundle(repo_root=root, with_audio=with_audio)

    oasis_res = sync_enclave_oasis_save_and_bridge(repo_root=root)
    audit_res = validate_repository(repo_root=root, strict=True)

    return {
        "ok": bool(audit_res.get("valid")),
        "mode": "LOCAL_OASIS_SHOWRUNNER",
        "sovereign_forge_endpoint": "http://127.0.0.1:19447/v1alpha",
        "current_sol": current_sol,
        "current_tick": current_tick,
        "rashomon_active_pov": active_pov,
        "rashomon_next_pov": next_pov,
        "science_deck_card": sci_card,
        "hardware_sympathy": sympathy,
        "player_17th_node_initialized": bool(player_state.get("initialized")),
        "player_17th_node_stage": (player_state.get("arc_progression") or {}).get("stage"),
        "atlas_bundle": atlas_res,
        "oasis_bridge_synced": bool(oasis_res.get("lineage")),
        "constitutional_laws_passed": int(audit_res.get("laws_passed", 0)),
        "simulation_advanced": sim_result is not None,
    }


def synthesize_sovereign_forge_enclave_session(
    request_body: dict[str, Any],
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Execute a local Sovereign Forge Enclave session when cloud Jules is offline or post-2026-11-10."""
    root = Path(repo_root).resolve() if repo_root else REPO_ROOT
    cycle = run_local_oasis_cycle(
        repo_root=root,
        advance_sim_sols=0,
        evolve_17th_node=False,
        compile_atlas=False,
        with_audio=False,
    )
    title = str(request_body.get("title") or "enclave_local_forge_session")
    return {
        "name": f"sessions/forge_enclave_s{cycle['current_sol']:03d}_t{cycle['current_tick']:04d}",
        "state": "COMPLETED",
        "title": title,
        "sovereign_forge_mode": "LOCAL_OASIS_SHOWRUNNER",
        "rashomon_active_pov": cycle["rashomon_active_pov"],
        "constitutional_laws_passed": cycle["constitutional_laws_passed"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the 100% Local Oasis Showrunner & Atlas Book Compiler.")
    parser.add_argument("--advance-sols", type=int, default=0, help="Number of local Sols to simulate.")
    parser.add_argument("--with-audio", action="store_true", help="Synthesize local Piper TTS narration.")
    args = parser.parse_args()
    out = run_local_oasis_cycle(
        advance_sim_sols=args.advance_sols,
        evolve_17th_node=True,
        compile_atlas=True,
        with_audio=args.with_audio,
    )
    print(json.dumps(out, indent=2))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

