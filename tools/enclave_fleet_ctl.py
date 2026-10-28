#!/usr/bin/env python3
"""Unified 300-Session Rolling-Window Fleet Controller & Standby Launch Manager (`enclave_fleet_ctl.py`).

Manages:
1. Standby Launch Gate (`--status`, `--standby`, `--arm-launch`):
   - Default state is `STANDBY` (`ops/config.json`: `"enabled": false`, `"launch_state": "STANDBY"`).
   - While on `STANDBY`, `--tick` and `--reap` perform a zero-cost health/heartbeat update and exit 0
     without consuming any Google Jules sessions.
   - Single command (`python3 tools/enclave_fleet_ctl.py --arm-launch`) arms the 36-wave / 300-session
     rolling-window fleet; `--standby` disarms it immediately.
2. Cross-Fleet 300-Session Rolling-Window Token Bucket (`${XDG_STATE_HOME:-$HOME/.local/state}/lfs-jules-fleet/rolling_budget_300.json`):
   - Coordinates `enclave-digital-twin`, `lfs-tycoon-factory` (`StrataPaper`), `lfs-trasharcade-factory`,
     and `willow-guild-factory` across the Google Jules Ultra 300-session rolling 24h window and 60-concurrent-VM ceiling.
3. Lightweight Self-Hosted Local AI Context-Aware Managers (`aegis-ollama.service` @ `127.0.0.1:11434`):
   - `qwen3.5:4b-q4_K_M`: Judge & Tactician ($T=0.05$, LPI gate, DC calculation, CALYPSO rule).
   - `gemma4:e4b-it-q4_K_M`: Showrunner Context Steward ($T=0.35$, Mulligan "Toys, Not Plots" & Mercer 5-sense).
   - `qwen2.5-coder:3b-instruct-q4_K_M`: 5-Section Task Card compiler & sanitized F-120 feedback resolver.
4. Systemd Unit Installation & Verification (`--install-systemd`):
   - Installs `lfs-enclave-factory.{service,timer}` (36 waves/24h at +08/+48/+28) and
     `lfs-enclave-reaper.{service,timer}` (every 5m at :03/5) into `~/.config/systemd/user/`.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.local_ai_manager import (
    JUDGE_TACTICIAN_MODEL,
    SHOWRUNNER_STEWARD_MODEL,
    TASK_CARD_COMPILER_MODEL,
    LocalContextAwareManager,
)
from tools.jules_enclave_dispatcher import (
    AUTO_RETRY_RESERVE_CAP,
    HARD_DISPATCH_CEILING_24H,
    PLAN_CEILING_24H,
    ROLLING_SAFETY_BUFFER,
    SCHEDULED_PRODUCTIVE_CAP,
    JulesEnclaveDispatcher,
    default_budget_state,
)


def _xdg_state_home() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state"))


SHARED_FLEET_STATE_DIR = _xdg_state_home() / "lfs-jules-fleet"
SHARED_FLEET_BUDGET_FILE = SHARED_FLEET_STATE_DIR / "rolling_budget_300.json"
ENCLAVE_RUNTIME_STATE_DIR = _xdg_state_home() / "lfs-enclave-factory"
TYCOON_STATE_FILE = _xdg_state_home() / "lfs-tycoon-factory" / "state.json"
TRASHARCADE_STATE_FILE = _xdg_state_home() / "lfs-trasharcade-factory" / "state.json"
WILLOW_GUILD_STATE_FILE = _xdg_state_home() / "lfs-willow-guild-factory" / "state.json"
SYSTEMD_USER_DIR = Path.home() / ".config" / "systemd" / "user"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_runtime_budget_file(repo_root: Path = REPO_ROOT) -> Path:
    """Resolve the externalized runtime budget state path (`$XDG_STATE_HOME/lfs-enclave-factory/budget.json`).

    Seeds from `ops/budget.json` if absent so the git working tree (`ops/budget.json`) remains 100% clean.
    """
    resolved_root = Path(repo_root).resolve()
    if resolved_root != REPO_ROOT:
        return resolved_root / "ops" / "budget.json"
    state_dir = _xdg_state_home() / "lfs-enclave-factory"
    runtime_budget = state_dir / "budget.json"
    if not runtime_budget.is_file():
        try:
            state_dir.mkdir(parents=True, exist_ok=True)
            seed_file = resolved_root / "ops" / "budget.json"
            if seed_file.is_file():
                shutil.copy2(str(seed_file), str(runtime_budget))
            else:
                runtime_budget.write_text(
                    json.dumps(default_budget_state(), indent=2) + "\n",
                    encoding="utf-8",
                )
        except OSError:
            return resolved_root / "ops" / "budget.json"
    return runtime_budget


def _count_factory_sessions_24h(state_path: Path, now_dt: datetime) -> dict[str, int]:
    """Count sessions created in the last 24h and currently in-flight for a peer factory."""
    if not state_path.is_file():
        return {"dispatched_24h": 0, "in_flight": 0}
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return {"dispatched_24h": 0, "in_flight": 0}

    cutoff = now_dt - timedelta(hours=24)
    dispatched_24h = 0
    in_flight = 0
    for rec in (data.get("sessions") or {}).values():
        if not isinstance(rec, dict):
            continue
        if rec.get("outcome") is None:
            in_flight += 1
        created_str = str(rec.get("created_at") or rec.get("created") or rec.get("dispatched_at_iso") or "")
        if created_str:
            try:
                c_str = created_str[:-1] + "+00:00" if created_str.endswith("Z") else created_str
                c_dt = datetime.fromisoformat(c_str)
                if c_dt.tzinfo is None:
                    c_dt = c_dt.replace(tzinfo=timezone.utc)
                if c_dt >= cutoff:
                    dispatched_24h += 1
            except Exception:
                pass
    return {"dispatched_24h": dispatched_24h, "in_flight": in_flight}


def compute_cross_fleet_rolling_telemetry(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Compute unified 300-session rolling-24h telemetry across Enclave, LFS-Tycoon, LFS_TrashArcade, and Willow Guild."""
    now_iso = _utc_now_iso()
    now_dt = datetime.now(timezone.utc)
    runtime_budget = _resolve_runtime_budget_file(repo_root)
    dispatcher = JulesEnclaveDispatcher(repo_root=repo_root, budget_file=runtime_budget, dry_run=True)
    local_mgr = LocalContextAwareManager(repo_root=repo_root)

    enclave_budget = dispatcher.load_budget(now_iso=now_iso)
    standby_guard = dispatcher.check_standby_or_paused()
    sympathy = local_mgr.evaluate_hardware_sympathy()

    state_home = _xdg_state_home()
    tycoon_stats = _count_factory_sessions_24h(state_home / "lfs-tycoon-factory" / "state.json", now_dt)
    arcade_stats = _count_factory_sessions_24h(state_home / "lfs-trasharcade-factory" / "state.json", now_dt)
    willow_stats = _count_factory_sessions_24h(state_home / "lfs-willow-guild-factory" / "state.json", now_dt)
    enclave_live_24h = sum(
        1
        for e in (enclave_budget.get("session_ledger_24h") or [])
        if isinstance(e, dict) and str(e.get("state") or "") != "COMPLETED_DRY_RUN"
    )
    enclave_dryrun_24h = int(enclave_budget.get("rolling_24h_dispatched", 0))

    total_live_24h = (
        enclave_live_24h
        + tycoon_stats["dispatched_24h"]
        + arcade_stats["dispatched_24h"]
        + willow_stats["dispatched_24h"]
    )
    total_in_flight = (
        len(enclave_budget.get("active_sessions") or [])
        + tycoon_stats["in_flight"]
        + arcade_stats["in_flight"]
        + willow_stats["in_flight"]
    )

    payload = {
        "schema_version": "lfs_jules_fleet_rolling_300_v2.0.0",
        "updated_at_iso": now_iso,
        "plan_ceiling_rolling_24h": PLAN_CEILING_24H,
        "hard_dispatch_ceiling_24h": HARD_DISPATCH_CEILING_24H,
        "ultra_concurrent_vm_cap": 60,
        "enclave_launch_state": standby_guard["launch_state"],
        "enclave_enabled": standby_guard["enabled"],
        "fleet_mode": standby_guard["fleet_mode"],
        "standby_reasons": standby_guard["reasons"],
        "cross_fleet_rolling_24h": {
            "factories_tracked": [
                "enclave-digital-twin",
                "lfs-tycoon-factory",
                "lfs-trasharcade-factory",
                "willow-guild-factory",
            ],
            "enclave_live_dispatched_24h": enclave_live_24h,
            "enclave_dry_run_simulated_24h": enclave_dryrun_24h,
            "lfs_tycoon_dispatched_24h": tycoon_stats["dispatched_24h"],
            "lfs_trasharcade_dispatched_24h": arcade_stats["dispatched_24h"],
            "willow_guild_dispatched_24h": willow_stats["dispatched_24h"],
            "total_live_dispatched_24h": total_live_24h,
            "remaining_hard_ceiling_24h": max(0, HARD_DISPATCH_CEILING_24H - total_live_24h),
            "remaining_plan_ceiling_24h": max(0, PLAN_CEILING_24H - total_live_24h),
            "total_in_flight_vms": total_in_flight,
            "available_concurrent_vm_slots": max(0, 60 - total_in_flight),
            "next_enclave_slot_reclaim_at_iso": enclave_budget.get("next_slot_reclaim_at_iso", now_iso),
        },
        "enclave_300_session_allocation": {
            "scheduled_productive_cap_24h": SCHEDULED_PRODUCTIVE_CAP,
            "auto_retry_reserve_cap_24h": AUTO_RETRY_RESERVE_CAP,
            "rolling_safety_buffer_24h": ROLLING_SAFETY_BUFFER,
            "waves_per_24h": 36,
            "inter_wave_spacing_minutes": 40,
            "phase_shift_schedule": "Even hours :08,:48 | Odd hours :28 (zero collision with :00/:15/:30/:45)",
        },
        "local_ai_infrastructure_pipeline": {
            "ollama_service": "aegis-ollama.service (127.0.0.1:11434)",
            "judge_tactician_model": JUDGE_TACTICIAN_MODEL,
            "showrunner_steward_model": SHOWRUNNER_STEWARD_MODEL,
            "task_card_compiler_model": TASK_CARD_COMPILER_MODEL,
            "hardware_sympathy": sympathy,
        },
    }

    try:
        fleet_dir = _xdg_state_home() / "lfs-jules-fleet"
        fleet_dir.mkdir(parents=True, exist_ok=True)
        (fleet_dir / "rolling_budget_300.json").write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass

    return payload


