"""Oasis v2.0 Digital Twin Save Lineage, Rupee (`RUP`) Meta-Reward & Live ODE Bridge (`CRUCIBLE-14`).

Strictly preserves Law L12 (in-world `engine/shadow_economy.py` and `events/*.json` remain 100%
non-monetary 3-Sol favor/prank triads) while bridging `PA-15` (`enclave-digital-twin`) to the
LFS Oasis v2.0 ecosystem:
1. Archives `snapshots/latest.json`, `digests/daily/sol_*_dispatch.json`, and `relationships/graph.json`
   to `${XDG_DATA_HOME:-$HOME/.local/share}/lfs-oasis/saves/enclave-digital-twin/` with a vector-clock
   `save.lineage.json` receipt (`schema: "aegisEnvelopeV1-save-lineage"`).
2. Computes player meta-rewards in `Rupees` (`RUP` CMY Gems: `+10 RUP` per verified Evening Dispatch,
   `+25 RUP` per Sol Feast convergence, `+50 RUP` per Grand Project milestone).
3. Publishes `enclaveTwinLiveState` (all 16 MBTI citizens `enclave_01_hector`..`enclave_16_elara`,
   including `enclave_07_willow` Whole-Trait ODE states and `kp_exo` magneto-weather) atomically
   under `fcntl.flock(LOCK_EX)` to `${XDG_DATA_HOME:-$HOME/.local/share}/lfs-aegis/aegis_asset_bridge.json`.
"""

from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any

from engine.enclave_city_sim import (
    generate_enclave_city_state,
    summarize_enclave_city_state,
)
from tools.check_enclave_constitutions import CANONICAL_16_CHARACTER_IDS


def _load_asset_bridge_lock_module(repo_root: Path | None = None) -> Any | None:
    """Resolve and load `aegis_asset_bridge_lock` for fcntl.flock + CRDT union updates, with safe fallback."""
    if "aegis_asset_bridge_lock" in sys.modules:
        return sys.modules["aegis_asset_bridge_lock"]
    try:
        import aegis_asset_bridge_lock as mod  # type: ignore
        return mod
    except ImportError:
        pass

    candidates: list[Path] = [
        Path(__file__).resolve().parents[3] / "core" / "companion" / "clients" / "linux" / "aegis_asset_bridge_lock.py",
    ]
    if repo_root is not None:
        resolved_root = Path(repo_root).resolve()
        if len(resolved_root.parents) >= 2:
            candidates.append(
                resolved_root.parents[1] / "core" / "companion" / "clients" / "linux" / "aegis_asset_bridge_lock.py"
            )
    for cand in candidates:
        if cand.is_file():
            try:
                spec = importlib.util.spec_from_file_location("aegis_asset_bridge_lock", str(cand))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    sys.modules["aegis_asset_bridge_lock"] = mod
                    spec.loader.exec_module(mod)
                    return mod
            except Exception:
                continue
    return None

OASIS_CMY_RUPEE_GEM_TIERS: tuple[int, ...] = (1, 5, 10, 25, 50, 100, 250, 500, 1000)
DISPATCH_REWARD_RUP = 10
FEAST_CONVERGENCE_REWARD_RUP = 25
GRAND_PROJECT_MILESTONE_REWARD_RUP = 50


