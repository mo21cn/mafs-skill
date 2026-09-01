# Authority Rules

These rules are part of the Skill contract. They may not be
weakened by packaging, configuration, operator convenience, or
default settings. If you find yourself wanting to relax one of
them, you are looking at a new contract — not a configuration
change.

## 1. Admission authority — CQS

`CQS` (CandidateQuestionSet) is the only authority that decides
which candidate questions enter the workflow.

```text
Admit once.    Do not re-admit on every iteration.
Do not bypass. Do not add candidates that CQS did not admit.
```

## 2. Evidence-obligation authority — SRP

`SRP` (SearchRequirementProfile) is the only authority that
records what evidence would discharge a requirement.

```text
A requirement is not done when its artifact exists.
A requirement is done when its SRP-defined evidence is met.
```

Each route in SRP has a status:

```text
REQUIRED     — must be discharged before discovery
CONDITIONAL  — held until explicitly activated
```

The Skill never auto-activates a CONDITIONAL route.

## 3. Resource authority — BudgetEnvelope

`BudgetEnvelope` is the only authority that decides whether a
search is feasible, constrained, or insufficient.

```text
feasible       — route can be fully funded
constrained    — route can be partially funded
insufficient   — route cannot be funded; binding must report
                 INTEGRATION_BLOCKED_BUDGET_INSUFFICIENT
```

The Skill never allocates beyond the envelope. Insufficient
routes remain unfunded; the Skill never invents more budget.

## 4. Lineage only — CQCMAFSIntegrationBinding

`CQCMAFSIntegrationBinding` records the lineage between CQC
artifacts and MAFS artifacts. It is **lineage only** — it does
not contain semantic interpretation, evidence discharge, or
budget reasoning. Those live in their parent artifacts.

A re-derivation of the binding chain from the four producer
artifacts (CQS, SRP, BudgetEnvelope, plus the source narrative)
must produce a byte-stable binding.

## 5. Model-authored search realization — MAFS

`MAFS` (Multi-Axis Falsification Search) is the only authority for
search realization: Axes, SearchOrders, `discover()`,
`CandidatePointer` enumeration, and `resolve()`.

The Skill never substitutes its own search for MAFS's.
The Skill never re-implements Axis or SearchOrder generation.

## 6. Structural traceability != semantic containment

`Structural traceability` (a path exists from A to B in the
artifact graph) is **not** the same as `semantic containment` (A
implies B's content). A local-claw signature on M1, M2, M3
proves structural traceability, not semantic containment.

```text
PASS:    the artifact chain reaches the expected endpoint
FAIL:    the artifact is the expected answer
```

The first is mechanical and verifiable. The second requires
human or model authority. The Skill does not pretend the first
is the second.

## 7. CONDITIONAL remains held until explicitly activated

CONDITIONAL routes are held by default. They require explicit
activation by a human or downstream authority. The Skill must
never auto-activate a CONDITIONAL route, even if the envelope
would support it.

## 8. Never auto-select top-1

`discover()` returns multiple `CandidatePointer`s. The Skill
must not auto-select the top-1. The model (or human) must
**explicitly select** which pointer to resolve.

```text
Forbidden:  candidates[0]
Forbidden:  auto_resolve()
Forbidden:  best_candidate
Forbidden:  rank_and_select
```

## 9. Never auto-resolve

`resolve()` is called only with an explicitly chosen
`CandidatePointer`. The Skill never auto-resolves a candidate.

## 10. Full MAFS run_preflight remains NOT_EVALUATED unless separately earned

`MAFS.run_preflight()` is not part of the default workflow. It
remains `NOT_EVALUATED` until:

- a CONDITIONAL route is activated, OR
- a downstream authority explicitly invokes preflight.

A preflight invocation that was not earned is a contract
violation.

## 11. Production repositories are immutable against the Skill

The Skill never modifies the CQC repository. The Skill never
modifies the MAFS repository. The Skill never merges them. The
Skill never vendors them.

If the Skill needs to change a rule in this file, that is a
new contract — not a configuration edit.

## 12. Bootstrap is stdlib-only; git is the only allowed external tool

The Skill's bootstrap scripts use Python standard library only.
They do not import `PyYAML`, `requests`, `pydantic`, or
`GitPython`. `git` is the only allowed external system tool.

If `git` is absent, the Skill reports `DEPENDENCY_TOOL_MISSING`
and STOPs. The Skill never auto-installs system software.

## 13. One-pin-per-source; no floating substitute

The Skill reads CQC's pin and MAFS's pin from
`release/BASELINES.json`. The resolver must reach
`git rev-parse HEAD == required 40-char SHA` for both.

No floating `main`, `latest`, `HEAD`, or dev branch may
substitute. No web search may substitute. No unverified source
archive may substitute.

## 14. Failure is honest

When bootstrap fails, the Skill reports a structured fact
record, not a stack trace:

```text
status
component
required_repository
required_commit
resolved_path
operation
reason
next_action
```

This is non-negotiable. UX that hides the actual failure
behind a generic "something went wrong" message is forbidden.
