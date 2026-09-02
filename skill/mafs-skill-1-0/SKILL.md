---
name: mafs-skill-1-0
description: "MAFS Skill 1.0 runs the CQC (P0..P5) then MAFS (P0..P3) falsification-search workflow. Bootstrap gate first reads release/BASELINES.json, runs resolve_runtime_dependencies.py, and runs doctor.py; only then does it digest a research narrative through CQS, SRP, BudgetEnvelope, and IntegrationBinding, hands off to MAFS discover, STOP, explicit CandidatePointer selection, and resolve."
version: 1.0.0
product: MAFS Skill 1.0
contract: MAFS-SKILL-1.0-DELIVERY-RA1-SELF-CONTAINED-EXACT-RUNTIME-REPRODUCIBLE-PACKAGE-v0.1
frozen_source_baseline: see release/BASELINES.json
runtime_path_c: PRESERVED
---

# MAFS Skill 1.0

This is the canonical agent-neutral Skill core. After installation, it
is **self-contained**: the Skill owns its bootstrap companion
(resolver + doctor + baseline truth + shared runtime predicate).

## 0. Installed topology (RA1 contract §4)

When installed at `<agent-skill-root>/mafs-skill-1-0/`:

```text
mafs-skill-1-0/
├── SKILL.md                                 this file
├── VERSION                                  1.0.0
├── agents/
│   └── openai.yaml                          Codex / OpenAI discovery adapter
├── references/
│   ├── BASELINES.md
│   ├── CQC_ARTIFACT_CHAIN.md
│   ├── MAFS_RUNTIME_BOUNDARY.md
│   └── AUTHORITY_RULES.md
├── release/
│   └── BASELINES.json                       canonical CQC + MAFS pins
└── scripts/
    ├── _runtime_truth.py                    shared executable-runtime predicate
    ├── resolve_runtime_dependencies.py     §11-15
    └── doctor.py                            §16
```

The installed Skill is operational even if the original source
package, the portable ZIP, or the development repository is deleted
(RA1 §4).

## 1. Before any scientific invocation — bootstrap gate

Every scientific invocation of this Skill MUST begin with these four
steps, in this order, and MUST NOT proceed past step 3 unless step 3
returned `RUNTIME_READY`:

```text
1. read installed release/BASELINES.json
2. run installed scripts/resolve_runtime_dependencies.py
3. run installed scripts/doctor.py
4. only then begin CQC digestion
```

The bootstrap gate (RA1 §5) MUST reference runtime companion files
relative to the installed Skill root. Forbidden:

```text
assuming repository checkout root
assuming source PKG path
asking HO to provide CQC / MAFS paths by default
calling scripts from the development repository
```

The Skill MUST NOT ask HO for the two local repository paths by
default. The two paths are optional expert overrides
(`MAFS_CQC_REPO` and `MAFS_ENGINE_REPO`) used only when the user
explicitly wants to point at a pre-existing development checkout. Even
then, the override is consumed read-only as an **acquisition source**;
the resolved executable path is always inside the managed runtime
home (RA1 §8, §9).

## 2. Frozen workflow

The workflow is fixed and may not be reinterpreted by the delivery
layer:

```text
Research Narrative
→ CandidateQuestionSet (CQS)        [admission authority]
→ SearchRequirementProfile (SRP)     [evidence-obligation authority]
→ BudgetEnvelope                     [resource authority]
→ CQCMAFSIntegrationBinding          [lineage only]
→ model-authored MAFS Axis / SearchOrder
→ discover()
→ STOP / cognitive checkpoint
→ explicit CandidatePointer selection (never auto)
→ resolve()
```

## 3. Frozen authority rules

These rules are part of the Skill contract and may not be weakened by
packaging, configuration, operator convenience, or default settings:

```text
CQS                     = admission authority
SRP                     = evidence-obligation authority
BudgetEnvelope          = resource authority
CQCMAFSIntegrationBinding = lineage only
MAFS Axis / SearchOrder = model-authored search realization
```

```text
Structural traceability != semantic containment
CONDITIONAL remains held until explicitly activated
Never auto-select top-1
Never auto-resolve
Full MAFS run_preflight remains NOT_EVALUATED unless separately earned
```

