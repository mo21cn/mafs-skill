# CQC Artifact Chain

The CQC producer generates a four-stage artifact chain before
handing off to MAFS. This document captures what each artifact is,
who is authoritative for it, and how the chain must be re-derived
on a clean machine.

```text
Research Narrative
  ↓
CandidateQuestionSet (CQS)            ← admission authority
  ↓
SearchRequirementProfile (SRP)        ← evidence-obligation authority
  ↓
BudgetEnvelope                        ← resource authority
  ↓
CQCMAFSIntegrationBinding             ← lineage only
  ↓
(handed off to MAFS)
```

## Research Narrative

The human-supplied research question, in natural language. It is
the input the user gives the Skill. The Skill never modifies the
narrative's scientific content; it only digests it.

## CandidateQuestionSet (CQS) — admission authority

CQS is the **admission authority**. It enumerates the candidate
questions that the CQC producer admits into the workflow. The
producer generates CQS from the Research Narrative; the Skill
cannot add or remove candidates outside the CQS contract.

Admit once; do not re-admit on every iteration.

## SearchRequirementProfile (SRP) — evidence-obligation authority

SRP records, for each requirement derived from CQS, what evidence
would discharge it. A requirement is not done when its artifact
exists — it is done when its SRP-defined evidence obligations are
met.

Each route in SRP has a status:

```text
REQUIRED     — must be discharged before discovery
CONDITIONAL  — held until explicitly activated
```

CONDITIONAL routes remain held until a human or downstream
authority explicitly activates them. The Skill must never auto-activate
CONDITIONAL.

## BudgetEnvelope — resource authority

BudgetEnvelope records the resource allocation (compute, time,
budget) granted to the search. The envelope is the **resource
authority**: it determines feasibility, not the CQS or the SRP.

```text
feasible       — the route can be funded within the envelope
constrained    — the route can be partially funded
insufficient   — the route cannot be funded; binding must be
                 INTEGRATION_BLOCKED_BUDGET_INSUFFICIENT
```

The Skill must never allocate beyond the envelope. Routes that
cannot be funded remain unfunded and are reported as such.

## CQCMAFSIntegrationBinding — lineage only

IntegrationBinding records the binding between the CQC producer
artifacts (CQS, SRP, BudgetEnvelope) and the MAFS consumer
artifacts (Axis, SearchOrder). It is **lineage only**: it does
not contain semantic interpretation, evidence discharge, or
budget reasoning. Those live in their parent artifacts.

Re-deriving the binding chain from the four producer artifacts
must produce a byte-stable binding, because the source artifacts
are hash-pinned.

## Re-derivation on a clean machine

When the Skill boots on a clean machine:

```text
1. resolver materializes CQC at b34a122
2. Skill imports CQC producer scripts (validate_cqs, render_srp,
   render_budget_envelope, build_integration_binding, …)
3. each artifact is regenerated against the pinned narratives
4. SHA-256 of each regenerated artifact is compared to the
   committed SHA-256 in CQC's docs/CQC_P*_SHA256_MANIFEST.txt
5. only artifacts whose bytes match exactly are accepted
```

If the SHA-256 of any artifact drifts from the manifest, the
resolver reports `RUNTIME_CACHE_CORRUPT` and re-materializes.
The Skill never silently accepts a drifted artifact.
