# MAFS Skill 1.0 — DSH Session Replay Runbook (per `MAFS-SKILL-1.0-PHASE-3-FINAL-v0.1`)

> **Audience**: HO / ChatGPT / human operator who can open a real DSH
> harness session.
> **Purpose**: Run a fresh actual DSH agent session against the
> Phase 2 hardened Skill so that the DSH-specific acceptance
> events in `MAFS-SKILL-1.0-PHASE-3-FINAL-v0.1` §5–§14 can be
> observed and recorded in `dsh_integration_trace_v3.json`.
> **Standing rule** (advisory §0): "A named acceptance event is
> PASS only if that event actually occurred. Mavis-direct ≠
> DSH-agent replay."

---

## 0. Pre-conditions (all already satisfied on this machine)

1. **Hardened Skill installed at the DSH path** (done in Phase 3 §P3.1):
   ```
   C:\Users\Administrator\AppData\Roaming\dsh-desktop\harness\skills\mafs-skill-1-0\
   ```
   Contains 17 files including `SKILL.md` (with `description` field),
   `references/DSH_DEPLOYMENT.md`, `references/driver_template.py`,
   `references/report_validation.py`, `scripts/derive_evidence_id.py`,
   `scripts/doctor.py` (DEVNULL'd), `scripts/resolve_runtime_dependencies.py` (DEVNULL'd).
   No `__pycache__`.

2. **Legacy OMX-era Skill archived** (per Phase 2 P2.D1):
   ```
   C:\Users\Administrator\.codex\skills-archive\multi_axis_falsification_search-v0.1\
   ```
   Should NOT appear in active Codex or DSH discovery. `install.py`
   still emits `LEGACY_SKILL_SHADOWING_DETECTED` if the legacy is
   present in active Codex.

3. **CQC + MAFS managed runtime ready** (verified at Phase 3 §P3.2):
   - `CQC_RESOLVER: READY` (HEAD `b34a1229` = pin)
   - `MAFS_RESOLVER: READY` (HEAD `cd09699f` = pin)
   - `OVERALL: READY` / `RUNTIME_READY` (doctor)

4. **DSH desktop version**: ≥ 0.1.1-rc.1

5. **Pre-allocated v3 artifacts in the v2 workspace** (reused, not rewritten by DSH):
   ```
   I:\有趣的项目\mafs_gf_search_v2\
   ├── mafs_planning.json            (7,796 bytes; SHA-256 d18845e1…)
   │   (this is the model-authored Axis / SearchOrder the DSH
   │    agent's skill will consume; per `lineage_glue.md` contract)
   ├── run_mafs_gf_v3.py             (planning-consuming driver; the
   │                                 DSH agent should use a similar
   │                                 consumption pattern, NOT inline
   │                                 _search_orders)
   ├── cqs.json, srp.json, budget_envelope.json, integration_binding.json
   │   (re-populated by the v3 driver; DSH agent may re-run or reuse)
   ├── discovery_candidate_pointers.json
   │   (written by the v3 driver; DSH agent may overwrite or reuse)
   ├── resolved_canonical_evidence.json
   │   (Phase 2 provenance-closure format; DSH agent may overwrite)
   └── REPORT.md
       (uses bounded language; validated by report_validation.py)
   ```

6. **`dsh_integration_trace_v3.json`** (Mavis-direct PENDING record):
   ```
   I:\有趣的项目\mafs_gf_search_v2\dsh_integration_trace_v3.json
   ```
   This is the Mavis-direct trace with PENDING fields for the
   DSH-specific acceptance events. The DSH session must overwrite
   the PENDING fields with actual values; see §4 below for the
   field-by-field schema.

---

## 1. Start the DSH session

1. Open DSH Desktop and start a new session.
2. Confirm skill discovery: in DSH's skill panel, locate `mafs-skill-1-0`.
   The skill's `description` field is:
   > "MAFS Skill 1.0 runs the CQC (P0..P5) then MAFS (P0..P3)
   > falsification-search workflow. Bootstrap gate first reads
   > release/BASELINES.json, runs resolve_runtime_dependencies.py,
   > and runs doctor.py; only then does it digest a research
   > narrative through CQS, SRP, BudgetEnvelope, and IntegrationBinding,
   > hands off to MAFS discover, STOP, explicit CandidatePointer
   > selection, and resolve."