## 4. Resolver states

The runtime resolver reports exactly one of these states. Missing
managed runtime is **not** the same as a wrong pinned commit (RA1 §12):

```text
READY
BASELINE_MATERIALIZATION_REQUIRED
BASELINE_MISMATCH
BASELINE_UNAVAILABLE
DEPENDENCY_TOOL_MISSING
RUNTIME_CACHE_CORRUPT
```

Semantics:

```text
missing managed runtime → BASELINE_MATERIALIZATION_REQUIRED
                         → materialize exact pin
                         → READY

wrong pin / dirty tree  → RUNTIME_CACHE_CORRUPT
                          → STOP (or full re-materialize)

cannot obtain exact pin → BASELINE_UNAVAILABLE
                          → STOP
```

## 5. Doctor overall states

```text
RUNTIME_READY
RUNTIME_MATERIALIZATION_REQUIRED
RUNTIME_BLOCKED
```

The doctor and the resolver share the **same executable-runtime
predicate** (RA1 §11): a managed dependency is executable iff
`(a) path is under the managed runtime home, (b) HEAD == required
40-char SHA, (c) tracked worktree bytes are clean against HEAD`. A
state where the resolver reports READY while the doctor reports
BLOCKED for the same runtime is forbidden.

## 6. Bootstrap constraint (Python standard library only)

All installed scripts use Python standard library only. They do not
import `PyYAML`, `requests`, `pydantic`, `GitPython`, or any other
external Python package. `git` is the only allowed external system
tool. If `git` is absent, scripts report `DEPENDENCY_TOOL_MISSING` and
STOP — they never auto-install system software.

## 7. What this Skill does NOT do

- It does not vendor CQC or MAFS source.
- It does not perform live scientific retrieval during acceptance.
- It does not auto-select the top-1 candidate.
- It does not auto-resolve.
- It does not weaken the CQC P0..P5 contract.
- It does not modify CQC or MAFS repositories.
- It does not create a GitHub Release, marketplace entry, or package
  registry publication (those require separate authorization).
- It does not claim offline support in version 1.0.
- It does not silently substitute the development repository for the
  installed runtime (RA1 §19).

## 8. Required companion files

```text
VERSION                                  1.0.0
release/BASELINES.json                   canonical CQC + MAFS pins
references/BASELINES.md                  human-readable pin reference
references/CQC_ARTIFACT_CHAIN.md         CQS → SRP → BudgetEnvelope → IntegrationBinding
references/MAFS_RUNTIME_BOUNDARY.md      MAFS producer / consumer split, Path C
references/AUTHORITY_RULES.md            the frozen authority rules in detail
agents/openai.yaml                       Codex / OpenAI discovery adapter
```

## 9. Companion tooling (lives in `scripts/` after install)

```text
scripts/_runtime_truth.py                 shared executable-runtime predicate
scripts/resolve_runtime_dependencies.py  clone / verify / materialize pinned repos
scripts/doctor.py                         RUNTIME_READY / MATERIALIZATION_REQUIRED / BLOCKED
```

## 10. Path C (repository independence)

```text
mo21cn/mafs-cqc       — CQC producer (P0..P5)
mo21cn/mafs-v3-p0     — MAFS runtime (P0..P3)
mo21cn/mafs-skill     — this delivery package
```

These three are independent. The Skill integrates the two source
repositories at runtime via the resolver; it does not merge their git
histories, vendor their source, or replace them.

## 11. Status line

```text
Product:        MAFS Skill 1.0
Version:        1.0.0
CQC pin:        b34a12295bb4522ff027724630f244f2438c19e6
MAFS pin:       cd09699fc8cc160ab5cfff00a41e714961dd2109
Repository:     mo21cn/mafs-skill
Path:           C
Contract:       MAFS-SKILL-1.0-DELIVERY-RA1-SELF-CONTAINED-EXACT-RUNTIME-REPRODUCIBLE-PACKAGE-v0.1
Authority:      HO + ChatGPT
Work actor:     Local Claw
```
