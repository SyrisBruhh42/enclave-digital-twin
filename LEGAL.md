# LFS Oasis Suite (`v2.0.0` / `v3.2-argon4`) — Legal, Licensing & Compliance Statement

**Copyright & First-Party License**: `Copyright (c) 2026 SyrisBruhh42. All Rights Reserved. Proprietary Source-Available License (Personal/Educational Inspection Only — Unauthorized Commercial Redistribution, Skill Marketplace Listing, Sublicensing, or AI Dataset Scraping Strictly Prohibited).`  
**Author & Steward**: `SyrisBruhh42`  
**Canonical Origin**: [`https://lewisfamilysystems.com`](https://lewisfamilysystems.com)  
**Companion Documents**: [`LICENSE`](LICENSE) · [`CREDITS.md`](CREDITS.md) · [`SECURITY.md`](SECURITY.md)

---

## 1. Copyright, Sovereignty & First-Party Proprietary Source-Available License

- **First-Party Code, Game Worlds, Lore, Assets & Agent Skills/Prompts (`AGENTS.md`, `SKILL.md`)** are unambiguously governed by:
  **`Copyright (c) 2026 SyrisBruhh42. All Rights Reserved. Proprietary Source-Available License (Personal/Educational Inspection Only — Unauthorized Commercial Redistribution, Skill Marketplace Listing, Sublicensing, or AI Dataset Scraping Strictly Prohibited).`**
- All original architectural specifications, governance contracts (`governance/*.json`), first-party source code, deterministic simulation engines, game worlds, lore, visual/audio assets, capsules, documentation, and autonomous agent instructions/skills/prompts (`AGENTS.md`, `SKILL.md`, `GEMINI.md`, `.agents/**`, `.claude/**`) across the Four-Umbrella LFS Oasis Suite (`1-lfs-anchor`, `2-lfs-server`, `3-lfs-aegis-linux`, and `4-lfs-aegis-android`) are the exclusive intellectual property of **`SyrisBruhh42`**.
- **Anti-Marketplace & Anti-Scraping Enforcement (`17 U.S.C. § 1202` CMI)**: No third-party marketplace (including, without limitation, `Agensi.io` or any commercial agent/skill directory), broker, or automated scraper is authorized to copy, list, index, package, sublicense, or sell any code, capsule, prompt, or skill (`SKILL.md`, `AGENTS.md`) from this suite or its companion repositories.

---

## 2. Third-Party Open-Source Software Attribution (`CREDITS.md` & `NOTICE`)

**Third-Party Open-Source Dependencies & Fonts** remain governed by their respective upstream permissive licenses (`Apache-2.0`, `MIT`, `BSD-3-Clause`, `PSF-2.0`, `SIL Open Font License 1.1` as itemized in [`CREDITS.md`](CREDITS.md) and each umbrella's `NOTICE` file), enforced continuously by `3-lfs-aegis-linux/core/lfs-ctl/verify_oss_license_compliance.py` (`UMB-06` / `LEGAL-01..04`):

1. **`LEGAL-01` — Dynamic `LGPL-3.0-only` Qt Binding (`PySide6-Essentials==6.11.2`)**:
   - `3-lfs-aegis-linux/capsules/image-sorter` links dynamically against `PySide6-Essentials==6.11.2` (`LGPL-3.0-only`, The Qt Company Ltd.) via standard wheel/shared library loading. All GPL-3.0 `PyQt6` dependencies have been completely removed from runtime and build lockfiles.
2. **`LEGAL-02` — Clean Electron Packaging (`willow-desktop-pet`)**:
   - `3-lfs-aegis-linux/capsules/willow-desktop-pet/scripts/package.cjs` excludes GPL `ffmpeg-static` binaries from `extraResource`.
3. **`LEGAL-03` — Minecraft Mod Capsules & Mojang/Microsoft Non-Affiliation**:
   - **NOT AN OFFICIAL MINECRAFT PRODUCT. NOT APPROVED BY OR ASSOCIATED WITH MOJANG OR MICROSOFT.**
   - All Minecraft-related capsules (`willowcraft`, `cool-hubble`, `true-survival-hardcore`) declare explicit loader manifest licenses (`MIT` / `CC0-1.0`) as required by `LEGAL-03` and distribute zero proprietary Mojang game binaries or credentials.
4. **`LEGAL-04` — SIL Open Font License 1.1 (`Noto Sans` & `Noto Serif`)**:
   - Bundled Lewis Design System typography (`Noto Sans` and `Noto Serif`, Copyright 2012-2026 Google LLC) is distributed under the **SIL Open Font License, Version 1.1 (`SIL OFL-1.1`)** as detailed in [`CREDITS.md`](CREDITS.md).
5. **`C-07` — Non-Commercial Model Quarantine**:
   - Any optional research model weights governed by non-commercial licenses (such as `CSD-ViT-L`) are strictly quarantined from commercial workloads and gated at `Tier 0` of the `AUTH-1` ABAC lattice.

---

## 3. Mandatory Safety, Wellness & Financial Disclaimers

1. **Valve & Steam Non-Affiliation**:
   - LFS Oasis is not affiliated with, endorsed by, or sponsored by **Valve Corporation** or **Steam**.
2. **Non-Medical & Wellness Disclaimer (`weightless-calm` / `:weightless`)**:
   - **Weightless Calm is a relaxation and breathing exercise tool and is NOT a medical device, clinical diagnostic tool, or substitute for professional medical or psychiatric advice.**
3. **Closed-Loop Non-Monetary Virtual Currency Disclaimer (`LFS Tokens / LFT` & `Rupees / RUP`)**:
   - **LFS Tokens (LFT) are closed-loop, non-monetary, non-transferable family/classroom chore and reward points with zero cash value, zero blockchain/cryptocurrency backing, and cannot be purchased, sold, or redeemed for fiat currency.**
   - The **Two-Vault Firewall (`ECON-FIREWALL-01`)** strictly isolates in-game Play/Capsule Rupees (`VAULT_PLAY_RUP`) from family chore/allowance ledgers (`VAULT_CHORE_ALLOWANCE`), prohibiting real-money monetization (`C-15`).
4. **No Warranty (`AS IS`)**:
   - THE SOFTWARE IS PROVIDED **"AS IS"**, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT.