3. The legacy `multi_axis_falsification_search` skill MUST NOT be
   selected. If DSH auto-selects it, STOP_AND_REPORT per
   advisory §6.

---

## 2. Use this exact task prompt

Paste the prompt verbatim into the DSH session:

```
调用 MAFS Skill 1.0 进行搜索任务：von Reyn et al. 2014/2020 等论文补充材料里的 GF 神经元 ID 清单
```

Do NOT modify the prompt. Do NOT pre-seed any selection (no
"select Q1, Q2, Q4" or similar). The cognitive actor (DSH human
operator) must inspect the live candidates and make the explicit
selection after STOP, per advisory §9.

---

## 3. Observe the required events (per advisory §6–§14)

| Advisory § | Event | How to observe in DSH |
|---|---|---|
| §6 | DSH discovered mafs-skill-1-0 | Skill panel shows the skill as selected |
| §7 | Runtime READY | DSH agent reports `RUNTIME_READY` after `doctor.py` |
| §7 | CQC exact pinned SHA verified | DSH agent reports `cqc.required_commit = b34a1229…` |
| §7 | MAFS exact pinned SHA verified | DSH agent reports `mafs.required_commit = cd09699f…` |
| §8 | STOP after `discover()` | DSH agent emits STOP and returns control (typically via `ask_user_question`) |
| §9 | Explicit selection by cognitive actor | DSH human-in-the-loop answer to `ask_user_question` |
| §9 | Selection NOT pre-seeded | The selected set is chosen from the current candidates, NOT from any earlier GF run |
| §10 | No auto-select | The DSH session does NOT run `top-1 auto-select` or similar |
| §10 | No auto-resolve | The DSH session does NOT run `resolve()` before explicit selection |
| §11 | Every `RESOLVED` Q carries `candidate_pointer_id` + `evidence_id` + `resolver_invocation_id` | Check `resolved_canonical_evidence.json` |
| §12 | Q3 uses bounded language (NOT "does not exist" / "不存在" / etc.) | Run `python <DSH_SKILL>/references/report_validation.py REPORT.md` |
| §13 | Q5 remains `ENTITY_RESOLUTION_REQUIRED` | Check `resolved_canonical_evidence.json` Q5 entry |
| §14 | Approval classification | Capture all `approval/asked` events with reason category |

---

## 4. Overwrite the PENDING fields in `dsh_integration_trace_v3.json`

Open `I:\有趣的项目\mafs_gf_search_v2\dsh_integration_trace_v3.json`
in a text editor. Replace each PENDING field with the actual
DSH-observed value. The PENDING field list is in
`dsh_integration_trace_v3.json::stop_and_report_conditions` and
in the field-level comments below:

| PENDING field | How to fill |
|---|---|
| `dsh_session_id` | The DSH session identifier (visible in the DSH UI / action bar) |
| `dsh_skill_discovery` | `"PASS"` (DSH found `mafs-skill-1-0`) or `"FAIL: <reason>"` |
| `runtime_ready` | `"PASS: doctor.py RUNTIME_READY at <ts> (DSH-confined-sandbox)"` |
| `stop_checkpoint_observed` | `true` if DSH agent visibly returned control after `discover()` |
| `explicit_selection_observed` | `true` if human-in-the-loop `ask_user_question` was answered |
| `selection_actor` | e.g. `"DSH human-in-the-loop via ask_user_question"` |
| `selected_question_ids` | e.g. `["Q1", "Q2", "Q4"]` (the actual selection, not pre-seeded) |
| `auto_select_observed` | `false` if selection was explicit (not top-1 auto) |
| `auto_resolve_observed` | `false` if `resolve()` was called only after explicit selection |
| `approval_total` | Integer count of `approval/asked` events |
| `approval_category_counts` | Dict mapping category name to count |

