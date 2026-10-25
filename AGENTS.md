# AGENTS.md — The Enclave of the 16 (`PA-15`)

## Operational Boundaries & Constitutional Invariants
- Preserve the 16-law constitutional checker (`engine/`), append-only event/ledger histories (`events/`, `ledgers/`), Winnow story sifter, FABLES-verified Evening Dispatch newscaster, and Showrunner DM Guide (`ui/command_slate.html`).
- Local Ollama inference (`tools/ollama_local_manager.py`) and Jules rolling-window standby scheduling (`ops/standby_scheduler.py`) must remain strictly additive and never mutate canon or bypass the single integrator.

## LFS Suite `v1.1.0` Capsule Alignment (`3-lfs-aegis-linux/capsules/enclave-digital-twin`, `PA-15`)

- **Umbrella Target**: `/home/joe/Projects/LFS-Suite/3-lfs-aegis-linux/capsules/enclave-digital-twin` (`PA-15`, The Enclave of the 16).
- **Additive Plug-In & Synergy Standard**: Governed by `/home/joe/Projects/LFS-Suite/LFS-ECOSYSTEM-PLUGIN-STANDARD.md`. Integrates `capsule.manifest.json`, `aegis_lds_theme.tres`, local ABAC policy hooks (`lfs-local-abac-v1`), and offline Ollama/Jules simulation workflows into the Linux Aegis umbrella.