def set_launch_state(
    repo_root: Path,
    arm: bool,
    fleet_mode: str | None = None,
) -> dict[str, Any]:
    """Arm (`LAUNCHED` / `ARMED`) or disarm (`STANDBY`) the Enclave fleet in externalized runtime config."""
    os.environ["LFS_ENCLAVE_RUNTIME_CONFIG"] = "1"
    resolved_root = Path(repo_root).resolve()
    cfg_path = (
        (_xdg_state_home() / "lfs-enclave-factory" / "config.json")
        if resolved_root == REPO_ROOT
        else (resolved_root / "ops" / "config.json")
    )
    dispatcher = JulesEnclaveDispatcher(repo_root=repo_root, dry_run=True)
    cfg = dispatcher.load_config()
    cfg["enabled"] = bool(arm)
    cfg["launch_state"] = "ARMED" if arm else "STANDBY"
    if fleet_mode in ("UNIFIED_FLEET", "ENCLAVE_DEDICATED_300"):
        cfg["fleet_mode"] = fleet_mode
    cfg["unified_4fleet_allocation_24h"] = {
        "enclave_digital_twin": 96,
        "lfs_trash_arcade": 72,
        "lfs_tycoon": 48,
        "willow_guild": 24,
        "scheduled_total_24h": 240,
        "auto_retry_reserve_24h": 30,
        "hard_ceiling_24h": 270,
        "safety_buffer_24h": 30,
        "plan_ceiling_24h": 300,
    }
    cfg["updated_at_iso"] = _utc_now_iso()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    telemetry = compute_cross_fleet_rolling_telemetry(repo_root=repo_root)
    return {
        "action": "ARMED_FOR_LAUNCH" if arm else "SET_TO_STANDBY",
        "enabled": cfg["enabled"],
        "launch_state": cfg["launch_state"],
        "fleet_mode": cfg.get("fleet_mode", "UNIFIED_FLEET"),
        "config_path": str(cfg_path),
        "updated_at_iso": cfg["updated_at_iso"],
        "telemetry": telemetry["cross_fleet_rolling_24h"],
    }


