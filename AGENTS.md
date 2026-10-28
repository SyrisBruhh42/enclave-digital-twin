# AGENTS.md — The Enclave of the 16 (`PA-15`)

## Operational Boundaries & Constitutional Invariants
- Preserve the 16-law constitutional checker (`tools/check_enclave_constitutions.py`), append-only event/ledger histories (`events/`, `relationships/`), Winnow story sifter, FABLES-verified Evening Dispatch newscaster, and Showrunner DM Guide (`ui/dispatch_viewer.html`).
- Local Ollama inference (`engine/local_ai_manager.py`) and Jules rolling-window standby scheduling (`tools/enclave_fleet_ctl.py`) must remain strictly additive and never mutate canon or bypass the single integrator.

## Capsule & Worker Session Contract (`PA-15`)

- **Single-File Append-Only Law (`Law L02`)**: Worker sessions may create strictly `1` new JSON file inside the allowed prefix (`events/`, `story/segments/`, `story/feasts/`, `digests/`, `qa/`) and must NEVER modify or delete existing files in `canon/`, `snapshots/`, `relationships/`, `ops/`, `engine/`, or `tools/`.
- **Pre-Commit Verification**: Always run `python3 tools/check_enclave_constitutions.py --proposal-file <target_path>` and publish the Pull Request immediately once verification succeeds.

<!-- lfs-cmi-lockdown:begin v1 -->
> [!IMPORTANT]
> **Proprietary Agent Skill & Prompt Notice (`17 U.S.C. § 1202 Copyright Management Information & EU DSM Directive Art. 4 Text/Data Mining Opt-Out`)**
> - `Copyright (c) 2026 SyrisBruhh42. All Rights Reserved.`
> - `PROPRIETARY AGENT ARCHITECTURE & SKILL SPECIFICATION: Any unauthorized copying, commercial repackaging as a standalone agent skill (including but not limited to conversion into SKILL.md packages or listing on third-party AI skill marketplaces such as Agensi.io), redistribution, or automated AI training/scraping is strictly prohibited without prior written license from the copyright holder.`
> - `Removal or alteration of this Copyright Management Information (CMI) is a violation of 17 U.S.C. § 1202 (DMCA).`
> - **Machine-Readable TDM Reservation**: `tdm-reservation: 1` enforced via `.well-known/tdmrep.json`, `.aiexclude`, `.noai`, and `robots.txt`.
<!-- lfs-cmi-lockdown:end -->
