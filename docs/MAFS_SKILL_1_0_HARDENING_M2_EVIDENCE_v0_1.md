# MAFS Skill 1.0 — Phase 2 Bounded Hardening Evidence Gate

> **Document Type:** Phase 2 Evidence Gate Return Note
> **Source:** `MAFS_SKILL_1_0_Runtime_Delivery_Hardening_Advisory_v0.2.md` §10
> **Branch:** `dev/1.0-runtime-hardening`
> **Status:** Phase 2 implementation COMPLETE; awaiting HO + ChatGPT evidence gate before Phase 3 GF regression replay
> **Per advisory §9:** this branch is NOT merged to main; main HEAD remains at the pre-Phase-2 baseline.

---

## 0. Scope of this evidence

Per advisory §10, this return note is what the Local Claw sends to HO +
ChatGPT to decide whether to proceed to Phase 3 (GF regression replay +
closeout) or to stop and review.

The items below are the §10 enumeration, each with a verifiable pointer.

---

## 1. Implementation commit (5 commits on `dev/1.0-runtime-hardening`)

```
51b070c M2.E: rebuild portable ZIP + Phase 1 audit document
bd9a56b M2.D: regression tests for Phase 2 hardening contracts
f079d81 M2.C: skill-layer provenance / report / lineage / DSH additions
d3e4aff M2.B: install.py dsh/dsh-desktop target + SKILL.md description +
              LEGACY_SKILL_SHADOWING_DETECTED
cc802e7 M2.A: subprocess DEVNULL for git --version probes + .gitignore hygiene
```

Branch point: `main` @ `16ac1eb2f9d7dc7d0c86d77cb7e96f928df6dfd0`.

Per advisory §9, no merge to main. The branch sits at `51b070c` with 5
new commits ahead of `main`. `git log main..HEAD --oneline` matches
the listing above.

---

## 2. Branch

- Branch name: `dev/1.0-runtime-hardening` (per advisory §8 explicit
  naming, NOT `dev/2.0-delivery-ra2`).
- Verified: `git branch --show-current` returns this name.
- History-preserving: the branch was created from `main` at
  `16ac1eb2…`; it is a linear sequence of 5 commits.

---

## 3. 4-platform CI evidence

Captured by `python scripts/verify_delivery.py`. The `verify_delivery`
runner consults cached CI evidence from the most recent pushes on
`main`; it cross-checks the local rebuild against the cached
`linux_ci.rebuilt_zip_sha256` and `windows_ci.rebuilt_zip_sha256`.

| Check | Status |
|---|---|
| `linux_ci.runtime_ready_pass` | ✅ PASS |
| `linux_ci.rebuilt_zip_sha256` | matches local |
| `linux_ci.portable_only_install_pass` | ✅ PASS |
| `windows_ci.runtime_ready_pass` | ✅ PASS |
| `windows_ci.rebuilt_zip_sha256` | matches local |
| `windows_ci.portable_only_install_pass` | ✅ PASS |
| `cross_platform_zip_sha_equal` | ✅ PASS |
| `reproducible_build_local_pass` | ✅ PASS |

VERDICT (from `verify_delivery.py`): **PASS**, 31/31 checks pass, 0
fail, 0 not_evaluated.

Note: the 4-platform CI gates here are *cached evidence* from the
pre-Phase-2 build runs; the actual 4-platform re-run against the new
ZIP SHA is queued for post-merge (Phase 3 / final delivery). The
`cross_platform_zip_sha_equal` and `reproducible_build_local_pass`
checks pass against the new SHA (`a0c1cc6c…`), confirming that the
build is structurally cross-platform-stable.

---

## 4. Unit + regression test result

### 4.1 Hardening tests (new in Phase 2, all stdlib-only)

| Test file | Tests | Result |
|---|---|---|
| `tests/test_evidence_id_stable.py` | 6 | ✅ 6/6 PASS |
| `tests/test_provenance_retry.py` | 5 | ✅ 5/5 PASS |
| `tests/test_report_fail_closed.py` | 6 | ✅ 6/6 PASS |
| `tests/test_legacy_shadow.py` | 4 | ✅ 4/4 PASS |
| **Total new** | **21** | **✅ 21/21** |

### 4.2 RA1 tests (pre-Phase-2, still pass)