def install_systemd_units(repo_root: Path = REPO_ROOT, enable_timers: bool = True) -> dict[str, Any]:
    """Install `lfs-enclave-factory.{service,timer}` and `lfs-enclave-reaper.{service,timer}` into `~/.config/systemd/user/`."""
    src_dir = repo_root / "ops" / "systemd"
    SYSTEMD_USER_DIR.mkdir(parents=True, exist_ok=True)
    installed: list[str] = []
    for unit_name in (
        "lfs-enclave-factory.service",
        "lfs-enclave-factory.timer",
        "lfs-enclave-reaper.service",
        "lfs-enclave-reaper.timer",
    ):
        src = src_dir / unit_name
        dst = SYSTEMD_USER_DIR / unit_name
        if src.is_file():
            shutil.copy2(str(src), str(dst))
            installed.append(unit_name)

    daemon_reloaded = False
    timers_enabled: list[str] = []
    try:
        res = subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            capture_output=True,
            text=True,
            timeout=5.0,
            check=False,
        )
        daemon_reloaded = res.returncode == 0
        if enable_timers:
            for t_unit in ("lfs-enclave-factory.timer", "lfs-enclave-reaper.timer"):
                er = subprocess.run(
                    ["systemctl", "--user", "enable", "--now", t_unit],
                    capture_output=True,
                    text=True,
                    timeout=5.0,
                    check=False,
                )
                if er.returncode == 0:
                    timers_enabled.append(t_unit)
    except (OSError, subprocess.SubprocessError):
        pass

    return {
        "installed_units": installed,
        "systemd_user_dir": str(SYSTEMD_USER_DIR),
        "daemon_reloaded": daemon_reloaded,
        "timers_enabled_on_standby_gate": timers_enabled,
    }


