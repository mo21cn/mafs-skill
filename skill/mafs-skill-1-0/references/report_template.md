# MAFS Skill 1.0 — Final Report Template

> **Authority model.** This template governs how a human-rendered final
> report MUST describe the artifacts produced by the driver
> (`resolved_canonical_evidence.json`, `discovery_candidate_pointers.json`,
> `integration_binding.json`, etc.). The driver / artifacts are
> authoritative; the report is a **rendering**, not an independent
> source. Per `MAINTENANCE_ADVISORY_v0.2` §3.C, **bounded search
> absence is not proof of global non-existence**; the report MUST
> inherit the artifact's negative-evidence authority and MUST NOT
> upgrade it.

## How to use

1. After `run_resolve.py` (or equivalent) writes the artifacts, copy this
   template into your workspace as `REPORT.md`.
2. Fill in the per-question table from `resolved_canonical_evidence.json`
   **field by field** — do not paraphrase or augment.
3. For Q3-style negative branches, use the verbatim bounded language
   from §3 below. Do **not** write "does not exist", "doesn't exist",
   "不存在", "没有这篇", or any equivalent global-non-existence claim.
4. Run `python references/report_validation.py REPORT.md` before
   publishing. **The validator is fail-closed**: any forbidden phrase
   triggers `REPORT VALIDATION FAIL` and blocks release.

## §1. Frozen workflow (executed end-to-end)

```
Research Narrative
→ CandidateQuestionSet (CQS)        <admit status from cqs.json>
→ SearchRequirementProfile (SRP)     <requirement list from srp.json>
→ BudgetEnvelope                     <FEASIBLE / INFEASIBLE>
→ CQCMAFSIntegrationBinding         <status from integration_binding.json>
→ MAFS Axis / SearchOrder            <list from model-authored planning artifact>
→ discover()                         <Q1..QN from discovery_candidate_pointers.json>
→ STOP (cognitive checkpoint)        <Y / N>
→ explicit CandidatePointer select   <human-selected Qs>
→ resolve()                          <canonical evidence for selected Qs>
```

## §2. Per-question result

| Q | Question (verbatim from CQS) | Identity recovered (DOI or "none") | Resolve (Y/N/ENTITY_RESOLUTION_REQUIRED) | Status |
|---|---|---|---|---|
| Q1 | <copy from cqs.json> | <DOI or "none"> | <Y/N/ENTITY_RESOLUTION_REQUIRED> | <see §3 language> |
| Q2 | ... | ... | ... | ... |
| ... | | | | |

## §3. Per-question status language (verbatim, do not paraphrase)

The report MUST pick the closest verbatim line below. The artifact
emitted `RESOLVED` / `NO_CANONICAL_CANDIDATE` / `LIKELY_CONFLATION` /
`ENTITY_RESOLUTION_REQUIRED` is the input.

### 3.1 Canonical evidence recovered (`RESOLVED`)

> Qn: paper identity **RECOVERED** (DOI `<doi>`); the source content
> was not re-rendered in this run.

### 3.2 Bounded negative / likely conflation (`NO_CANONICAL_CANDIDATE` or `LIKELY_CONFLATION`)

> Qn: no canonical candidate recovered under the bounded search; the
> current evidence supports likely conflation with `<closest
> canonical recovered paper, if any>`.

**Forbidden in this section** (see advisory §2.2):
- "does not exist"
- "doesn't exist"
- "不存在"
- "没有这篇"
- any equivalent global-non-existence claim

The wording "no canonical candidate was recovered under the bounded
search" is REQUIRED. The word "likely conflation" is REQUIRED when the
artifact emits `LIKELY_CONFLATION`. The word "bounded" is REQUIRED.

### 3.3 Entity-resolution boundary (`ENTITY_RESOLUTION_REQUIRED`)

> Qn: **ENTITY_RESOLUTION_REQUIRED** — the MAFS scholarly stack has
> no dataset adapter for this entity class. Operator-supplied seeds
> are marked `HISTORICAL_ENTITY_ANCHOR_UNVERIFIED`; no entity IDs are
> fabricated into the resolved results.

**Forbidden in this section** (advisory §6.2 + §2.2):
- "does not exist" applied to the entity
- any synthetic entity ID

## §4. Honest conclusion (mandatory)

End the report with a paragraph that names what the stack can and cannot
do, in the same bounded language. Example skeleton (adapt per task):

> The MAFS Skill 1.0 scholarly production stack resolved **paper
> identity** for the explicitly selected Qs, but it did **not** attempt
> source-content / dataset-entity resolution for the out-of-scope
> routes. Where the artifact marks a Q as `NO_CANONICAL_CANDIDATE`
> or `LIKELY_CONFLATION`, the report's wording reflects that
> bounded-search absence and does not assert global non-existence.

## §5. Reproducibility / artifact set

List every artifact file (path, sha256 if your harness requires it).
The fields come from the artifacts themselves; do not re-derive.

## §6. Boundary notes (contract-honoring)

These bullets are REQUIRED whenever they apply:

- **No auto-select / no auto-resolve**: discovery stopped, candidates
  were surfaced, the human explicitly selected Qn.., then resolve() ran.
- **CONDITIONAL routes remained held**: any route marked
  `RESERVE_CONDITIONAL` was **not** auto-activated.
- The MAFS / CQC managed repositories were **not modified** (import +
  call only).

## §7. Validation (mandatory step before publishing)

```bash
python <skill_root>/references/report_validation.py REPORT.md
```

If the validator exits non-zero, the report is blocked. Do not
override the validator by hand; if a forbidden phrase is in the report,
fix the report to use the bounded language from §3.