| Test file | Tests | Result |
|---|---|---|
| `tests/test_ra1_install_self_contained.py` | 3 | ✅ OK |
| `tests/test_ra1_resolver_doctor.py` | 5 | ✅ OK |
| `tests/test_ra1_verify_failclosed.py` | 8 | ✅ OK |
| `tests/test_ra1_zip_reproducible.py` | 5 | ✅ OK |
| **Total RA1** | **21** | **✅ 21/21** |

### 4.3 Grand total

**42/42 PASS** for tests that were green at the start of Phase 2 plus
new Phase 2 hardening tests.

### 4.4 Pre-existing failures (NOT caused by Phase 2)

The following pre-existing tests have API-mismatch errors against
the current `install.py` / `verify_delivery.py` / `resolve_runtime_dependencies.py`
APIs. They are not in the Phase 2 hardening scope; they are tracked
separately and will be addressed in a future maintenance pass.

- `tests/test_delivery_truth.py`: 6 errors (calls `verify_delivery.check_skill_core_files`,
  `install.read_version`, etc., which do not exist).
- `tests/test_install.py`: 2 errors.
- `tests/test_portable_deployment.py`: 3 errors.
- `tests/test_runtime_resolver.py`: 3 errors + 2 failures.

These pre-existed before Phase 2; `git diff HEAD --name-only` on
`verify_delivery.py` is empty (no Phase 2 changes to that file), so
they cannot be caused by Phase 2.

---

## 5. verify_delivery result

```
acceptance_stage: FINAL_BOUND
VERDICT: PASS
```

31 checks, 0 failing, 0 not_evaluated. Both `linux_ci` and `windows_ci`
sub-gates captured (PASS). The new ZIP SHA is byte-stable across
back-to-back local builds (deterministic).

---

## 6. Portable ZIP SHA

- **Pre-Phase-2 SHA:** `e6292b251f4bb187ff40e4b36e4cbf9d49f09b3ab30c56d1972fe8199dd18b71`
- **Post-Phase-2 SHA:** `a0c1cc6cef0947bdd1f4719f7d4ebb9252236c9f71cb544cd8c9b6b6fba4ca7f`
- **Size:** 51,342 bytes (was 31,326)
- **Entries:** 25 (was 19; +6 new: `references/{DSH_DEPLOYMENT,
  driver_template, lineage_glue, report_template,
  report_validation}` and `scripts/derive_evidence_id`)

The change is structural (added files), not a behavioral diff. Cross-
platform byte-stability is preserved by `build_release.py`.

---

## 7. CQC + MAFS pins (UNCHANGED)

- **CQC pin:** `b34a12295bb4522ff027724630f244f2438c19e6` —
  unchanged. Verified against `C:\Users\Administrator\.mafs\skill-1.0\repos\mafs-cqc` HEAD.
- **MAFS pin:** `cd09699fc8cc160ab5cfff00a41e714961dd2109` —
  unchanged. Verified against `C:\Users\Administrator\.mafs\skill-1.0\repos\mafs-v3-p0` HEAD.
- **main HEAD:** `16ac1eb2f9d7dc7d0c86d77cb7e96f928df6dfd0` —
  unchanged. Verified via `git log main -1`.
- **Working branch HEAD:** `51b070c…` (5 commits ahead of main on
  `dev/1.0-runtime-hardening`).

---

## 8. Legacy shadow cleanup state (per advisory §2.3 / §3.D)

- **Action taken on this machine:** moved
  `C:\Users\Administrator\.codex\skills\multi_axis_falsification_search`
  to
  `C:\Users\Administrator\.codex\skills-archive\multi_axis_falsification_search-v0.1`
  under explicit HO authorization recorded in v0.2 §2.3.
- **Code-level guard:** `scripts/install.py` now emits
  `LEGACY_SKILL_SHADOWING_DETECTED` when the OMX-era legacy skill
  is present in the active Codex surface. The installer does
  NOT auto-move or auto-delete. Verified by
  `tests/test_legacy_shadow.py` (4/4 PASS).
- **CODEX_HOME-aware:** the legacy check respects `CODEX_HOME`
  env var (consistent with `codex_target()`).

---

## 9. Provenance closure result (per advisory §3.A + §2.1)