def run_wave_tick(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Execute a wave tick (no-op heartbeat when on `STANDBY`)."""
    runtime_budget = _resolve_runtime_budget_file(repo_root)
    guard_dispatcher = JulesEnclaveDispatcher(repo_root=repo_root, budget_file=runtime_budget, dry_run=True)
    standby = guard_dispatcher.check_standby_or_paused()
    telemetry = compute_cross_fleet_rolling_telemetry(repo_root=repo_root)
    if standby["standby_or_paused"]:
        return {
            "status": "STANDBY_NOOP",
            "launch_state": standby["launch_state"],
            "enabled": standby["enabled"],
            "reasons": standby["reasons"],
            "sessions_dispatched": 0,
            "cross_fleet_rolling_24h": telemetry["cross_fleet_rolling_24h"],
        }

    # Determine current wave index from UTC hour/minute
    live_dispatcher = JulesEnclaveDispatcher(
        repo_root=repo_root,
        budget_file=runtime_budget,
        dry_run=False,
    )
    now_dt = datetime.now(timezone.utc)
    minute_of_day = now_dt.hour * 60 + now_dt.minute
    wave_idx = (minute_of_day // 60) % 24 + 1
    tick_id = ((wave_idx - 1) // 6) * 4 + ((wave_idx - 1) % 4) + 1
    res = live_dispatcher.dispatch_tick_sessions(tick_id=tick_id, persist=True)
    return {
        "status": "WAVE_DISPATCHED",
        "wave_index_1_to_24": wave_idx,
        "dispatch_result": res,
    }


def run_reaper_tick(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Execute the 5-minute F-120 stalled-session reaper (no-op heartbeat when on `STANDBY`)."""
    runtime_budget = _resolve_runtime_budget_file(repo_root)
    guard_dispatcher = JulesEnclaveDispatcher(repo_root=repo_root, budget_file=runtime_budget, dry_run=True)
    standby = guard_dispatcher.check_standby_or_paused()
    telemetry = compute_cross_fleet_rolling_telemetry(repo_root=repo_root)
    if standby["standby_or_paused"]:
        return {
            "status": "STANDBY_REAPER_HEARTBEAT",
            "launch_state": standby["launch_state"],
            "enabled": standby["enabled"],
            "reasons": standby["reasons"],
            "cross_fleet_rolling_24h": telemetry["cross_fleet_rolling_24h"],
        }
    live_dispatcher = JulesEnclaveDispatcher(
        repo_root=repo_root,
        budget_file=runtime_budget,
        dry_run=False,
    )
    return live_dispatcher.reap_stalled_sessions(persist=True)


def main(argv: list[str] | None = None) -> int:
    os.environ.setdefault("LFS_ENCLAVE_RUNTIME_CONFIG", "1")
    parser = argparse.ArgumentParser(
        description="Enclave of the 16 — 300-Session Rolling-Window Fleet Controller & Standby Manager."
    )
    parser.add_argument("--status", action="store_true", help="Show cross-fleet 300-session rolling-window & standby status.")
    parser.add_argument("--dry-run-24h", action="store_true", help="Simulate all 36 waves (300-session 24h plan) offline.")
    parser.add_argument("--tick", action="store_true", help="Execute wave tick (standby-gated).")
    parser.add_argument("--reap", action="store_true", help="Execute 5-minute F-120 stalled-session reaper (standby-gated).")
    parser.add_argument("--arm-launch", action="store_true", help="Arm the Enclave fleet for live launch.")
    parser.add_argument("--standby", action="store_true", help="Place the Enclave fleet on STANDBY (enabled=false).")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["UNIFIED_FLEET", "ENCLAVE_DEDICATED_300"],
        default=None,
        help="Optional fleet operating mode override.",
    )
    parser.add_argument("--install-systemd", action="store_true", help="Install systemd user timer/service units.")
    parser.add_argument("--repo-root", type=str, default=None, help="Repository root override.")
    args = parser.parse_args(argv)

    root = Path(args.repo_root).resolve() if args.repo_root else REPO_ROOT

    if args.install_systemd:
        res = install_systemd_units(repo_root=root, enable_timers=True)
        print(json.dumps(res, indent=2))
        return 0

    if args.arm_launch:
        res = set_launch_state(repo_root=root, arm=True, fleet_mode=args.mode)
        print(json.dumps(res, indent=2))
        return 0

    if args.standby:
        res = set_launch_state(repo_root=root, arm=False, fleet_mode=args.mode)
        print(json.dumps(res, indent=2))
        return 0

    if args.dry_run_24h:
        dispatcher = JulesEnclaveDispatcher(repo_root=root, dry_run=True)
        res = dispatcher.simulate_24h_300_session_plan()
        print(json.dumps(res, indent=2))
        return 0 if res.get("valid_300_session_plan") else 1

    if args.tick:
        res = run_wave_tick(repo_root=root)
        print(json.dumps(res, indent=2))
        return 0

    if args.reap:
        res = run_reaper_tick(repo_root=root)
        print(json.dumps(res, indent=2))
        return 0

    telemetry = compute_cross_fleet_rolling_telemetry(repo_root=root)
    print(json.dumps(telemetry, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
