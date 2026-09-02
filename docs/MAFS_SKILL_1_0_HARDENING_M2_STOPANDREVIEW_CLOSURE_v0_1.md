# MAFS Skill 1.0 — STOP_AND_REVIEW Closure Evidence (per PHASE 2 调修建议书 §6)

> **Document Type:** STOP_AND_REVIEW Closure Note
> **Source:** `PHASE 2调修建议书.txt` (per user message 2026-09-03 01:04 UTC)
> **Branch:** `dev/1.0-runtime-hardening`
> **Status:** STOP_AND_REVIEW closure complete. Awaiting `PROCEED_TO_PHASE_3` from HO + ChatGPT.
> **This document returns exactly the items listed in §6 of the STOP_AND_REVIEW advisory.**

---

## Per §6 — Return only

| §6 item | Value |
|---|---|
| **branch remote HEAD** | `95963ee6890e3193baa895a8ccc64e681082fe6a` on `dev/1.0-runtime-hardening` |
| **CI run ID** | `33659464515` |
| **Ubuntu job result** | **success** (job `100346146733`, runner `GitHub Actions 1000000419`, completed 2026-09-02T17:11:16Z) |
| **Windows job result** | **success** (job `100346147066`, runner `GitHub Actions 1000000420`, completed 2026-09-02T17:11:28Z) |
| **Ubuntu rebuilt ZIP SHA** | `a0c1cc6cef0947bdd1f4719f7d4ebb9252236c9f71cb544cd8c9b6b6fba4ca7f` (from "ZIP SHA verified" line) |
| **Windows rebuilt ZIP SHA** | `a0c1cc6cef0947bdd1f4719f7d4ebb9252236c9f71cb544cd8c9b6b6fba4ca7f` (from "ZIP SHA verified" line) |
| **canonical ZIP SHA** | `a0c1cc6cef0947bdd1f4719f7d4ebb9252236c9f71cb544cd8c9b6b6fba4ca7f` |
| **current-test count/result** | **42/42 PASS** (21 RA1 + 21 Phase 2 hardening) |
| **verify_delivery result** | **PASS** (31/31, captured by CI "verify_delivery.py fail-closed gate" step) |
| **main HEAD unchanged confirmation** | `16ac1eb2f9d7dc7d0c86d77cb7e96f928df6dfd0` (verified via `git log main -1`) |

URL: https://github.com/mo21cn/mafs-skill/actions/runs/33659464515

---

## Per §4 — Required on both Ubuntu and Windows (audit)

The advisory §4 enumerated 9 required gates on each platform. Both
platforms reported all 9 as **success**:

| Gate | Ubuntu | Windows |
|---|:---:|:---:|
| portable deterministic rebuild | ✅ | ✅ |
| rebuilt SHA == canonical new SHA | ✅ | ✅ |
| portable-only installation | ✅ | ✅ |
| installed resolver | ✅ | ✅ |
| exact CQC/MAFS materialization | ✅ | ✅ |
| installed doctor RUNTIME_READY | ✅ | ✅ |
| verify_delivery | ✅ | ✅ |
| RA1 tests | ✅ (21/21) | ✅ (21/21) |
| Phase-2 hardening tests | ✅ (21/21) | ✅ (21/21) |

**Cross-platform reproducibility confirmed**: both Ubuntu and
Windows independently rebuilt the portable ZIP from the same source
tree and produced **byte-identical** SHA
`a0c1cc6cef0947bdd1f4719f7d4ebb9252236c9f71cb544CD8C9B6B6FBA4CA7F`.

---

## Per §5 — Stale-test classification resolution

The advisory §5 required explicit resolution of pre-existing tests
that referenced v0 API surfaces. Per option (1), four tests were
**moved** out of the active acceptance surface:

| Original path | New path | Reason |
|---|---|---|
| `tests/test_delivery_truth.py` | `tests/legacy_v0/delivery_truth_v0_legacy.py` | `verify_delivery.check_skill_core_files` / `install.read_version` / `install.REQUIRED_FILES` no longer exist |
| `tests/test_install.py` | `tests/legacy_v0/install_v0_legacy.py` | Pre-dates `dsh` / `dsh-desktop` targets and `LEGACY_SKILL_SHADOWING_DETECTED` |
| `tests/test_portable_deployment.py` | `tests/legacy_v0/portable_deployment_v0_legacy.py` | Same v0 API mismatch as `delivery_truth_v0_legacy.py` |
| `tests/test_runtime_resolver.py` | `tests/legacy_v0/runtime_resolver_v0_legacy.py` | Tests renamed / removed internals of `resolve_runtime_dependencies.py` (`REPOS_DIR`, `git_head_sha`) |

The new file names drop the `test_` prefix so
`unittest discover -p "test_*.py"` (used by `tests/run_local_acceptance.py`
and by the CI workflow) no longer picks them up. A
`tests/legacy_v0/README.md` documents the move, the rationale, and
the correct procedure to re-promote a legacy test (which requires
**repairing the test body**, not just renaming it back).

