# AGENTS.md — The Enclave of the 16 (`PA-15`)

## Operational Boundaries & Constitutional Invariants
- Preserve the 16-law constitutional checker (`tools/check_enclave_constitutions.py`), append-only event/ledger histories (`events/`, `relationships/`), Winnow story sifter, FABLES-verified Evening Dispatch newscaster, and Showrunner DM Guide (`ui/dispatch_viewer.html`).
- Local Ollama inference (`engine/local_ai_manager.py`) and Jules rolling-window standby scheduling (`tools/enclave_fleet_ctl.py`) must remain strictly additive and never mutate canon or bypass the single integrator.

## Capsule & Worker Session Contract (`PA-15`)

- **Single-File Append-Only Law (`Law L02`)**: Worker sessions may create strictly `1` new JSON file inside the allowed prefix (`events/`, `story/segments/`, `story/feasts/`, `digests/`, `qa/`) and must NEVER modify or delete existing files in `canon/`, `snapshots/`, `relationships/`, `ops/`, `engine/`, or `tools/`.
- **Pre-Commit Verification**: Always run `python3 tools/check_enclave_constitutions.py --proposal-file <target_path>` and publish the Pull Request immediately once verification succeeds.

