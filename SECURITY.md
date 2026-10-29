# LFS Oasis Suite (`v2.0.0` / `v3.2-argon4`) — Security Policy & Public-Repository Safety Standard

**Copyright**: `Copyright (c) 2026 Lewis Family Systems / SyrisBruhh42. All Rights Reserved.`  
**Security Architecture**: Zero-Trust `AUTH-1` Typed ABAC · `ZT-6` Secret Redaction · `ZT-10` 3-Stage Sandbox · 3-Tier Portfolio Airlock

---

## 1. Zero-Trust `AUTH-1` Total Typed ABAC (`AbacExecutionEnvelopeV2`)

Every state-mutating action, capability invocation, setting mutation, and cross-game bridge call across `U1..U4` is governed by the **5-Level Sovereign Precedence Lattice (`Tier 0..4`)** enforced in `2-lfs-server/core/web-platform/lib/abac/typedAbacEngine.ts` and synchronized across all 6 governance mirrors (`governance/authority-contract.json` with `1,200` compiled rules and `governance/action-registry.json` with `1,192` registered entrypoints):

1. **Tier 0 — Immutable Safety & Hardware Floor**:
   - Enforces non-overridable invariants: `ZT-6` secret/PII redaction, `C-07` non-commercial model quarantine, `ECON-FIREWALL-01` Two-Vault economy isolation, and `HardwareSympathyGuard` (`>= 4.0 GiB` free host RAM floor).
2. **Tier 1 — Sovereign Emergency & Step-Up Authentication (`StepUpLeaseV2` & `DA-10`)**:
   - High-blast-radius administrative actions require cryptographic step-up verification (`DA-10` PBKDF2-SHA256 passphrase or hardware key) with single-use nonce replay immunity (`StepUpLeaseV2`) and instant Drawbridge perimeter revocation (`/dev/shm/lfs-perimeter-v1` in `<50ms`).
3. **Tier 2 — Explicit Negative Restrictions (`-attr` Deny Bindings)**:
   - Explicit negative attribute bindings strictly precede and override all Tier 3 VIP leases and Tier 4 role defaults.
4. **Tier 3 — Bounded VIP Pass Leases (`VipPassLeaseV1`)**:
   - Enforces `VIP-NO-COUP-01` anti-coup invariance and a bounded `<= 10.0x` priority multiplier cap inside the `Q48.16` `OasisQueueEngine`.
5. **Tier 4 — Baseline Role, Persona & Capsule Grants**:
   - Scoped least-privilege defaults for capsules (`cp12-capsule-manifest-v2`) and cross-game item entitlements (`lfs-local-abac-v1` / `lfs.game.item.use`).

---

## 2. `ZT-6` Secret Redaction & 4-Part Human Error Envelopes

The **Zero-Trust Scrubber (`ZT-6`)** and `governance/error-catalog.json` guarantee that runtime exceptions, logs, DMAIC diagnostic bundles, and UI error dialogs never leak sensitive data:

- **Automatic Credential & PII Scrubbing**: All bearer tokens, `Cookie` / `Set-Cookie` headers, API keys, passphrase hashes, session nonces, and raw stack traces are stripped before reaching logs, telemetry, or UI surfaces.
- **4-Part Redacted Error Contract**: Every user-visible error resolves to a structured 4-part plain-language envelope (`<= Grade 8.0` Flesch-Kincaid readability) containing `what_happened`, `why_it_happened`, `how_to_fix`, and explicit `data_safety: "Your data and saves were not changed."`.
- **Authenticated Save Encryption (`aegisEnvelopeV1`)**: Cross-device saves and configuration snapshots are encrypted at rest and in transit using **AES-256-GCM** (`aegisEnvelopeV1`) with authenticated integrity tags.

---

## 3. `ZT-10` 4-Zone Workspace Isolation & 3-Stage External Sandbox Cascade

Untrusted or external projects (`Zone C: DEVELOPED_OUTSIDE / DOWNLOADED_OUTSIDE`) are classified via `3-lfs-aegis-linux/core/lfs-ctl/oasis_intake_classifier.py` (**3-Second X-Ray Nutrition Label**) and isolated by `oasis_external_sandbox.py`:

1. **Stage 1**: Rootless `bwrap` (Bubblewrap) namespace isolation with read-only system mounts.
2. **Stage 2**: `systemd-run --user --scope --slice=background.slice -p MemoryMax=4G` resource containment with full XDG state redirection to `Zone D` (`~/.local/share/lfs-oasis`).
3. **Stage 3**: AppArmor profile receipt verification paired with **Sandbox Time-Machine** pre-launch snapshot rewind.

---

## 4. Public-Repository Safety & 3-Tier GitHub Portfolio Airlock (`UMB-01..06`)

To protect family privacy, workstation topology, and proprietary infrastructure across all `36` GitHub repositories under `SyrisBruhh42/*`:

1. **Rule 1 — Strict 3-Tier Visibility Airlock**:
   - **Tier 1 (Public Surface — `4` Repositories Only)**: Strictly limited to the `3` sanitized Google Jules target repositories (`LFS-Tycoon`, `LFS_TrashArcade`, `enclave-digital-twin`) and the public profile repository (`SyrisBruhh42/SyrisBruhh42`).
   - **Tier 2 (`4` Active Governance/Fleet Repos) & Tier 3 (`28` Docked Donor Lineage Repos)**: All `32` internal, family, infrastructure, and archival repositories (`project-office`, `lfs-jules`, `codex-antigravity-workbench`, `dot-workspace`, `lfs-member-sites`, `dads-book-lore`, `aegis-hub`, `aegis-familiar`, `lfs-netpulse`, `lfs-synchub`, etc.) MUST remain strictly **`PRIVATE` (`isPrivate: true`)**.
2. **Rule 2 — Zero Workstation, Network, or Secret Leakage in Public Repos**:
   - Public repositories (`Tier 1`) must contain **zero** `/home/<user>` local workstation paths, **zero** private RFC1918 (`10.x`, `192.168.x`, `172.16-31.x`) or Tailscale (`100.x`) IP addresses, **zero** personal email addresses or internal hostnames, **zero** API keys/secrets, and **zero** binary SQLite/runtime state files across both HEAD and full Git commit history (`git log -p --all`).
3. **Rule 3 — Mandatory Legal & Licensing Headers**:
   - Every public repository and every LFS Oasis umbrella (`U1..U4`) must maintain an explicit `README.md`, `LICENSE`, `LEGAL.md`, and `SECURITY.md`.

---

## 5. Reporting Security Issues

Report any suspected vulnerability, ABAC policy bypass, or public-repository data exposure directly to the realm steward via GitHub Private Vulnerability Reporting on `SyrisBruhh42` or through the administrative Sovereign Override Deck (`StepUpLeaseV2`). Do not post credentials, private IPs, or active exploit payloads in public issues.