def _xdg_data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _atomic_write_json(target_path: Path, payload: dict[str, Any]) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target_path.name}.",
        suffix=".tmp",
        dir=str(target_path.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        raw_bytes = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
        with os.fdopen(fd, "wb") as fh:
            fh.write(raw_bytes)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(str(tmp_path), str(target_path))
        try:
            dir_fd = os.open(str(target_path.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def compute_enclave_player_meta_rewards(repo_root: Path) -> dict[str, Any]:
    """Compute player-facing Rupee (`RUP`) meta-rewards from verified Enclave simulation milestones."""
    root = Path(repo_root).resolve()
    dispatches_dir = root / "digests" / "daily"
    feasts_dir = root / "story" / "feasts"
    events_dir = root / "events"

    dispatch_files = sorted(dispatches_dir.glob("sol_*_dispatch.json")) if dispatches_dir.is_dir() else []
    feast_files = sorted(feasts_dir.glob("sol_*_feast.json")) if feasts_dir.is_dir() else []

    milestone_event_ids: list[str] = []
    feast_event_ids: list[str] = []
    if events_dir.is_dir():
        for ev_path in sorted(events_dir.glob("*.json")):
            try:
                ev = json.loads(ev_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(ev, dict):
                continue
            ev_type = str(ev.get("event_type") or "")
            ev_id = str(ev.get("event_id") or ev_path.stem)
            if ev_type in ("EXPEDITION_DISCOVERY", "SCHRODINGER_HARVEST_DEBATE"):
                milestone_event_ids.append(ev_id)
            elif ev_type == "THE_FEAST_CONVERGENCE":
                feast_event_ids.append(ev_id)

    verified_dispatches = len(dispatch_files)
    verified_feasts = max(len(feast_files), len(feast_event_ids))
    verified_milestones = len(milestone_event_ids)

    total_rupees = (
        verified_dispatches * DISPATCH_REWARD_RUP
        + verified_feasts * FEAST_CONVERGENCE_REWARD_RUP
        + verified_milestones * GRAND_PROJECT_MILESTONE_REWARD_RUP
    )

    return {
        "currency_code": "RUP",
        "cmy_gem_tiers": list(OASIS_CMY_RUPEE_GEM_TIERS),
        "verified_dispatches_count": verified_dispatches,
        "verified_feasts_count": verified_feasts,
        "grand_project_milestones_count": verified_milestones,
        "milestone_event_ids": milestone_event_ids,
        "reward_breakdown_rup": {
            "evening_dispatches_rup": verified_dispatches * DISPATCH_REWARD_RUP,
            "sol_feast_convergences_rup": verified_feasts * FEAST_CONVERGENCE_REWARD_RUP,
            "grand_project_milestones_rup": verified_milestones * GRAND_PROJECT_MILESTONE_REWARD_RUP,
        },
        "total_earned_rupees": total_rupees,
        "in_world_economy_monetary": False,
    }


def extract_enclave_twin_live_state(repo_root: Path) -> dict[str, Any]:
    """Extract live 16-citizen Whole-Trait ODE states and exoplanet weather from `snapshots/latest.json`."""
    root = Path(repo_root).resolve()
    latest_path = root / "snapshots" / "latest.json"
    snap: dict[str, Any] = {}
    if latest_path.is_file():
        try:
            snap = json.loads(latest_path.read_text(encoding="utf-8"))
        except Exception:
            snap = {}

    weather = snap.get("weather") if isinstance(snap.get("weather"), dict) else {}
    chrono = snap.get("chronosphere") if isinstance(snap.get("chronosphere"), dict) else {}
    raw_states = snap.get("character_states") if isinstance(snap.get("character_states"), dict) else {}

    kp_exo = float(weather.get("kp_exo", chrono.get("kp_exo", 3.5)) or 3.5)
    colony_sol = int(snap.get("colony_sol", chrono.get("colony_sol", 1)) or 1)
    tick_id = int(snap.get("tick_id", chrono.get("tick_id", 1)) or 1)
    day_phase = str(snap.get("day_phase") or chrono.get("day_phase") or "DAWN_SHIFT")

    character_states: dict[str, dict[str, Any]] = {}
    for cid in CANONICAL_16_CHARACTER_IDS:
        st = raw_states.get(cid) if isinstance(raw_states.get(cid), dict) else {}
        trait_states = st.get("trait_states") if isinstance(st.get("trait_states"), dict) else {}
        character_states[cid] = {
            "character_id": cid,
            "tick_id": int(st.get("tick_id", tick_id) or tick_id),
            "day_phase": str(st.get("day_phase") or day_phase),
            "stress": float(st.get("stress", 0.25) or 0.0),
            "fatigue": float(st.get("fatigue", 0.20) or 0.0),
            "sleep_debt_norm": float(st.get("sleep_debt_norm", st.get("fatigue", 0.20)) or 0.0),
            "kp_exo": float(st.get("kp_exo", kp_exo) or kp_exo),
            "polarity_inversion_active": bool(st.get("polarity_inversion_active", False)),
            "trait_states": {
                "openness": float(trait_states.get("openness", st.get("openness", 0.5)) or 0.5),
                "conscientiousness": float(
                    trait_states.get("conscientiousness", st.get("conscientiousness", 0.5)) or 0.5
                ),
                "extraversion": float(trait_states.get("extraversion", st.get("extraversion", 0.5)) or 0.5),
                "agreeableness": float(trait_states.get("agreeableness", st.get("agreeableness", 0.5)) or 0.5),
                "neuroticism": float(trait_states.get("neuroticism", st.get("neuroticism", 0.5)) or 0.5),
                "hexaco_honesty_humility": float(
                    trait_states.get("hexaco_honesty_humility", st.get("hexaco_honesty_humility", 0.7)) or 0.7
                ),
            },
            "triggered_caps_rules": list(st.get("triggered_caps_rules") or []),
            "behavioral_directives": list(st.get("behavioral_directives") or []),
        }

    willow_state = character_states.get("enclave_07_willow", {})
    city_state = generate_enclave_city_state(root, seed=f"enclave_sol_{colony_sol:03d}")
    city_summary = summarize_enclave_city_state(city_state)
    return {
        "schema": "enclave-twin-live-state-v2",
        "project_id": "PA-15",
        "capsule_id": "enclave-digital-twin",
        "updated_at_iso": _utc_now_iso(),
        "colony_sol": colony_sol,
        "tick_id": tick_id,
        "day_phase": day_phase,
        "kp_exo": kp_exo,
        "micro_climate_regime": str(weather.get("micro_climate_regime") or "Nominal_ Valley_Breeze"),
        "active_biome_cell": str(weather.get("active_biome_cell") or "Enclave_Crater_Valley"),
        "willow_resonance": willow_state,
        "enclaveCitySummary": city_summary,
        "character_states": character_states,
    }


def sync_enclave_oasis_save_and_bridge(
    repo_root: Path | str,
    save_root: Path | str | None = None,
    bridge_path: Path | str | None = None,
    account_binding_id: str = "default",
    privacy_generation: int = 1,
) -> dict[str, Any]:
    """Archive Enclave state to Oasis Rclone save dir and atomically update `aegis_asset_bridge.json`."""
    root = Path(repo_root).resolve()
    data_home = _xdg_data_home()
    resolved_save_dir = (
        Path(save_root).resolve()
        if save_root is not None
        else (data_home / "lfs-oasis" / "saves" / "enclave-digital-twin")
    )
    resolved_bridge_path = (
        Path(bridge_path).resolve()
        if bridge_path is not None
        else (data_home / "lfs-aegis" / "aegis_asset_bridge.json")
    )

    resolved_save_dir.mkdir(parents=True, exist_ok=True)
    sha256_manifest: dict[str, str] = {}
    copied_files: list[str] = []

    latest_snap = root / "snapshots" / "latest.json"
    if latest_snap.is_file():
        dst_snap = resolved_save_dir / "latest.json"
        shutil.copy2(str(latest_snap), str(dst_snap))
        sha256_manifest["latest.json"] = _sha256_file(dst_snap)
        copied_files.append("latest.json")

    dispatches_dir = root / "digests" / "daily"
    if dispatches_dir.is_dir():
        dispatch_files = sorted(dispatches_dir.glob("sol_*_dispatch.json"))
        if dispatch_files:
            latest_disp = dispatch_files[-1]
            dst_disp = resolved_save_dir / latest_disp.name
            shutil.copy2(str(latest_disp), str(dst_disp))
            sha256_manifest[latest_disp.name] = _sha256_file(dst_disp)
            copied_files.append(latest_disp.name)

    rel_graph = root / "relationships" / "graph.json"
    if rel_graph.is_file():
        dst_graph = resolved_save_dir / "graph.json"
        shutil.copy2(str(rel_graph), str(dst_graph))
        sha256_manifest["graph.json"] = _sha256_file(dst_graph)
        copied_files.append("graph.json")

    city_state = generate_enclave_city_state(root)
    city_summary = summarize_enclave_city_state(city_state)
    dst_city = resolved_save_dir / "enclave_city_state.json"
    _atomic_write_json(dst_city, city_state)
    sha256_manifest["enclave_city_state.json"] = _sha256_file(dst_city)
    copied_files.append("enclave_city_state.json")

    lineage_path = resolved_save_dir / "save.lineage.json"
    prev_generation = 0
    parent_hashes: list[str] = []
    prev_vector_clock: dict[str, int] = {}
    if lineage_path.is_file():
        try:
            prev_lin = json.loads(lineage_path.read_text(encoding="utf-8"))
            prev_generation = int(prev_lin.get("generation", 0) or 0)
            if prev_lin.get("head_hash"):
                parent_hashes = [str(prev_lin["head_hash"])]
            if isinstance(prev_lin.get("vector_clock"), dict):
                prev_vector_clock = {str(k): int(v) for k, v in prev_lin["vector_clock"].items()}
        except Exception:
            pass

    next_generation = prev_generation + 1
    vector_clock = dict(prev_vector_clock)
    vector_clock["enclave-digital-twin"] = int(vector_clock.get("enclave-digital-twin", 0)) + 1

    manifest_blob = json.dumps(sha256_manifest, sort_keys=True).encode("utf-8")
    head_hash = hashlib.sha256(manifest_blob + f":{next_generation}".encode("utf-8")).hexdigest()
    now_iso = _utc_now_iso()

    meta_rewards = compute_enclave_player_meta_rewards(root)
    live_state = extract_enclave_twin_live_state(root)

    lineage_payload = {
        "schema": "aegisEnvelopeV1-save-lineage",
        "schema_v1": "lfs-oasis-save-lineage-v1",
        "capsule_id": "enclave-digital-twin",
        "project_id": "PA-15",
        "generation": next_generation,
        "vector_clock": vector_clock,
        "head_hash": head_hash,
        "parent_hashes": parent_hashes,
        "sha256_manifest": sha256_manifest,
        "currency_code": "RUP",
        "cmy_gem_tiers": list(OASIS_CMY_RUPEE_GEM_TIERS),
        "earned_rupees_total": meta_rewards["total_earned_rupees"],
        "colony_sol": live_state["colony_sol"],
        "tick_id": live_state["tick_id"],
        "enclave_city_summary": city_summary,
        "updated_at_iso": now_iso,
    }
    _atomic_write_json(lineage_path, lineage_payload)

    # Delegate to aegis_asset_bridge_lock.update_asset_bridge() (fcntl.flock + CRDT union) with safe fallback
    resolved_bridge_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = resolved_bridge_path.with_name(f"{resolved_bridge_path.name}.lock")
    partition_key = f"{account_binding_id}:{int(privacy_generation)}"
    bridge_lock_mod = _load_asset_bridge_lock_module(root)

    if bridge_lock_mod is not None and hasattr(bridge_lock_mod, "update_asset_bridge"):
        def _enclave_crdt_patch(part: dict[str, Any]) -> dict[str, Any]:
            prev_enclave_rup = int(part.get("enclaveRupeeContribution", 0) or 0)
            new_enclave_rup = int(meta_rewards["total_earned_rupees"])
            delta_rup = max(0, new_enclave_rup - prev_enclave_rup)
            prev_balance = int(part.get("rupeeBalance", part.get("rupees", 0)) or 0)
            updated_balance = (
                prev_balance + delta_rup
                if prev_enclave_rup > 0
                else max(prev_balance, new_enclave_rup)
            )
            part["currency_code"] = "RUP"
            part["currencyCode"] = "RUP"
            part["enclaveTwinLiveState"] = live_state
            part["enclaveCitySummary"] = city_summary
            part["enclaveMetaRewards"] = meta_rewards
            part["enclaveRupeeContribution"] = max(prev_enclave_rup, new_enclave_rup)
            part["rupeeBalance"] = max(prev_balance, updated_balance)
            part["cmyGemTiers"] = list(OASIS_CMY_RUPEE_GEM_TIERS)
            part["updated_at_iso"] = now_iso
            return part

        bridge_doc = bridge_lock_mod.update_asset_bridge(
            _enclave_crdt_patch,
            account_binding_id=account_binding_id,
            privacy_generation=int(privacy_generation),
            bridge_path=resolved_bridge_path,
        )
        # Ensure top-level Enclave summary & dual currency fields are persisted alongside CRDT union sets
        with lock_path.open("a+", encoding="utf-8") as lock_fh:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
            try:
                part_state = (bridge_doc.get("partitions") or {}).get(partition_key, {})
                bridge_doc["updated_at_iso"] = now_iso
                bridge_doc["currency_code"] = "RUP"
                bridge_doc["currencyCode"] = "RUP"
                bridge_doc["enclaveTwinLiveState"] = live_state
                bridge_doc["enclaveCitySummary"] = city_summary
                bridge_doc["enclaveMetaRewards"] = meta_rewards
                bridge_doc["enclaveRupeeContribution"] = int(
                    part_state.get("enclaveRupeeContribution", meta_rewards["total_earned_rupees"])
                )
                bridge_doc["cmyGemTiers"] = list(OASIS_CMY_RUPEE_GEM_TIERS)
                _atomic_write_json(resolved_bridge_path, bridge_doc)
            finally:
                fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
    else:
        with lock_path.open("a+", encoding="utf-8") as lock_fh:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
            try:
                bridge_data: dict[str, Any] = {}
                if resolved_bridge_path.is_file():
                    try:
                        loaded = json.loads(resolved_bridge_path.read_text(encoding="utf-8"))
                        if isinstance(loaded, dict):
                            bridge_data = loaded
                    except Exception:
                        bridge_data = {}

                bridge_data.setdefault("schema", "lfs-local-abac-v1")
                bridge_data["updated_at_iso"] = now_iso
                bridge_data["currency_code"] = "RUP"
                bridge_data["currencyCode"] = "RUP"
                bridge_data["enclaveTwinLiveState"] = live_state
                bridge_data["enclaveCitySummary"] = city_summary
                bridge_data["enclaveMetaRewards"] = meta_rewards

                prev_enclave_rup = int(bridge_data.get("enclaveRupeeContribution", 0) or 0)
                new_enclave_rup = int(meta_rewards["total_earned_rupees"])
                delta_rup = max(0, new_enclave_rup - prev_enclave_rup)
                prev_balance = int(bridge_data.get("rupeeBalance", bridge_data.get("rupees", 0)) or 0)
                updated_balance = prev_balance + delta_rup if prev_enclave_rup > 0 else max(prev_balance, new_enclave_rup)
                bridge_data["enclaveRupeeContribution"] = max(prev_enclave_rup, new_enclave_rup)
                bridge_data["rupeeBalance"] = updated_balance
                bridge_data["cmyGemTiers"] = list(OASIS_CMY_RUPEE_GEM_TIERS)

                partitions = bridge_data.setdefault("partitions", {})
                part = partitions.setdefault(
                    partition_key,
                    {
                        "accountBindingId": account_binding_id,
                        "privacyGeneration": int(privacy_generation),
                        "ownedItemIds": [],
                        "unlockedItemIds": [],
                        "rupeeBalance": 0,
                    },
                )
                part["currency_code"] = "RUP"
                part["currencyCode"] = "RUP"
                part["enclaveTwinLiveState"] = live_state
                part["enclaveCitySummary"] = city_summary
                part["enclaveMetaRewards"] = meta_rewards
                part["rupeeBalance"] = max(int(part.get("rupeeBalance", 0) or 0), updated_balance)
                part["updated_at_iso"] = now_iso

                _atomic_write_json(resolved_bridge_path, bridge_data)
            finally:
                fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)

    return {
        "saved_files": copied_files,
        "save_dir": str(resolved_save_dir),
        "lineage_path": str(lineage_path),
        "bridge_path": str(resolved_bridge_path),
        "lineage": lineage_payload,
        "meta_rewards": meta_rewards,
        "enclave_city_summary": city_summary,
        "enclave_twin_live_state": live_state,
    }
