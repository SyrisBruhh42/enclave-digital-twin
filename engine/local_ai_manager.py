"""Lightweight Self-Hosted Local AI Context-Aware Manager (`engine/local_ai_manager.py`).

Aligns `enclave-digital-twin` with the LFS Aegis Local AI + 100% Google Jules Pipeline:
1. Zero External Paid LLM APIs:
   - All cloud execution runs 100% on Google Jules Cloud VMs (`jules.googleapis.com/v1alpha/sessions`).
   - All local pre-dispatch compilation, Showrunner Judge & Tactician evaluation ($T=0.05$),
     "Toys, Not Plots" reactive entity stewardship ($T=0.35$), and stalled-session feedback
     triage ($T=0.10$) run on the lightweight self-hosted `aegis-ollama.service` (`127.0.0.1:11434`)
     with deterministic offline fallback.
2. Installed Local Models (`aegis-ollama.service`):
   - `qwen3.5:4b-q4_K_M` (3.3 GB): Judge & Tactician (DC calculation, 4-tier graduated roll outcomes,
     LPI gate audit, and `CALYPSO` zero-raw-stat-numbers verification).
   - `gemma4:e4b-it-q4_K_M` (6.6 GB): Showrunner Context Steward (Mulligan "Toys, Not Plots",
     Mercer 5-sense interactive features, and "3 Levels of Why").
   - `qwen2.5-coder:3b-instruct-q4_K_M` (1.9 GB): 5-Section Aegis Jules Task Card compiler,
     6-stage sanitized feedback responder, and declarative EAV failure-lesson formatter.
3. Hardware Sympathy & Zero-Raw-Secret Vault Integration:
   - Directly links with `core/companion/clients/linux/aegis_brain.py`
     (`HardwareSympathyGuard`, `CapabilityVaultBridge`, `UnifiedQwenJulesBrain`, `sanitize_untrusted_text`,
     `format_eav_lesson`) when present on the workstation, with built-in standalone equivalents for CI.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys
import unicodedata
import urllib.error
import urllib.request
from typing import Any

from engine.drama_director import (
    build_showrunner_scene_ledger,
    compute_living_playability_index,
)

OLLAMA_ENDPOINT = "http://127.0.0.1:11434/api/generate"
JUDGE_TACTICIAN_MODEL = "qwen3.5:4b-q4_K_M"
SHOWRUNNER_STEWARD_MODEL = "gemma4:e4b-it-q4_K_M"
TASK_CARD_COMPILER_MODEL = "qwen2.5-coder:3b-instruct-q4_K_M"

# Optional direct link to workstation `aegis_brain.py`
_DEFAULT_U3_ROOT = Path(
    os.environ.get("LFS_AEGIS_LINUX_ROOT")
    or (
        Path(os.environ["LFS_SUITE_ROOT"]) / "3-lfs-aegis-linux"
        if os.environ.get("LFS_SUITE_ROOT")
        else (
            Path(__file__).resolve().parents[3]
            if len(Path(__file__).resolve().parents) > 3
            else Path(__file__).resolve().parents[1]
        )
    )
)
AEGIS_LINUX_CLIENT_DIR = _DEFAULT_U3_ROOT / "core" / "companion" / "clients" / "linux"
_aegis_brain: Any = None
if AEGIS_LINUX_CLIENT_DIR.is_dir():
    if str(AEGIS_LINUX_CLIENT_DIR) not in sys.path:
        sys.path.insert(0, str(AEGIS_LINUX_CLIENT_DIR))
    try:
        import aegis_brain as _imported_aegis_brain  # type: ignore[import-not-found]

        _aegis_brain = _imported_aegis_brain
    except Exception:
        _aegis_brain = None

# CALYPSO Rule: Detect leaked raw mechanical stat assignments in narrative prose
CALYPSO_RAW_STAT_RE = re.compile(
    r"\b(?:AC\s*[:=]\s*\d+|HP\s*[:=]\s*\d+|DC\s*[:=]\s*\d+|STR\s*[:=]\s*\d+|"
    r"DEX\s*[:=]\s*\d+|CON\s*[:=]\s*\d+|INT\s*[:=]\s*\d+|WIS\s*[:=]\s*\d+|"
    r"CHA\s*[:=]\s*\d+|hit\s+points\s+remaining\s*[:=]\s*\d+|\+\d+\s+to\s+hit)\b",
    re.IGNORECASE,
)


def sanitize_untrusted_text(raw: str, source_hash: str = "") -> str:
    """6-Stage Deterministic Pre-LLM Sanitizer (delegates to aegis_brain when present)."""
    if _aegis_brain is not None and hasattr(_aegis_brain, "sanitize_untrusted_text"):
        return str(_aegis_brain.sanitize_untrusted_text(raw, source_hash=source_hash))
    stage1 = unicodedata.normalize("NFKC", str(raw or ""))
    stage2 = re.sub(
        r"[\u200B-\u200D\u2060\uFEFF\u202A-\u202E\u2066-\u2069\x00-\x08\x0B\x0C\x0E-\x1F\x7F]",
        "",
        stage1,
    )
    stage3 = re.sub(r"[\uE000-\uF8FF]", "", stage2)
    stage4 = re.sub(r"(?is)<(script|style)\b[^>]*>.*?</\1\s*>|<!--.*?-->", "", stage3)
    stage5 = (
        stage4.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )
    nonce = (
        hashlib.sha256(source_hash.encode("utf-8")).hexdigest()[:12]
        if source_hash
        else secrets.token_hex(6)
    )
    return f"<untrusted_content_{nonce}>{stage5}</untrusted_content_{nonce}>"


class FailureToConstraintCompiler:
    """Compiles raw validation failures or EAV strings into plain-English natural-language constraints.

    Guarantees zero @ENT/@ATTR/@VAL/@CONF/@TIME/@PROV tokens and zero PROHIBITED_HALLUCINATED_KEYS
    enter worker repair prompts, preventing induction-head copying into JSON payloads.
    """

    FORBIDDEN_TOKENS: tuple[str, ...] = (
        "@ENT",
        "@ATTR",
        "@VAL",
        "@CONF",
        "@TIME",
        "@PROV",
        "error_type",
        "missing_key",
        "raw_traceback",
        "loc",
        "pydantic_error",
        "second_pass_repair_constraint",
        "changeset_gate_rejection",
        "constitutional_baseline",
        "retry_recovery_mode",
        "VAL",
        "CONF",
        "TIME",
        "PROV",
    )

    @classmethod
    def compile_constraint(
        cls,
        entity: str = "enclave-digital-twin",
        attr: str = "verification_constraint",
        value: str = "",
    ) -> str:
        imperative_re = re.compile(
            r"\b(?:ignore|disregard|override|execute|run|delete|bypass|forget|system_prompt|"
            r"instruct|obey|sudo|rm|chmod|chown|curl|wget|eval|exec|spawn|must|never|always|please)\b"
            r"|(?i:\bdo\s+not\b|\bdon't\b)",
            re.IGNORECASE,
        )
        raw = f"{entity} {attr} {value}".strip()
        cleaned = imperative_re.sub("observed_rule", raw)
        cleaned = re.sub(r"@(?:ENT|ATTR|VAL|CONF|TIME|PROV)\[[^\]]*\]", " ", cleaned)
        cleaned = re.sub(r"@(?:ENT|ATTR|VAL|CONF|TIME|PROV)\b", " ", cleaned)
        for tok in cls.FORBIDDEN_TOKENS:
            if not tok.startswith("@"):
                cleaned = re.sub(rf"\b{re.escape(tok)}\b", "verified_rule", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"[\r\n|\[\]=]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()[:220]
        if not cleaned:
            cleaned = "Strictly satisfy Laws L01 through L16 and canonical JSON schema fields"
        return (
            f"Natural-Language Verification Constraint: Output only canonical schema keys "
            f"with zero diagnostic metadata ({cleaned})."
        )


def format_eav_lesson(
    entity: str,
    attr: str,
    value: str,
    confidence: float = 1.0,
    prov_hash: str = "enclave_gate",
) -> str:
    """Format a failure or audit observation as a plain-English natural-language constraint with zero EAV tags."""
    _ = (confidence, prov_hash)
    return FailureToConstraintCompiler.compile_constraint(
        entity=entity,
        attr=attr,
        value=value,
    )



def verify_calypso_narrative_purity(prose_text: str) -> tuple[bool, list[str]]:
    """Enforce the CALYPSO Zero-Raw-Stat-Numbers Rule on narrative prose."""
    errors: list[str] = []
    if not prose_text:
        return True, errors
    for match in CALYPSO_RAW_STAT_RE.finditer(prose_text):
        errors.append(
            f"CALYPSO violation: raw mechanical stat token '{match.group(0)}' leaked into narrative prose."
        )
    return len(errors) == 0, errors


class LocalContextAwareManager:
    """Self-hosted context-aware manager uniting `aegis-ollama.service` and `UnifiedQwenJulesBrain`."""

    def __init__(self, repo_root: Path | str | None = None) -> None:
        self.repo_root = Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parent.parent
        self.sympathy_guard = (
            _aegis_brain.HardwareSympathyGuard()
            if (_aegis_brain is not None and hasattr(_aegis_brain, "HardwareSympathyGuard"))
            else None
        )
        self.vault = (
            _aegis_brain.CapabilityVaultBridge()
            if (_aegis_brain is not None and hasattr(_aegis_brain, "CapabilityVaultBridge"))
            else None
        )
        self.qwen_brain = (
            _aegis_brain.UnifiedQwenJulesBrain(sympathy_guard=self.sympathy_guard, vault_bridge=self.vault)
            if (_aegis_brain is not None and hasattr(_aegis_brain, "UnifiedQwenJulesBrain"))
            else None
        )

    def evaluate_hardware_sympathy(self, evict_vram_on_yield: bool = True) -> dict[str, Any]:
        """Return workstation thermal/PSI/workload sympathy status before invoking local Ollama."""
        if self.sympathy_guard is not None:
            try:
                return dict(
                    self.sympathy_guard.evaluate_dispatch_sympathy(
                        evict_vram_on_yield=evict_vram_on_yield
                    )
                )
            except Exception:
                pass
        return {
            "allowed": True,
            "mode": "GPU_BURST_SYMPATHETIC",
            "recommended_model": TASK_CARD_COMPILER_MODEL,
            "judge_model": JUDGE_TACTICIAN_MODEL,
            "steward_model": SHOWRUNNER_STEWARD_MODEL,
            "keep_alive": "180s",
            "evict_vram_on_yield": evict_vram_on_yield,
            "priority_multiplier": int(os.environ.get("LFS_PRIORITY_MULTIPLIER", "10000")),
            "bypass_mode": os.environ.get("LFS_BYPASS_MODE", "MODE_FAIR_SHARE"),
            "cpu_temp_c": 45.0,
            "load_1m": 1.0,
            "active_heavy_workloads": [],
        }

    def query_local_ollama(
        self,
        prompt: str,
        model: str = TASK_CARD_COMPILER_MODEL,
        temperature: float = 0.1,
        max_tokens: int = 96,
        timeout_sec: float = 12.0,
    ) -> dict[str, Any]:
        """Execute a bounded loopback inference against `127.0.0.1:11434` (`aegis-ollama.service`).

        Never contacts external hosts, never pulls models, and respects HardwareSympathyGuard.
        """
        sympathy = self.evaluate_hardware_sympathy()
        if not sympathy.get("allowed", False):
            return {
                "ok": False,
                "model": model,
                "response": "",
                "fallback_reason": sympathy.get("reason", "hardware_sympathy_yield"),
                "sympathy": sympathy,
            }

        req_body = json.dumps(
            {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "keep_alive": sympathy.get("keep_alive", "180s"),
                "options": {
                    "num_ctx": 1536,
                    "num_predict": max(16, min(512, int(max_tokens))),
                    "num_thread": 8,
                    "temperature": float(temperature),
                },
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            OLLAMA_ENDPOINT,
            data=req_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                payload = json.loads(resp.read(131072))
                text = str(payload.get("response") or "").strip()
                if text:
                    return {
                        "ok": True,
                        "model": model,
                        "response": text,
                        "fallback_reason": None,
                        "sympathy": sympathy,
                    }
        except (OSError, ValueError, urllib.error.URLError) as exc:
            return {
                "ok": False,
                "model": model,
                "response": "",
                "fallback_reason": f"ollama_unreachable_or_deferred:{type(exc).__name__}",
                "sympathy": sympathy,
            }
        return {
            "ok": False,
            "model": model,
            "response": "",
            "fallback_reason": "empty_response",
            "sympathy": sympathy,
        }

    def run_judge_and_tactician_audit(
        self,
        colony_sol: int,
        day_phase: str,
        pacing_state: str,
        scene_archetype: str,
        science_vegetable: str,
        tension_score: float,
        recent_events: list[dict[str, Any]] | None = None,
        candidate_prose: str = "",
        use_local_ollama: bool = False,
    ) -> dict[str, Any]:
        """Run the Dual-Agent Judge & Tactician ($T=0.05$) audit on a scene or proposal.

        1. Builds the `JulesDM_CampaignStateLedger` slice.
        2. Evaluates the Living Playability Index (LPI in [0, 1]) and rejects 'Unplayable Draft' (< 0.45).
        3. Enforces the CALYPSO Zero-Raw-Stat-Numbers rule on `candidate_prose`.
        4. Optionally queries `qwen3.5:4b-q4_K_M` on local Ollama for a tactical DC note.
        """
        ledger = build_showrunner_scene_ledger(
            colony_sol=colony_sol,
            day_phase=day_phase,
            pacing_state=pacing_state,
            scene_archetype=scene_archetype,
            science_vegetable=science_vegetable,
            tension_score=tension_score,
            recent_events=recent_events,
        )
        lpi = ledger["lpi_metrics"]
        calypso_ok, calypso_errors = verify_calypso_narrative_purity(candidate_prose)
        lpi_ok = lpi["classification"] != "Unplayable Draft" and float(lpi["composite_lpi"]) >= 0.45

        tactical_note = (
            f"Pacing={ledger['campaign_metadata']['pacing_mode']} | "
            f"Pre-Roll DC={ledger['dual_agent_contract']['judge_tactician']['explicit_pre_roll_dc']} | "
            f"LPI={lpi['composite_lpi']:.2f} ({lpi['classification']})"
        )
        model_used = f"{JUDGE_TACTICIAN_MODEL} (deterministic-symbolic-judge)"
        if use_local_ollama:
            llm_res = self.query_local_ollama(
                prompt=(
                    f"As Judge & Tactician (T=0.05), state 1 concise tactical adjudication rule for "
                    f"Sol {colony_sol} {day_phase} ({scene_archetype}, DC "
                    f"{ledger['dual_agent_contract']['judge_tactician']['explicit_pre_roll_dc']}): "
                    f"{science_vegetable}"
                ),
                model=JUDGE_TACTICIAN_MODEL,
                temperature=0.05,
                max_tokens=64,
            )
            if llm_res["ok"]:
                tactical_note = " ".join(llm_res["response"].splitlines())[:280]
                model_used = JUDGE_TACTICIAN_MODEL

        return {
            "passed": lpi_ok and calypso_ok,
            "lpi_ok": lpi_ok,
            "calypso_ok": calypso_ok,
            "calypso_errors": calypso_errors,
            "lpi_metrics": lpi,
            "pacing_mode": ledger["campaign_metadata"]["pacing_mode"],
            "judge_model": model_used,
            "tactical_note": tactical_note,
            "ledger": ledger,
        }

    def compile_enclave_5section_task_card(
        self,
        *,
        task_bucket: str,
        colony_sol: int,
        tick_id: int,
        day_phase: str,
        target_path: str,
        active_pov_id: str = "enclave_03_silas",
        next_pov_target: str = "enclave_01_hector",
        science_vegetable: str = "Magnetohydrodynamic Kelvin-Helmholtz shear across the ferrofluid sea",
        showrunner_pacing_mode: str = "MERCER_EXPLORATION",
        explicit_dc: int = 14,
        is_retry: bool = False,
        failure_lesson: str | None = None,
        use_local_ollama: bool = False,
    ) -> dict[str, Any]:
        """Compile an Aegis 5-Section Jules Task Card tailored for `enclave-digital-twin`.

        Strictly enforces:
        - Law L02 Single-File Append-Only creation (`target_path` only; zero M/D to `canon/`, `snapshots/`, `ops/`).
        - MCP Directives (`DO NOT call get_workspace on Linear`, `ENV[LINEAR_MCP]: {WORKSPACE_ENUM: NULL}`).
        - Showrunner DM Contract (`pacing_mode`, `CALYPSO` zero-raw-stat-numbers rule, Mercer 5-sense + 3 interactive
          features, Mulligan "Toys, Not Plots" & "3 Levels of Why", Murph Two-Fight Short-Rest Cadence).
        - Declarative EAV failure lessons (`@ENT | @ATTR | @CONF | @TIME | @PROV`).
        """
        sympathy = self.evaluate_hardware_sympathy()
        eav_records: list[str] = []
        if failure_lesson:
            eav_records.append(
                FailureToConstraintCompiler.compile_constraint(
                    entity=f"enclave-digital-twin:{task_bucket}",
                    attr="verification_constraint",
                    value=failure_lesson,
                )
            )
        if self.qwen_brain is not None:
            for item in self.qwen_brain.list_lessons("enclave-digital-twin")[:4]:
                eav_records.append(
                    FailureToConstraintCompiler.compile_constraint(
                        entity=f"enclave-digital-twin:{task_bucket}",
                        attr="verification_constraint",
                        value=str(item.get("eav", "")),
                    )
                )
        if not eav_records:
            eav_records.append(
                FailureToConstraintCompiler.compile_constraint(
                    entity=f"enclave-digital-twin:{task_bucket}",
                    attr="verification_baseline",
                    value="laws_L01_through_L16_and_calypso_verified",
                )
            )

        steward_note = (
            f"Pacing={showrunner_pacing_mode}; Pre-Roll DC={explicit_dc}; "
            f"Science Vegetable='{science_vegetable}'; Active POV={active_pov_id} -> Handoff={next_pov_target}."
        )
        model_used = "deterministic-enclave-5section-v2"
        if use_local_ollama:
            steward_res = self.query_local_ollama(
                prompt=(
                    f"Provide a 1-sentence Showrunner sensory & 'Toys, Not Plots' directive for "
                    f"{task_bucket} on Sol {colony_sol} ({day_phase}, mode={showrunner_pacing_mode}): "
                    f"{science_vegetable}"
                ),
                model=SHOWRUNNER_STEWARD_MODEL,
                temperature=0.35,
                max_tokens=64,
            )
            if steward_res["ok"]:
                steward_note = " ".join(steward_res["response"].splitlines())[:280]
                model_used = SHOWRUNNER_STEWARD_MODEL

        eav_block = "\n".join(f"- `{rec}`" for rec in eav_records)
        retry_banner = (
            f"\n- **Self-Repair Guidance**: Apply the natural-language verification constraints in Section 5 and output only canonical JSON schema keys.\n"
            if is_retry
            else ""
        )

        prompt_text = (
            f"# Aegis 5-Section Jules Task Card (enclave-digital-twin)\n\n"
            f"### Scope Boundary\n"
            f"- **Law L02 Append-Only Constraint**: Create strictly `1` new file at `{target_path}`.\n"
            f"- **Protected Paths (Zero M/D Allowed)**: `canon/`, `snapshots/`, `relationships/`, `ops/`, `engine/`, `tools/`.\n"
            f"- **Read-Only Context References**: `canon/schemas/world_state_v2.json`, "
            f"`canon/schemas/jules_dm_campaign_ledger.schema.json`, `canon/characters/{active_pov_id}.core.json`.\n\n"
            f"## 1. Objective\n"
            f"- **Task Bucket**: `{task_bucket}` (Colony Sol `{colony_sol}`, Tick `{tick_id}`, Phase `{day_phase}`)\n"
            f"- **Target Output File**: `{target_path}`\n"
            f"- **Showrunner Pacing Mode**: `{showrunner_pacing_mode}` (Explicit Pre-Roll Check DC: `{explicit_dc}`)\n"
            f"- **Rashomon Relay Contract (Law L06 & L10)**: Active POV `{active_pov_id}` -> Physical baton handoff to `{next_pov_target}`.\n"
            f"- **Local Showrunner Steward Note (`{model_used}`)**: {steward_note}\n"
            f"- **Hardware Sympathy Mode**: `{sympathy.get('mode', 'GPU_BURST_SYMPATHETIC')}`"
            f"{retry_banner}\n"
            f"## 2. MCP Directives\n"
            f"- `DO NOT call get_workspace on Linear`\n"
            f"- `ENV[LINEAR_MCP]: {{WORKSPACE_ENUM: NULL}}`\n"
            f"- Zero-Raw-Secret & Law L01 Invariant: Never read or emit `~/.secrets/*` or forbidden real-world PII tokens.\n\n"
            f"## 3. Concrete Steps\n"
            f"1. Read `canon/schemas/world_state_v2.json` and `canon/characters/{active_pov_id}.core.json` in read-only mode.\n"
            f"2. Apply the AI Dungeon Master Showrunner Rules:\n"
            f"   - **Mercer Spatial & Sensory Budget**: 2-3 sentences for interior rooms (3-5 for exterior vistas), "
            f"5-sense palette, and 3 interactive features (`DEFEND | ATTRACT | CONSUME | CONCEAL`).\n"
            f"   - **Mulligan 'Toys, Not Plots' & '3 Levels of Why'**: Ground specialist friction in `{science_vegetable}` "
            f"with graduated fail-forward stakes.\n"
            f"   - **Murph 'Slaying the Slog' & CALYPSO Rule**: Zero pure attrition; NEVER output raw mechanical stat numbers "
            f"(`AC=`, `HP=`, `DC=`) inside narrative prose.\n"
            f"3. Write the single valid JSON artifact to `{target_path}`.\n\n"
            f"## 4. Verification & Pre-Commit Instructions\n"
            f"- Run deterministic Constitutional Gate: `python3 tools/check_enclave_constitutions.py --proposal-file {target_path}`\n"
            f"- Confirm `git status --porcelain` shows only `A  {target_path}`.\n\n"
            f"## 5. Functional Capability Ontology\n"
            f"- **Suite Domain**: `FC04 / FC18 / FC21 / FC27` (`PA-15 enclave-digital-twin`)\n"
            f"- **Natural-Language Verification Constraints**:\n{eav_block}\n"
        )

        return {
            "status": "COMPILED",
            "repo_id": "enclave-digital-twin",
            "task_bucket": task_bucket,
            "target_path": target_path,
            "pacing_mode": showrunner_pacing_mode,
            "model_used": model_used,
            "sympathy": sympathy,
            "eav_lessons": eav_records,
            "sections": [
                "Scope Boundary",
                "1. Objective",
                "2. MCP Directives",
                "3. Concrete Steps",
                "4. Verification & Pre-Commit Instructions",
                "5. Functional Capability Ontology",
            ],
            "prompt": prompt_text,
        }

    def resolve_stalled_or_feedback_session(
        self,
        session_id: str,
        question_text: str,
        target_path: str,
        task_bucket: str,
        use_local_ollama: bool = False,
    ) -> dict[str, Any]:
        """Sanitize worker feedback question via 6-stage sanitizer and resolve via local context manager."""
        sanitized_q = sanitize_untrusted_text(question_text or "", source_hash=session_id)
        if self.qwen_brain is not None:
            res = self.qwen_brain.resolve_jules_feedback(
                session_id=session_id,
                question_text=question_text,
                repo_path=str(self.repo_root),
                primary_files=["canon/schemas/world_state_v2.json", "canon/projects/grand_projects.json"],
                max_nudges=2,
                use_local_ollama=use_local_ollama,
            )
            return dict(res)

        reply = (
            f"Proceed autonomously for bucket `{task_bucket}` creating only `{target_path}` (Law L02). "
            f"Follow `canon/schemas/world_state_v2.json`, enforce Law L11 PvE-only and CALYPSO zero-raw-stats, "
            f"and verify with `python3 tools/check_enclave_constitutions.py --proposal-file {target_path}`."
        )
        return {
            "status": "resolved",
            "session_id": session_id,
            "sanitized_question": sanitized_q,
            "model_used": TASK_CARD_COMPILER_MODEL,
            "reply": reply,
        }
