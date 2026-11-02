<!-- HUMAN-NOTES:BEGIN -->
# The Enclave of the 16 (`enclave-digital-twin` — `PA-15`)

Constitutional multi-agent digital twin simulation featuring a 16-law constitutional checker, append-only Sol event ledgers, Winnow story sifter, FABLES-verified Evening Dispatch newscaster, interactive Showrunner Command Slate (`ui/dispatch_viewer.html`), Local Ollama Manager (`engine/local_ai_manager.py`), and 300-session rolling-window Jules standby scheduler (`tools/enclave_fleet_ctl.py`).

## Verification

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

## Capsule Manifest & Runtime Alignment (`PA-15`)

This repository ships `capsule.manifest.json` (`enclave-digital-twin`, `PA-15`) with deterministic offline simulation (`tools/run_sol_simulation.py`) and 16-law constitutional verification (`tools/check_enclave_constitutions.py --strict`).
<!-- HUMAN-NOTES:END -->

<!-- STEWARD:BEGIN -->
## LFS Oasis Sovereign Steward Manifest (`v2.0.0-cp12-argon4-apex`)

| Property | Value |
| :--- | :--- |
| **Repository** | `SyrisBruhh42/enclave-digital-twin` |
| **Capsule / Project ID** | `enclave-digital-twin` (`PA-15`) |
| **Suite Release Alignment** | `LFS Oasis v2.0.0 / CP-12 + v3.8-sovereign-forge` (`v2.0.0-cp12-argon4-apex`) |
| **Runtime & Architecture** | Python 3.12 Constitutional Simulation Engine + HTML5 Showrunner Command Slate (`ui/dispatch_viewer.html`) + Local Ollama Bridge |
| **Local Storage Engine** | Append-Only Local JSONL Sol Ledgers & SQLite WAL (`PRAGMA synchronous=NORMAL`) |
| **Governance & ABAC** | `AUTH-1` Total Typed ABAC (`lfs-local-abac-v1`) · `ZT-6` Zero-Trust Scrubbing |

### 1. Architecture & Four-Umbrella (`U1..U4`) Integration
Constitutional multi-agent digital twin simulation featuring a 16-law constitutional checker, append-only Sol event ledgers, Winnow story sifter, FABLES-verified Evening Dispatch newscaster, and interactive Showrunner Command Slate.

- **Offline-First Autonomy**: Operates 100% locally by default with deterministic state persistence and zero mandatory cloud dependencies.
- **LFS Oasis Suite Dockability**: Integrates with `2-lfs-server` (`127.0.0.1:3000`), `3-lfs-aegis-linux` (`Willow v0.2.0` / `lfs-ctl` Spine / Local Sovereign Forge `:19447`), and `4-lfs-aegis-android` via `aegisEnvelopeV1` AES-256-GCM Save Lab envelopes and `lds-tokens.w3c.json` theme packs (`evergreen-dark`, `evergreen-light`, `high-contrast`, `calm`).

### 2. Zero-Trust Credential Vault & `RATCHET-11` Secret Hygiene
- **Zero Committed Secrets**: Static configuration files (`firebase-applet-config.json`, `.env.example`) carry `"VAULT_INJECTED_AT_RUNTIME"` placeholders. No literal `AIzaSy*`, `GOCSPX-*`, `ya29.*`, `1//*`, or `sk-*` keys are ever stored in Git history or working trees.
- **Runtime Injection & Offline Fallback**: Client loaders resolve credentials strictly at runtime via `import.meta.env.VITE_FIREBASE_API_KEY` or the loopback Sovereign Vault endpoint (`/api/lfs/vault/client-config`) and automatically fall back to local IndexedDB / SQLite WAL storage when offline.
- **Privacy & Third-Party Disclosures**: See [`PRIVACY.md`](./PRIVACY.md) and [`THIRD_PARTY_NOTICES.md`](./THIRD_PARTY_NOTICES.md).

### 3. Copyright Management Information (`17 U.S.C. § 1202`) & TDM Opt-Out (`EU DSM Art. 4`)
> [!IMPORTANT]
> - `Copyright (c) 2026 SyrisBruhh42 / Lewis Family Systems. All Rights Reserved.`
> - `PROPRIETARY AGENT ARCHITECTURE & SKILL SPECIFICATION: Any unauthorized copying, commercial repackaging as a standalone agent skill (including but not limited to conversion into SKILL.md packages or listing on third-party AI skill marketplaces such as Agensi.io), redistribution, or automated AI training/scraping is strictly prohibited without prior written license from the copyright holder.`
> - `Removal or alteration of this Copyright Management Information (CMI) is a violation of 17 U.S.C. § 1202 (DMCA).`
> - **Machine-Readable TDM Reservation (`tdm-reservation: 1`)**: Enforced via [`.well-known/tdmrep.json`](./.well-known/tdmrep.json), [`.aiexclude`](./.aiexclude), [`.noai`](./.noai), and [`robots.txt`](./robots.txt).
<!-- STEWARD:END -->