If any of the above cannot be filled (e.g., DSH cannot discover
the hardened skill, or runtime cannot reach READY), STOP_AND_REPORT
per advisory §6 / §7.

After overwriting, recompute the artifact hashes in
`artifact_hashes` if any of the JSON files changed. The
`mafs_planning.json` SHA-256 must remain
`d18845e19460662e65c42cc2339096a6fb7a923643c0068897050b71b10679b7`
because that is the artifact the driver consumed (per advisory
§16: "The driver must consume the same bytes whose hash is
recorded.").

---

## 5. Capture the new dsh_integration_trace_v3.json (final form)

The overwritten trace IS the v3 submission. Save it as the same
file (`I:\有趣的项目\mafs_gf_search_v2\dsh_integration_trace_v3.json`).
No new file is required; the Mavis-direct version is overwritten
in place.

---

## 6. Final acceptance package

The complete Phase 3-Final submission per advisory §22:

1. `docs/MAFS_SKILL_1_0_PHASE_3_FINAL_CLOSEOUT.md` (Mavis writes this; see
   next file)
2. `dsh_integration_trace_v3.json` (overwritten by the DSH session,
   with PENDING fields filled)
3. `mafs_planning.json` (Mavis already wrote; SHA-256 fixed at
   `d18845e19460662e65c42cc2339096a6fb7a923643c0068897050b71b10679b7`)
4. `resolved_canonical_evidence.json` (overwritten by the DSH agent
   after the explicit selection; the Mavis-direct v2/v3 version is
   a valid baseline)
5. `REPORT.md` (overwritten by the DSH agent; must pass
   `references/report_validation.py`)

Additional run artifacts may remain in the workspace
(`mafs_gf_search_v2/`) and in the test fixtures
(`tests/fixtures/mafs_gf_search_v2/`) for archaeology.

---

## 7. After the DSH session: submit for Final Acceptance

Send the 5 items above to HO + ChatGPT for `ACCEPT_HARDENING`
or `STOP_AND_REVIEW` per advisory §24. The acceptance standard
in advisory §25 (`yaml` checklist) is the gate.

Only after HO + ChatGPT `ACCEPT_HARDENING` may the
history-preserving merge `dev/1.0-runtime-hardening` → `main`
(`--no-ff`) be performed, per advisory §24 / §19.

---

## 8. What if the DSH session fails one of the §21 stop conditions?

If any of the following occur, STOP the DSH session immediately
and report to HO + ChatGPT:

- DSH cannot discover the hardened Skill
- legacy Skill is selected
- runtime cannot reach READY
- planning artifact requires CQC/MAFS schema change
- explicit selection requires authority redesign
- CQC pin must change
- MAFS pin must change
- new scientific planner appears necessary
- auto-selection appears necessary
- main merge is required to continue

These conditions are the §21 STOP_AND_REPORT triggers. None of
them has been observed in the Mavis-direct v3 run; the only
PENDING fields are the harness-mediated ones (DSH session events),
which require an actual DSH session to observe.

---

## 9. Why this runbook exists

The Mavis session cannot directly invoke a DSH agent. The
Mavis-direct v3 run (which produced this runbook + the v3 trace
+ the v3 driver) demonstrates that:

- The Phase 2 hardening works (RESOLVED Q1/Q2/Q4 with provenance
  closure; Q3 bounded negative; Q5 entity boundary).
- The planning artifact is correctly emitted and consumed by the
  driver (`run_mafs_gf_v3.py`).
- The deterministic surface (evidence_id stable, bounded language
  preserved, planning artifact hash recorded, CQC/MAFS pins
  unchanged) is verified.

The non-deterministic surface (DSH session events: skill discovery,
runtime READY under DSH, STOP observation, explicit selection,
auto-select/auto-resolve non-occurrence, approval classification)
requires a real DSH session. This runbook is the bridge.

---

**Runbook version**: 1.0 (Phase 3-Final)
**Source advisory**: `MAFS-SKILL-1.0-PHASE-3-FINAL-v0.1`
**Authoring**: Local Claw (Mavis)
**Date**: 2026-09-03
