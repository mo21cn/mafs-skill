# MAFS Runtime Boundary

MAFS is the **model-authored search realization** layer. It takes
the CQCMAFSIntegrationBinding produced by CQC and converts it
into Axes, SearchOrders, and a discover() call that surfaces
candidate evidence.

The Skill sits at the boundary between CQC (producer) and MAFS
(consumer). The boundary is non-negotiable: the Skill cannot
reinterpret MAFS's contract, and MAFS cannot reinterpret CQC's.

## What MAFS owns

```text
Axis                    — search axis definition
SearchOrder             — concrete search instruction
discover()              — produces CandidatePointers
run_preflight()         — checks preflight conditions
```

MAFS's `discover()` returns multiple `CandidatePointer`s. The
model (or human) must then **explicitly select** one pointer and
call `resolve()`. The Skill never auto-selects the top-1.

```text
Forbidden:  discover()[0]              ← auto-select top-1
Forbidden:  auto_resolve()             ← auto-resolve without selection
Forbidden:  rank_and_select(candidates) ← ranking-as-selection
```

## What the Skill does at the boundary

The Skill's role at the boundary is:

1. Hand the IntegrationBinding to MAFS.
2. Wait for `discover()` results.
3. **Stop at a cognitive checkpoint** — never auto-select.
4. Surface the candidate list to the human.
5. Receive the human's explicit `CandidatePointer` selection.
6. Call `resolve()` with that pointer.

The Skill is not a "smart" layer. It is a deterministic
boundary-walker.

## run_preflight — NOT_EVALUATED by default

A full MAFS `run_preflight()` is expensive and pre-emptively
exhausts a budget envelope. The Skill treats `run_preflight()` as
`NOT_EVALUATED` by default; it remains `NOT_EVALUATED` until
explicitly earned by:

- a CONDITIONAL route being activated, OR
- a downstream authority explicitly invoking preflight.

A preflight invocation that was not separately earned is a
contract violation.

## Path C — repository independence

```text
mo21cn/mafs-cqc    — CQC producer (P0..P5)
mo21cn/mafs-v3-p0  — MAFS runtime (P0..P3)
mo21cn/mafs-skill  — this delivery package
```

These three are independent. The Skill integrates them at runtime
via the resolver; it does not:

- vendor CQC source into the Skill
- vendor MAFS source into the Skill
- merge the CQC and MAFS git histories
- use a submodule to pull one into the other
- claim offline support by embedding whole repositories

If a future contract changes this boundary, it must do so by
issuing a new contract — never silently.

## Why the resolver clones each repo at runtime

The resolver clones CQC and MAFS into a private runtime cache
under `~/.mafs/skill-1.0/repos/`. This is not vendoring: the
clones are isolated, marked read-only against the user's other
checkouts, and discarded on Skill uninstall.

```text
~/.mafs/skill-1.0/
├── repos/        ← resolver-managed runtime clones
│   ├── mafs-cqc/
│   └── mafs-v3-p0/
├── state/        ← Skill state (binding cache, etc.)
└── logs/         ← resolver / doctor logs
```

Mutable state lives outside the installed Skill. The installed
Skill is immutable against upgrades; runtime state can be cleared
without touching the Skill.
