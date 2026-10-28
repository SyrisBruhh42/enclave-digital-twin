# The Enclave of the 16 (`enclave-digital-twin` — `PA-15`)

Constitutional multi-agent digital twin simulation featuring a 16-law constitutional checker, append-only Sol event ledgers, Winnow story sifter, FABLES-verified Evening Dispatch newscaster, interactive Showrunner Command Slate (`ui/dispatch_viewer.html`), Local Ollama Manager (`engine/local_ai_manager.py`), and 300-session rolling-window Jules standby scheduler (`tools/enclave_fleet_ctl.py`).

## Verification

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

## Capsule Manifest & Runtime Alignment (`PA-15`)

This repository ships `capsule.manifest.json` (`enclave-digital-twin`, `PA-15`) with deterministic offline simulation (`tools/run_sol_simulation.py`) and 16-law constitutional verification (`tools/check_enclave_constitutions.py --strict`).

---

## Legal, Licensing, Credits & Security

* **License**: [`LICENSE`](./LICENSE) — Copyright (c) 2026 SyrisBruhh42. All Rights Reserved.
* **Legal & IP Notice**: [`LEGAL.md`](./LEGAL.md) & [`NOTICE`](./NOTICE) — Intellectual property reservation, warranty disclaimer, and compliance terms.
* **Open-Source & Font Attributions**: [`CREDITS.md`](./CREDITS.md) — Third-party engine, runtime, and SIL Open Font License 1.1 typography credits.
* **Security Policy**: [`SECURITY.md`](./SECURITY.md) — Zero-Trust security invariants and private vulnerability disclosure policy.
