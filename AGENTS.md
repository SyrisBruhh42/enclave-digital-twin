# AGENTS.md — The Enclave of the 16 (`PA-15`)

## Operational Boundaries & Constitutional Invariants
- Preserve the 16-law constitutional checker (`tools/check_enclave_constitutions.py`), append-only event/ledger histories (`events/`, `relationships/`), Winnow story sifter, FABLES-verified Evening Dispatch newscaster, and Showrunner DM Guide (`ui/dispatch_viewer.html`).
- Local Ollama inference (`engine/local_ai_manager.py`) and Jules rolling-window standby scheduling (`tools/enclave_fleet_ctl.py`) must remain strictly additive and never mutate canon or bypass the single integrator.

## LFS Suite `v1.1.0` Capsule Alignment (`3-lfs-aegis-linux/capsules/enclave-digital-twin`, `PA-15`)

- **Umbrella Target**: `3-lfs-aegis-linux/capsules/enclave-digital-twin` (`PA-15`, The Enclave of the 16).
- **Additive Plug-In & Synergy Standard**: Governed by `governance/LFS-ECOSYSTEM-PLUGIN-STANDARD.md`. Integrates `capsule.manifest.json`, `aegis_lds_theme.tres`, local ABAC policy hooks (`lfs-local-abac-v1`), and offline Ollama/Jules simulation workflows into the Linux Aegis umbrella.