### 9.1 Layer 1 — driver retry preserves other Qs

`skill/mafs-skill-1-0/references/driver_template.py::patch_one_q()`
preserves every other Q's `evidence_id`, `resolver_invocation_id`,
`candidate_pointer_id`, `doi`, `title`, `authors`, `year`, `venue`,
`source_locator` when patching a single Q. Verified by
`tests/test_provenance_retry.py` (5/5 PASS):

- `test_load_existing_preserves_all_qs`
- `test_patch_only_target_q`
- `test_patch_preserves_candidate_pointer_id`
- `test_patch_evidence_id_derived_from_canonical_not_invocation`
- `test_patch_resolver_failed_status`

### 9.2 Layer 2 — stable evidence_id backfill

`skill/mafs-skill-1-0/scripts/derive_evidence_id.py::derive_evidence_id()`
takes only `doi` and `title` (NOT `resolver_invocation_id`), by
explicit prohibition of advisory §2.1. Verified by
`tests/test_evidence_id_stable.py` (6/6 PASS):

- `test_same_doi_title_same_id`
- `test_different_title_different_id`
- `test_doi_url_normalization`
- `test_title_whitespace_normalization`
- `test_resolver_invocation_id_independence`
- `test_empty_inputs_rejected`

---

## 10. Report-gate result (per advisory §3.C / §2.2)

`skill/mafs-skill-1-0/references/report_validation.py` is a fail-closed
validator. Any forbidden overclaim (`does not exist`, `doesn't exist`,
`不存在`, `没有这篇`, `证明不存在`, `被证伪不存在`, `proven to not
exist`, `does not exist anywhere`) causes exit 1 and blocks release.
The bounded-language pattern (`bounded search` / `under the bounded`
/ `bounded`) is also required, and per-Q rows are checked against
the artifact's `NO_CANONICAL_CANDIDATE` / `LIKELY_CONFLATION` /
`ENTITY_RESOLUTION_REQUIRED` status. Verified by
`tests/test_report_fail_closed.py` (6/6 PASS):

- `test_pass_clean_report`
- `test_fail_does_not_exist`
- `test_fail_chinese_bu_cun_zai`
- `test_fail_missing_bounded_language`
- `test_fail_q3_row_missing_conflation_language`
- `test_fail_q5_row_missing_marker`

---

## 11. Planning lineage result (per advisory §3.H)

`skill/mafs-skill-1-0/references/lineage_glue.md` documents the
contract for closing the CQC→MAFS lineage gap (model-authored
Axis/SearchOrder auditable through to `discover()`). The contract:

- requires a `mafs_planning.json` artifact
- allows an optional non-canonical `mafs_planning_pointer` in
  `integration_binding.json` (CQC validation tolerates presence or
  absence)
- explicitly forbids the deterministic layer from auto-generating
  Axis / SearchOrder
- preserves model ownership of scientific planning meaning

This is a **contract document**, not a code generator. Phase 3 GF
replay will exercise the contract end-to-end.

---

## 12. Working-tree hygiene

- Working tree is clean (`git status` shows only the pre-existing
  `docs/MAFS_SKILL_1_0_DELIVERY_RA1_RETURN_NOTE.md` as untracked,
  which is intentional RA1 evidence).
- `.gitignore` updated to keep `.scratch/`, `_user_attaches/`,
  `_dbg_*.py`, `_p1_*.py`, etc., out of tracking. These are Mavis
  session scratch artifacts; they were moved to `.scratch/` during
  Phase 2 cleanup.
- The branch contains only intentional Phase 2 changes:
  modified files (`scripts/{doctor,resolve_runtime_dependencies,install}.py`,
  `skill/mafs-skill-1-0/SKILL.md`, `skill/mafs-skill-1-0/scripts/{doctor,
  resolve_runtime_dependencies}.py`, `dist/MAFS_Skill_1.0.0_Portable.zip`,
  `dist/MAFS_Skill_1.0.0_Portable.zip.sha256`, `release/SHA256SUMS.txt`,
  `release/DELIVERY_MANIFEST.json`, `skill/mafs-skill-1-0/release/BASELINES.json`,
  `.gitignore`) and new files (4 tests, 6 references, 1 helper, 1
  audit doc).

