---
name: mafs-skill-1-0
version: 1.0.0
product: MAFS Skill 1.0
contract: MAFS-SKILL-1.0-PORTABLE-DELIVERY-RUNTIME-BOOTSTRAP-v0.1
frozen_source_baseline: see BASELINES.json
runtime_path_c: PRESERVED
---

# MAFS Skill 1.0

This is the canonical agent-neutral Skill core. It is the **single
source of truth** for the MAFS Skill 1.0 workflow. The
`agents/openai.yaml` file is a thin adapter for OpenAI / Codex
discovery and is **not** the canonical core.

## 0. Before any scientific invocation — bootstrap gate

Every scientific invocation of this Skill MUST begin with these four
steps, in this order, and MUST NOT proceed past step 3 unless step 3
returned `RUNTIME_READY`:

```text
1. read baseline truth
2. resolve / materialize dependencies
3. require RUNTIME_READY
4. only then begin CQC digestion
```

Step 1 reads `release/BASELINES.json` (installed as part of the
package) to obtain the exact pinned CQC and MAFS commits. Step 2
delegates to `scripts/resolve_runtime_dependencies.py`. Step 3
delegates to `scripts/doctor.py`.

**The Skill MUST NOT ask HO for the two local repository paths by
default.** The two paths are optional expert overrides
(`MAFS_CQC_REPO` and `MAFS_ENGINE_REPO`) used only when the user
explicitly wants to point at a pre-existing development checkout.

Correct UX:

```text
HO: 调用 MAFS Skill 1.0 搜索……
→ automatic runtime resolution
→ workflow
```

Forbidden UX:

```text
please provide CQC and MAFS local paths
```

## 1. Frozen workflow

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

## 2. Frozen authority rules

These rules are part of the Skill contract and may not be weakened by
packaging, configuration, or operator convenience:

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

## 3. Resolver states

The runtime resolver reports exactly one of these states. Missing
local repository is **not** the same as a wrong pinned commit:

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
missing local repo      → BASELINE_MATERIALIZATION_REQUIRED
                         → automatic materialization
                         → READY

wrong commit / dirty tree → BASELINE_MISMATCH
                          → STOP (or isolated materialization if
                            user explicitly opts in)

cannot obtain exact commit → BASELINE_UNAVAILABLE
                           → STOP
```

## 4. Doctor overall states

```text
RUNTIME_READY
RUNTIME_MATERIALIZATION_REQUIRED
RUNTIME_BLOCKED
```

A `RUNTIME_READY` doctor report is the precondition for any
scientific execution. Anything less is a bootstrap failure; the
Skill must not paper over it.

## 5. Bootstrap constraint (Python standard library only)

All scripts in this package use Python standard library only. They
do not import `PyYAML`, `requests`, `pydantic`, `GitPython`, or any
other external Python package. `git` is the only allowed external
system tool. If `git` is absent, scripts report
`DEPENDENCY_TOOL_MISSING` and STOP — they never auto-install system
software.

This constraint exists because the first HO real-use test of the
Skill loaded the contract but failed at runtime because `PyYAML` was
missing on a clean machine.

## 6. What this Skill does NOT do

- It does not vendor CQC or MAFS source.
- It does not perform live scientific retrieval during acceptance.
- It does not auto-select the top-1 candidate.
- It does not auto-resolve.
- It does not weaken the CQC P0..P5 contract.
- It does not modify CQC or MAFS repositories.
- It does not create a GitHub Release, marketplace entry, or package
  registry publication (those require separate authorization).
- It does not claim offline support in version 1.0.

## 7. Required companion files

```text
VERSION                                  # 1.0.0
release/BASELINES.json                   # canonical CQC + MAFS pins
references/BASELINES.md                  # human-readable pin reference
references/CQC_ARTIFACT_CHAIN.md         # CQS → SRP → BudgetEnvelope → IntegrationBinding
references/MAFS_RUNTIME_BOUNDARY.md      # MAFS producer / consumer split, Path C
references/AUTHORITY_RULES.md            # the frozen authority rules in detail
agents/openai.yaml                       # Codex / OpenAI discovery adapter
```

## 8. Companion tooling (not part of the agent-neural core)

These are part of the package but live in `scripts/`:

```text
scripts/install.py                       # install into codex / agents / --target-dir
scripts/resolve_runtime_dependencies.py  # clone / verify / materialize pinned repos
scripts/doctor.py                        # RUNTIME_READY / MATERIALIZATION_REQUIRED / BLOCKED
scripts/verify_delivery.py               # §38 acceptance standard checker
scripts/build_release.py                 # dist/MAFS_Skill_1.0.0_Portable.zip
```

## 9. Path C (repository independence)

```text
mo21cn/mafs-cqc       — CQC producer (P0..P5)
mo21cn/mafs-v3-p0     — MAFS runtime (P0..P3)
mo21cn/mafs-skill     — this delivery package
```

These three repositories are independent. The Skill integrates the
two source repositories at runtime via the resolver; it does not
merge their git histories, vendor their source, or replace them.

## 10. Status line

```text
Product:        MAFS Skill 1.0
Version:        1.0.0
CQC pin:        b34a12295bb4522ff027724630f244f2438c19e6
MAFS pin:       cd09699fc8cc160ab5cfff00a41e714961dd2109
Repository:     mo21cn/mafs-skill
Path:           C
Authority:      HO + ChatGPT
Work actor:     Local Claw
```
