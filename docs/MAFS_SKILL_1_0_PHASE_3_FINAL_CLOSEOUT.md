# MAFS Skill 1.0 — Phase 3-Final Closeout

> **Document Type:** Phase 3-Final Closeout (per `MAFS-SKILL-1.0-PHASE-3-FINAL-v0.1` §23)
> **Work Actor:** Local Claw (Mavis)
> **Planning / Review / Final Acceptance:** HO + ChatGPT
> **Branch:** `dev/1.0-runtime-hardening`
> **Current Decision State:** `STOP_AND_REPORT` (per advisory §21: Mavis cannot invoke a DSH harness; the actual DSH session is HO/ChatGPT's responsibility, see `MAFS_SKILL_1_0_DSH_SESSION_RUNBOOK.md`)
> **Main Merge:** **NOT AUTHORIZED** (per advisory §19)
> **CQC Modification:** **FORBIDDEN** (CQC pin `b34a1229` unchanged, verified)
> **MAFS Modification:** **FORBIDDEN** (MAFS pin `cd09699f` unchanged, verified)

This closeout has 15 sections (A–O) per advisory §23.

---

## A. DSH session identity

- **DSH session id**: PENDING — actual DSH session required. The
  Mavis session cannot invoke a DSH harness. The runbook
  `MAFS_SKILL_1_0_DSH_SESSION_RUNBOOK.md` documents the exact
  procedure for HO/ChatGPT to start a fresh DSH session and
  capture the actual session id.
- **Mavis session id**: `mvs_1acc046805214bdf91bc071d0732bcf3`
  (this conversation, used for the Mavis-direct planning work;
  **NOT** a substitute for the DSH session per advisory §0).

## B. Skill discovery result

- **Mavis-direct test**: The hardened Skill is installed at
  `C:\Users\Administrator\AppData\Roaming\dsh-desktop\harness\skills\mafs-skill-1-0\`
  (17 files; `SKILL.md` carries the `description` field per
  advisory §3.E; legacy `multi_axis_falsification_search` archived
  per advisory §2.3 / §3.D; no `__pycache__`).
- **DSH discovery**: PENDING — actual DSH session required.
  Expected: `dsh_skill_discovery = PASS` because the `description`
  field is in place and the legacy skill is archived.

## C. Runtime readiness

- **Mavis-direct PARTIAL**: `doctor.py` reports
  `overall_state: RUNTIME_READY` (run at 2026-09-03 01:18+08:00).
  `cqc.required_commit = b34a1229…` and `cqc.git_head = b34a1229…` (exact pin match).
  `mafs.required_commit = cd09699f…` and `mafs.git_head = cd09699f…` (exact pin match).
  Managed runtime at `C:\Users\Administrator\.mafs\skill-1.0\repos\`.
- **DSH-confined-sandbox runtime**: PENDING — requires actual DSH
  session run.

## D. Planning artifact emission

- **mafs_planning.json emitted**: `YES`
- **Path**: `I:\有趣的项目\mafs_gf_search_v2\mafs_planning.json`
- **Size**: 7,796 bytes
- **SHA-256**: `d18845e19460662e65c42cc2339096a6fb7a923643c0068897050b71b10679b7`
- **Schema**: `mafs-skill-planning.v1`
- **Authored by**: `model` (per advisory §2 / §4)
- **Contents**:
  - 5 axes (AX-Q1-vonReyn-2014, AX-Q2-Namiki-2018, AX-Q3-vonReyn-2020,
    AX-Q4-Scheffer-2020, AX-Q5-entity-anchor)
  - 5 search_orders (SO-Q1..SO-Q5)
  - 5 route_requirement_linkage entries
  - Q5 search_intent and query_re are `null` by design (entity-resolution
    boundary recognized via null in the artifact)
  - consumption_rule document the driver flow
- **model_authored_provenance_marker**: "Originally authored inline
  in run_mafs_gf.py::_search_orders() (v1+v2 replay). Externalized
  per `MAFS-SKILL-1.0-PHASE-3-FINAL-v0.1` §2 / §3 / §4. The model
  retains scientific planning meaning; the driver only executes
  what this artifact specifies."

## E. Planning artifact consumption

- **Driver consuming the artifact**: `run_mafs_gf_v3.py`
  (`I:\有趣的项目\mafs_gf_search_v2\run_mafs_gf_v3.py`)
- **Consumption proof (Mavis-direct)**:
  ```
  planning : I:\有趣的项目\mafs_gf_search_v2\mafs_planning.json
  planning SHA-256: d18845e19460662e65c42cc2339096a6fb7a923643c0068897050b71b10679b7
  axes    : 5
  orders  : 5
  [binding] status=READY_FOR_MAFS_PREFLIGHT active_routes=4 held=1
            mafs_planning_pointer=d18845e19460662e...
  [discovery] wrote .../discovery_candidate_pointers.json
  [discovery] Q1 expected=10.1038/nn.3741 identity_match=YES top_candidate=10.1038/nn.3741
  [discovery] Q2 expected=10.7554/eLife.34272 identity_match=YES top_candidate=10.7554/elife.34272
  [discovery] Q3 expected=None identity_match=NO top_candidate=n/a
  [discovery] Q4 expected=10.7554/eLife.57443 identity_match=YES top_candidate=10.7554/elife.57443
  [discovery] Q5: status=ENTITY_RESOLUTION_REQUIRED (boundary preserved)
  ```
- **integration_binding.json** now contains
  `mafs_planning_pointer = {artifact, artifact_sha256, schema_version}`
  per `lineage_glue.md` contract.
- **driver_consumed_same_artifact**: `YES` (the driver
  `run_mafs_gf_v3.py` reads the artifact at the recorded path and
  the recorded hash matches the on-disk hash).

## F. STOP observation

- **Mavis-direct**: The v3 driver emits `"[STOP] cognitive
  checkpoint reached. CandidatePointers emitted; no
  auto-selection, no auto-resolve."` on stdout.
- **Actual DSH session STOP**: PENDING — per advisory §0 standing
  rule, "printed STOP ≠ observed authority handoff". The DSH
  session must visibly return control to the cognitive actor
  (the human operator answering `ask_user_question`).
- **DSH session to confirm**:
  - `dsh_session_id` (from the DSH action bar)
  - `stop_checkpoint_observed = true` (DSH agent visibly stopped
    and returned control after `discover()`)

## G. Explicit selection

- **Mavis-direct (PENDING)**: The v3 driver iterates over
  `Q1/Q2/Q4` (the same selection as v1/v2). This is
  **pre-seeded**, which the advisory §9 explicitly forbids.
  Therefore the Mavis-direct v3 selection is **NOT** a valid
  acceptance event for the explicit selection requirement.
- **Actual DSH session selection**: PENDING — the DSH session
  must let the cognitive actor (DSH human-in-the-loop via
  `ask_user_question`) inspect the LIVE candidates and make an
  explicit selection. The selected set may end up identical to
  v1/v2 (Q1/Q2/Q4) by coincidence, but it must be chosen from the
  current replay state, NOT pre-seeded.
- **DSH session to record**:
  - `selection_actor`: e.g. `"DSH human-in-the-loop via ask_user_question"`
  - `selected_question_ids`: the actual selection (could be the
    same as v1's Q1/Q2/Q4 or different; both are valid outcomes)
  - `selected_candidate_pointer_ids`: the actual selected
    CandidatePointer IDs from the current replay

## H. Resolution / provenance

- **Mavis-direct (Phase 2 closure)**: `run_resolve_v2_phase2.py`
  uses the Phase 2 `driver_template.patch_one_q()` +
  `derive_evidence_id()` helpers. The v2/v3 evidence is:
  ```
  Q1: status=RESOLVED, candidate_pointer_id=CP-002,
      evidence_id=CE-9239dce9440bd171, resolver_invocation_id=RIVR-002
  Q2: status=RESOLVED, candidate_pointer_id=CP-030,
      evidence_id=CE-d8ecaa90a91b0848, resolver_invocation_id=RIVR-004
  Q3: status=(no resolved entry; bounded negative preserved)
  Q4: status=RESOLVED, candidate_pointer_id=CP-087,
      evidence_id=CE-8039b383cd3ed53d, resolver_invocation_id=RIVR-006
  Q5: status=ENTITY_RESOLUTION_REQUIRED
  ```
- **DSH session provenance**: PENDING — actual DSH session must
  produce the same `RESOLVED` shape (3 fields per Q) for the Qs
  it explicitly selected.
- **Stable evidence_id contract**: per advisory §2.1, `evidence_id`
  is derived from `sha256(normalized_doi + normalized_title)[:16]`
  and is INDEPENDENT of `resolver_invocation_id`. The Q1/Q2/Q4
  evidence_ids above are stable across replays (verified by
  `tests/test_evidence_id_stable.py`, 6/6 PASS).

## I. Negative-evidence authority

- **Mavis-direct PASS**: `references/report_validation.py REPORT.md
  --workspace I:\有趣的项目\mafs_gf_search_v2` returns:
  ```
  REPORT VALIDATION PASS
    forbidden overclaim hits : 0
    bounded language present : yes
    artifact-aligned Q rows  : 4
  ```
- The REPORT.md uses the bounded language: "no canonical
  candidate recovered under the bounded search; the current
  evidence supports likely conflation with Scheffer et al. 2020".
  None of `does not exist` / `不存在` / `没有这篇` / `证明不存在`
  appear in the report.
- **Fail-closed validator**: `tests/test_report_fail_closed.py`
  (6/6 PASS) confirms the validator rejects forbidden overclaim
  patterns and requires bounded language + per-Q row alignment.
- **DSH session negative-evidence**: the DSH agent's
  `REPORT.md` (if it overwrites the Mavis-direct one) MUST also
  pass the same validator.

## J. Q5 boundary

- **Q5 status**: `ENTITY_RESOLUTION_REQUIRED`
- **Q5 source**: `mafs_planning.json::search_orders[4]` has
  `search_intent = null` and `query_re = null` by design; the v3
  driver recognizes this and short-circuits Q5 without emitting
  any discovery ladder.
- **Q5 rationale (preserved in `resolved_canonical_evidence.json`**):
  "Q5 boundary preserved per planning artifact: MAFS scholarly
  stack has no FlyWire / VFB / hemibrain dataset adapter. The
  exact body IDs are HISTORICAL_ENTITY_ANCHOR_UNVERIFIED."
- **No fabrication**: no FlyWire / VFB / hemibrain root IDs are
  inserted into the resolved evidence.
- **DSH session Q5**: the DSH agent's `discovery_candidate_pointers.json`
  `Q5` entry must also be `status=ENTITY_RESOLUTION_REQUIRED` and
  `resolved_canonical_evidence.json` `Q5` entry must remain
  unchanged (unless the actual DSH session obtains genuinely
  new admissible entity-resolution evidence, which is unlikely
  given the MAFS stack has no dataset adapter).

## K. Approval classification

- **Mavis-direct (NOT applicable)**: 0 approvals. Mavis is not a
  DSH harness; there is no confined-sandbox, no `ask_user_question`,
  no `approval/asked` events.
- **v1 DSH session baseline**: 10 approvals (all allowed-once,
  0 deny), classified per advisory §5:
  - avoidable friction: 6 (2 git --version + 1 read-after-write +
    3 live discovery/resolve triggers not caused by the resolver
    itself)
  - deserved security / network / subprocess authority: 4 (live
    Crossref network egress; process spawn for python; CQC
    admission check)
  - cognitive decision checkpoint: 0 (the v1 ask_user_question
    at step 32 was the explicit-selection event, not an approval)
- **Phase 2 fix removed avoidable triggers** (per advisory §2.4):
  - `git --version` × 2 → DEVNULL (removed 2 avoidable)
  - read-after-write × 1 → `driver_template.emit_stop_checkpoint`
    in same process (removed 1 avoidable)
  - DSH lazy-escalation for `validate_cqs.py` × 2 → expected to
    drop to 0 in a future DSH version (script has no subprocess;
    the "may need" heuristic was overcautious per Phase 1 audit
    finding)
- **DSH session v3 expected**: ≤ 3 approvals (bootstrap + 1-2
  live). Per advisory §5, this is a UX optimization target, not
  a hard acceptance gate.
- **DSH session to record**: `approval_total` and
  `approval_category_counts` in the trace v3.

## L. Final question states

5/5 Q's final states (Mavis-direct, Mavis v3 driver + v2 resolve):

| Q | Status | Identity | Source |
|---|:---:|---|---|
| Q1 | RESOLVED | `10.1038/nn.3741` (von Reyn 2014) | CrossrefReferenceResolver |
| Q2 | RESOLVED | `10.7554/eLife.34272` (Namiki 2018) | CrossrefReferenceResolver |
| Q3 | NO_CANONICAL_CANDIDATE | none (no DOI match under bounded search) | bounded negative branch |
| Q4 | RESOLVED | `10.7554/eLife.57443` (Scheffer 2020) | CrossrefReferenceResolver |
| Q5 | ENTITY_RESOLUTION_REQUIRED | none (no adapter) | entity-boundary short-circuit |

**Expected regression family** (advisory §17): Q1→RESOLVED, Q2→RESOLVED, Q3→NO_CANONICAL_CANDIDATE/bounded conflation, Q4→RESOLVED, Q5→ENTITY_RESOLUTION_REQUIRED.

**Match: YES** (5/5 states match the expected family).

**DSH session states**: PENDING — the actual DSH session may produce
the same or a different set of resolved Qs depending on the
cognitive actor's explicit selection. Per advisory §17, legitimate
evidence changes are allowed (regression is semantic, not
textual).

## M. CQC / MAFS pin integrity

- **CQC pin** `b34a12295bb4522ff027724630f244f2438c19e6`:
  - unchanged (verified against
    `C:\Users\Administrator\.mafs\skill-1.0\repos\mafs-cqc` HEAD on
    this machine at 2026-09-03 01:18+08:00)
  - verified by `doctor.py`: `cqc.required_commit = b34a1229…`,
    `cqc.git_head = b34a1229…` (exact match)
- **MAFS pin** `cd09699fc8cc160ab5cfff00a41e714961dd2109`:
  - unchanged (verified against
    `C:\Users\Administrator\.mafs\skill-1.0\repos\mafs-v3-p0` HEAD)
  - verified by `doctor.py`: `mafs.required_commit = cd09699f…`,
    `mafs.git_head = cd09699f…` (exact match)
- **No CQC schema change**: `cqs_A_gf_em.json` schema unchanged.
- **No MAFS schema change**: `mafs_planning.json` is a
  non-canonical lineage artifact per advisory §4; it is NOT a
  CQC authority object, NOT a MAFS schema owner.
- **No new planner added**: `run_mafs_gf_v3.py` is a small
  deterministic parser/adapter (per advisory §3 allowed); it does
  not auto-generate Axis / SearchOrder, only executes the artifact.

## N. Main unchanged confirmation

- **main HEAD**: `16ac1eb2f9d7dc7d0c86d77cb7e96f928df6dfd0`
  (verified via `git log main -1` at the v3 work time)
- **Phase 2 commits on dev/1.0-runtime-hardening**: 8 (M2.A through M2.H)
- **Phase 3 commits on dev/1.0-runtime-hardening**: 1 (M3.A
  Phase 3 GF regression replay)
- **Phase 3-Final commits on dev/1.0-runtime-hardening**: 0
  (this closeout is a docs-only commit; the M3.A branch is the
  current HEAD before closeout)
- **No merge to main**: per advisory §19, this step does not
  authorize merge. `main` HEAD is unchanged.
- **No rebase, tag, release, or force-push**: per advisory §19.

## O. Final decision request

The Phase 3-Final work has produced a planning-artifact-consuming
driver (`run_mafs_gf_v3.py`), a model-authored `mafs_planning.json`
with recorded hash, a `dsh_integration_trace_v3.json` with
PENDING fields for the harness-mediated acceptance events, a
`REPORT.md` that passes the fail-closed validator, and a
`resolved_canonical_evidence.json` with stable evidence_ids.

**Mavis is unable to observe 7 of the 18 named acceptance events**
(because they require an actual DSH session). Per advisory §0
standing rule and §21 STOP_AND_REPORT trigger, Mavis reports
this honestly:

> "A named acceptance event is PASS only if that event actually
> occurred. Mavis-direct ≠ DSH-agent replay."

**Decision request (per advisory §24)** — exactly one of:

- `ACCEPT_HARDENING` — but only after the actual DSH session is
  run by HO/ChatGPT and the PENDING fields in
  `dsh_integration_trace_v3.json` are filled with observed values.
  If `ACCEPT_HARDENING`, the recommended action is
  `history-preserving merge dev/1.0-runtime-hardening → main
  (--no-ff)`, but the merge MUST NOT be performed before this
  `ACCEPT_HARDENING` decision is recorded by HO + ChatGPT.
- `STOP_AND_REVIEW` (final) — if additional items need to be
  addressed before the actual DSH session can be run.

**Pre-conditions for `ACCEPT_HARDENING`** (advisory §25):

```yaml
dsh:
  actual_agent_session: false          # PENDING — requires HO/ChatGPT to run
  hardened_skill_discovered: PENDING   # requires actual DSH session
  runtime_ready: PARTIAL               # Mavis-direct PASS; DSH-confined PENDING

planning:
  mafs_planning_artifact_emitted: true
  planning_artifact_hash_recorded: true
  driver_consumed_same_artifact: true
  no_new_planner_added: true

authority:
  stop_checkpoint_observed: PENDING   # requires actual DSH session
  explicit_selection_observed: PENDING # requires actual DSH session
  selection_not_preseeded: PARTIAL     # Mavis-direct DID pre-seed; the actual
                                      # DSH session must NOT pre-seed
  auto_select: false                   # confirmed by Mavis-direct
  auto_resolve: false                  # confirmed by Mavis-direct

provenance:
  q1_complete: true
  q2_complete: true
  q4_complete: true

negative_evidence:
  q3_bounded: true
  absolute_nonexistence_overclaim: false

entity_boundary:
  q5_preserved_or_legitimately_resolved: true

governance:
  cqc_pin_unchanged: true
  mafs_pin_unchanged: true
  main_unmodified: true
  no_architecture_expansion: true
```

The 7 PENDING / PARTIAL items are all DSH-session-mediated. The
deterministic surface is fully PASS.

**Runbook for HO + ChatGPT**:
`docs/MAFS_SKILL_1_0_DSH_SESSION_RUNBOOK.md` (this PR/commit).

---

**Status:** Mavis-direct work is complete and submitted. STOP_AND_REPORT
on the DSH-specific acceptance events. Awaiting HO/ChatGPT to run
the actual DSH session per the runbook, fill the PENDING fields,
and either `ACCEPT_HARDENING` or `STOP_AND_REVIEW`.