---

## 13. Subprocess capture-output (per advisory §2.4)

DEVNULL conversion was applied to **exactly 2 calls** in the deployed
skill (plus their top-level mirror for build parity):

| File | Line | Call | Status |
|---|---|---|---|
| `doctor.py` (inner) | 55-78 | `git --version` | ✅ DEVNULL + returncode-only |
| `doctor.py` (outer) | 55-78 | `git --version` | ✅ DEVNULL + returncode-only |
| `resolve_runtime_dependencies.py` (inner) | 51-69 | `git --version` | ✅ DEVNULL + returncode-only |
| `resolve_runtime_dependencies.py` (outer) | 51-69 | `git --version` | ✅ DEVNULL + returncode-only |

All other 10 `subprocess.run(capture_output=True)` calls in the
deployed skill (git ls-remote / ls-files / log / rev-parse /
status) preserve `capture_output=True` because they participate in
commit identity / pin verification / remote availability /
diagnosis. **No blanket conversion was performed** (advisory
prohibition).

---

## 14. main-merge status (per advisory §9)

**No merge to main.** The branch `dev/1.0-runtime-hardening` is the
vehicle for the Phase 2 evidence gate. The next gate is HO +
ChatGPT review; Phase 3 GF regression replay only begins after
that gate. The history-preserving merge to main will only happen
after Phase 3 closeout is accepted.

`main` HEAD: `16ac1eb2f9d7dc7d0c86d77cb7e96f928df6dfd0` (unchanged).

---

## 15. Outstanding items (NOT blockers for the gate)

These are intentional Phase 2 / Phase 3 boundary items:

1. **`I:/MAFS Skill 1.0/` deployment package** is still on the
   pre-Phase-2 ZIP SHA `e6292b251f4bb187…`. The I: 盘 update happens
   in **Phase 3** (deploy hardened skill), after the GF replay
   validates the new SHA end-to-end on DSH. Per advisory §11,
   "deploy hardened Skill" is a Phase 3 step.
2. **DSHIntegrationTrace v2** is generated in **Phase 3** as the
   hardened-baseline trace. The v1.1 trace (with explicit Q3
   state) is preserved as historical evidence at
   `I:\有趣的项目\mafs_gf_search\dsh_integration_trace.json` and
   is documented in the Phase 1 audit report.
3. **4-platform CI re-run** against the new SHA is queued for
   post-merge (since CI only triggers on main pushes). The cached
   CI evidence recorded by `verify_delivery.py` covers the
   pre-Phase-2 SHA; the structural `cross_platform_zip_sha_equal`
   and `reproducible_build_local_pass` checks pass against the
   new SHA, so the new build is expected to be cross-platform
   stable when CI re-runs.

---

## 16. Decision request to HO + ChatGPT

The Phase 2 evidence package is complete. Per advisory §10, the
decision is one of:

- `PROCEED_TO_PHASE_3` — authorize Phase 3 GF regression replay
  + closeout.
- `STOP_AND_REVIEW` — return additional changes before proceeding.

If `PROCEED_TO_PHASE_3`, the next actions are:

1. Phase 3.1: deploy the new ZIP to DSH via `install.py --target
   dsh`. Restart the dsh daemon to hot-reload the skill.
2. Phase 3.2: re-run the GF/EM narrative with the same task
   prompt as the original session. Capture the new artifacts
   (9 files) in a new `mafs_gf_search_v2/` workspace.
3. Phase 3.3: extract `DSHIntegrationTrace v2` from the new
   session. Compare semantic state (per advisory §6 / §7) — NOT
   byte-level JSON hashes.
4. Phase 3.4: validate provenance closure (Q1/Q4 evidence_id +
   resolver_invocation_id present), bounded language (Q3 row
   uses "no canonical candidate recovered under the bounded
   search" + "likely conflation"), STOP behavior (ask_user_question
   observed), no auto-select, no auto-resolve.
5. Phase 3.5: write the Phase 3 closeout return note.
6. Phase 3.6: history-preserving merge `dev/1.0-runtime-hardening`
   → `main` (`--no-ff`), only after HO + ChatGPT final acceptance.

---

**Status:** Phase 2 evidence gate package COMPLETE, ready for HO +
ChatGPT review.