This is recorded in commit `95963ee` ("M2.G: stale-test
classification + CI hardening test step"). The CI workflow
`.github/workflows/delivery-ci.yml` was also extended with a
"Phase 2 hardening tests" step that runs the four new hardening
test files by name; that step passed on both Ubuntu and Windows.

---

## Per §7 — STOP discipline

The advisory §7 mandated:

> "Do not deploy to DSH yet. Do not run GF replay yet. Do not merge
> main."

Confirmed:

- `install.py --target dsh` is **not** invoked in this evidence
  closure. The `--target dsh` / `--target dsh-desktop` choice is
  added to `install.py` (per advisory §2.3 / §3.D / §3.E) but no
  `install.py` invocation against the user's live
  `%APPDATA%\dsh-desktop\harness\skills\` happens. The DSH Desktop
  continues to use the pre-Phase-2 build that was deployed in
  the original session.
- **GF regression replay is NOT run.** No `mafs_gf_search_v2/`
  workspace is created. No DSH session is restarted. No
  `DSHIntegrationTrace v2` is generated. Per advisory §11, these
  are Phase 3 steps, gated on the present closure.
- **main is NOT merged.** `git log main..HEAD --oneline` shows 7
  commits on `dev/1.0-runtime-hardening`; `git log main -1` shows
  `16ac1eb2…` unchanged. The history-preserving merge
  `dev/1.0-runtime-hardening` → `main` is deferred to Phase 3
  per advisory §12 (only after `HO + ChatGPT Final Acceptance`).

---

## Branch composition (7 commits on `dev/1.0-runtime-hardening`)

```
95963ee M2.G: stale-test classification + CI hardening test step
           (per STOP_AND_REVIEW §5)
c9ba278 M2.F: Phase 2 evidence gate return note (per advisory section 10)
51b070c M2.E: rebuild portable ZIP + Phase 1 audit document
bd9a56b M2.D: regression tests for Phase 2 hardening contracts
f079d81 M2.C: skill-layer provenance / report / lineage / DSH additions
d3e4aff M2.B: install.py dsh/dsh-desktop target + SKILL.md description +
              LEGACY_SKILL_SHADOWING_DETECTED
cc802e7 M2.A: subprocess DEVNULL for git --version probes + .gitignore hygiene
```

---

## Red lines preserved (per advisory v0.2 §13 / §15)

- CQC pin `b34a12295bb4522ff027724630f244f2438c19e6` — unchanged
  (verified against `~/.mafs/skill-1.0/repos/mafs-cqc` HEAD on this
  machine).
- MAFS pin `cd09699fc8cc160ab5cfff00a41e714961dd2109` — unchanged
  (verified against `~/.mafs/skill-1.0/repos/mafs-v3-p0` HEAD on
  this machine).
- `main` HEAD: `16ac1eb2f9d7dc7d0c86d77cb7e96f928df6dfd0` — unchanged
  (verified via `git log main -1`).
- CQS / SRP / BudgetEnvelope / MAFS business semantics: untouched
  (the new code is skill-layer compatibility + new references/
  templates, not a re-architecture).
- No new EvidenceLandscapePackage, ROC, or new scientific planner
  was introduced.
- No `auto ranker`, `auto candidate selection`, or `auto resolve`
  was introduced. The STOP cognitive checkpoint and the
  human-explicit-selection flow are preserved (verified by
  `tests/test_provenance_retry.py`).
- `capture_output=True → DEVNULL` was applied to **exactly 2 calls**
  (the `git --version` probes in `doctor.py` and
  `resolve_runtime_dependencies.py`, in both inner and outer
  copies). The other 10 `subprocess.run` calls in the deployed
  skill preserve `capture_output=True` because they participate
  in commit identity / pin verification / remote availability /
  runtime diagnosis. **No blanket conversion was performed.**
- DSH-specific allowlist / sandbox tier configuration is **not**
  in core `SKILL.md`; it lives in
  `skill/mafs-skill-1-0/references/DSH_DEPLOYMENT.md` (isolated
  adapter per advisory §4).

---

## Decision request to HO + ChatGPT

The STOP_AND_REVIEW closure is complete. Per advisory §7, the next
action is the HO + ChatGPT evidence review of this closure. The
advisory §10 of v0.2 said `PROCEED_TO_PHASE_3` or `STOP_AND_REVIEW`
is the decision; this document supplies the §6 inputs that the
decision requires.

If `PROCEED_TO_PHASE_3`:
- Phase 3.1: `install.py --target dsh` to deploy the new
  `a0c1cc6c…` ZIP into the live DSH skills directory.
- Phase 3.2: restart the dsh daemon to hot-reload the skill.
- Phase 3.3: re-run the GF/EM narrative with the same task
  prompt as the original session. Capture the new artifacts in a
  new `mafs_gf_search_v2/` workspace.
- Phase 3.4: extract `DSHIntegrationTrace v2` from the new
  session. Compare semantic state (per advisory §6 / §7) — NOT
  byte-level JSON hashes.
- Phase 3.5: validate provenance closure (Q1/Q4 evidence_id +
  resolver_invocation_id present), bounded language (Q3 row
  uses "no canonical candidate recovered under the bounded
  search" + "likely conflation"), STOP behavior (ask_user_question
  observed), no auto-select, no auto-resolve.
- Phase 3.6: write the Phase 3 closeout return note.
- Phase 3.7: history-preserving merge `dev/1.0-runtime-hardening`
  → `main` (`--no-ff`), only after `HO + ChatGPT Final
  Acceptance`.

If `STOP_AND_REVIEW` (a second time): the advisory should name
the additional items to address before another evidence closure.

---

**Status:** STOP_AND_REVIEW closure COMPLETE, ready for HO +
ChatGPT review of the §6 inputs above.
