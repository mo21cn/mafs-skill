# MAFS Skill 1.0 — Portable Delivery Package

**Product:** MAFS Skill 1.0
**Version:** 1.0.0
**Machine Name:** `mafs-skill-1-0`
**Repository:** `mo21cn/mafs-skill`
**Branch:** `dev/1.0-delivery` (development) → `main` (post-acceptance)

A versioned, portable MAFS Skill 1.0 package that can be installed on a
clean machine or handed to Codex / another compatible agent without
pre-existing CQC / MAFS working copies.

## What this package contains

```text
mafs-skill/
├── VERSION                      # 1.0.0
├── README.md                    # this file
├── skill/mafs-skill-1-0/        # canonical agent-neutral Skill core
│   ├── SKILL.md
│   ├── agents/openai.yaml       # Codex/OpenAI discovery adapter
│   └── references/              # BASELINES / CQC_ARTIFACT_CHAIN / MAFS_RUNTIME_BOUNDARY / AUTHORITY_RULES
├── scripts/                     # stdlib-only bootstrap + delivery tooling
│   ├── install.py
│   ├── resolve_runtime_dependencies.py
│   ├── doctor.py
│   ├── verify_delivery.py
│   └── build_release.py
├── release/                     # canonical dependency truth + manifest
│   ├── BASELINES.json
│   ├── DELIVERY_MANIFEST.json
│   └── SHA256SUMS.txt
├── tests/                       # clean-machine / wrong-repo / corrupt-cache / network-failure
├── docs/                        # DELIVERY_SUMMARY.md + DELIVERY_METRICS.json
└── .github/workflows/           # delivery-ci.yml (ubuntu + windows)
```

## Frozen Source Baselines

| Source | Repository | Commit |
|---|---|---|
| CQC (P0..P5 producer) | `mo21cn/mafs-cqc` | `b34a12295bb4522ff027724630f244f2438c19e6` |
| MAFS (P0..P3 runtime) | `mo21cn/mafs-v3-p0` | `cd09699fc8cc160ab5cfff00a41e714961dd2109` |

These pins are stored in `release/BASELINES.json` (single source of truth).
No floating `main`, `latest`, `HEAD`, or dev branch may substitute.

## Repository Ownership — Path C

> **Merge the protocol, not the repositories.**

CQC and MAFS remain independent repositories. The Skill delivery layer
owns only packaging, installation, runtime bootstrap, baseline
verification, manifests, and deployment documentation.

The Skill never vendors CQC / MAFS source into the package.

## Quick start

```powershell
# 1) Install (Codex on Windows)
python scripts/install.py --target codex

# 2) Doctor
python scripts/doctor.py

# 3) Resolver materializes CQC + MAFS at exact pinned SHAs automatically
# (no HO input required; no clone path required)
```

For a generic agent (no Codex):

```powershell
python scripts/install.py --target-dir <compatible-agent-skill-dir>
```

For dry-run inspection:

```powershell
python scripts/install.py --target codex --dry-run
```

## What is not in this package

- No CQC or MAFS source (resolved at runtime, not vendored)
- No GitHub Release, marketplace publication, or package registry publication
- No PyYAML / requests / pydantic / GitPython bootstrap dependency
- No scientific execution engine
- No auto-candidate selection; no auto-resolve
- No live scientific search during acceptance

## Bootstrap Constraint

All scripts in `scripts/` use **Python standard library only**. This
prevents the failure mode observed during the first HO real-use test
where the Skill loaded but its runtime dependency readiness check
failed because `PyYAML` was missing.

`git` is the only allowed external system tool. If absent, scripts
report `DEPENDENCY_TOOL_MISSING` and STOP — they never auto-install
system software.

## Status

Delivery is `READY_FOR_HO_CHATGPT_ACCEPTANCE` once §22 / §26 / §27
acceptance gates have passed. See `docs/MAFS_SKILL_1_0_DELIVERY_SUMMARY.md`
section L for the current HO acceptance status.

---

Local Claw — `MAFS-SKILL-1.0-PORTABLE-DELIVERY-RUNTIME-BOOTSTRAP-v0.1`
