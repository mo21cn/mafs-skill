# MAFS Skill 1.0 — Delivery-RA1 Summary

contract: MAFS-SKILL-1.0-DELIVERY-RA1-SELF-CONTAINED-EXACT-RUNTIME-REPRODUCIBLE-PACKAGE-v0.1
deliverer: Local Claw (Mavis)
delivery_date: 2026-09-02

> **STATUS WORKFLOW**
>
> This RA1 Summary is a structured audit trail derived from machine
> evidence and CI facts. It is **not** the source of truth. The
> canonical current acceptance truth is:
> - `docs/MAFS_SKILL_1_0_DELIVERY_RA1_METRICS.json`
>
> The metrics file declares an `acceptance_stage` field:
> - `PUSH_A_PREBIND` — implementation commit; CI-evidence fields may
>   carry `NOT_EVALUATED_PENDING_PUSH_A` per the explicit whitelist
>   (HO+ChatGPT Push-A Remediation authorization, 2026-09-02)
> - `FINAL_BOUND` — Push B; every CI-evidence field must be
>   concretely bound and PASS

---

## A. RA1 reason

The first portable-delivery implementation proved the architecture
was viable but did not satisfy the actual software-delivery
boundary. The measured failures (F1–F8) were recorded in the RA1
contract §0.

## B. Before / After architecture

**Before (v0):**

```text
portable repo
→ install only Skill prose/core
→ installed Skill points back to repo bootstrap
→ user repo may become executable runtime
→ ZIP depends on build-environment metadata
→ CI proves source checkout, not portable artifact
```

**After (RA1):**

```text
portable ZIP
→ self-contained installed Skill
→ installed bootstrap (resolver + doctor + baseline truth + shared predicate)
→ isolated managed exact runtime
→ resolver/doctor single truth (one shared predicate)
→ deterministic product bytes
→ portable-only CI (extract → install from extracted → execute)
→ truthful machine acceptance (verifier fail-closed)
```

## C. Installed Skill surface (RA1 §4)

After install at `<agent-skill-root>/mafs-skill-1-0/`:

```text
mafs-skill-1-0/
├── SKILL.md
├── VERSION (1.0.0)
├── agents/openai.yaml
├── references/{BASELINES, CQC_ARTIFACT_CHAIN,
                MAFS_RUNTIME_BOUNDARY, AUTHORITY_RULES}.md
├── release/BASELINES.json
└── scripts/
    ├── _runtime_truth.py            shared executable-runtime predicate
    ├── resolve_runtime_dependencies.py
    └── doctor.py
```

The installed Skill is **operational even if the original source
package, the portable ZIP, or the development repository is deleted**
(RA1 §4). All 11 required paths are mechanically verified by
`install.py` post-install.

## D. Managed runtime semantics (RA1 §8, §10)

User-supplied `MAFS_CQC_REPO` / `MAFS_ENGINE_REPO` are **acquisition
sources only**, never the executable `resolved_path`. The executable
CQC and MAFS paths always live under:

```text
~/.mafs/skill-1.0/repos/mafs-cqc/
~/.mafs/skill-1.0/repos/mafs-v3-p0/
```

A managed dependency is executable iff all of (RA1 §10):

```text
1. path is under the managed runtime home
2. HEAD == required 40-char SHA
3. tracked worktree bytes are clean against HEAD
```

(`git diff --quiet HEAD --` && `git diff --cached --quiet HEAD --`)

## E. Resolver / Doctor single truth (RA1 §11)

Both scripts share `scripts/_runtime_truth.executable_runtime_predicate`.
No case exists where the resolver reports `READY` while the doctor
reports `BLOCKED` for the same managed-runtime state.

## F. Portable-only clean-machine proof (RA1 §7)

`tests/test_ra1_install_self_contained.py::test_t3_portable_only_install_reaches_runtime_ready`
builds a deterministic portable ZIP, extracts it into an isolated
temp directory, runs `install.py FROM THE EXTRACTED PACKAGE`, and
asserts the installed Skill contains the full runtime companion set.

The CI workflow (`.github/workflows/delivery-ci.yml`) does the same
in a real GitHub Actions runner and additionally runs the installed
resolver + doctor against the real `b34a122...` and `cd09699...`
commits fetched from GitHub.

## G. Reproducible ZIP proof (RA1 §15)

`tests/test_ra1_zip_reproducible.py::test_t11_repeated_local_build_same_sha`
asserts that two consecutive local builds of the same committed
product bytes produce **byte-identical** ZIP bytes and identical
SHA-256.

Normalizations applied (RA1 §15):

```text
file ordering                sorted by arcname
POSIX archive paths          forward slashes only
ZIP timestamps               fixed (1980-01-01 00:00:00)
ZIP creator system           fixed (0 = MS-DOS / FAT)
external_attr / file perms   fixed (0o644)
compression                  ZIP_DEFLATED + compresslevel 9
filename encoding            UTF-8 (no host codepage leak)
directory entries            not emitted (member-only)
```

Canonical portable SHA256 (local reproduction):

```text
2131b1501647f822972a4c5a9aa26ce10834807fccab2f782b2a6acb9e8a5f9b
```

Size: **42,276 bytes** (machine bytes, not human-readable rounding).

## H. Linux / Windows CI evidence (RA1 §18, §19, §20)

```text
delivery-ci run 33585474656
  - delivery (ubuntu-latest)   in 24s   success
  - delivery (windows-latest)  in 24s   success
```

All 11 substantive steps PASS on both platforms (build → install →
resolver materialize → doctor RUNTIME_READY → verify_delivery → tests).

### Cross-platform reproducibility finding (recorded honestly)

The committed canonical SHA, the local reproduction SHA, and the
two CI rebuilt SHAs are four distinct values:

```text
canonical (committed):   2131b1501647f822972a4c5a9aa26ce10834807fccab2f782b2a6acb9e8a5f9b
local reproduction:      2131b1501647f822972a4c5a9aa26ce10834807fccab2f782b2a6acb9e8a5f9b  (matches canonical)
windows CI rebuild:     bb9e9c2ab853849c1c958ac7f0011f23204bfb0eef4d48a925ce17d7d69cbef2
ubuntu CI rebuild:      e6292b251f4bb187ff40e4b36e4cbf9d49f09b3ab30c56d1972fe8199dd18b71
```

Local reproducibility (two consecutive local builds) PASSES.
Cross-platform reproducibility FAILS.

### Root cause

The portable ZIP includes `__pycache__/*.pyc` files written to
the working tree when Python imports the installed scripts during
the CI install / verify step. Different Python builds (Linux
CPython 3.11.16 vs Windows CPython 3.11.9) produce different
cpython-3X bytecode, which changes the ZIP SHA. The `.pyc` files
are gitignored but exist in the working tree at ZIP build time
and are walked by `build_release.py`.

### Resolution status

`build_release.py` is in the do-not-modify list per the
HO+ChatGPT second bounded CI remediation authorization. A fix
that excludes `__pycache__/` from the source walk is a one-line
change but is not in scope for this Push B. The metrics file
records `cross_platform_zip_sha_equal: false` and includes a
`_push_b_evidence_notes` section explaining the cause.

Local-only reproducibility is asserted via
`reproducible_build_local_pass: true` (verified by
`tests/test_ra1_zip_reproducible.py::test_t11_repeated_local_build_same_sha`).

## I. User-repo no-mutation evidence (RA1 §9, §13)

`tests/test_ra1_resolver_doctor.py::test_t5_user_repo_remains_unmodified`
asserts that a user-supplied repository on a wrong commit retains its
HEAD and worktree bytes unchanged after a resolver run. The
executable-runtime predicate forbids a user override from being the
`resolved_path`.

## J. Canonical machine truth (RA1 §22, §24)

Canonical current acceptance truth is the metrics file referenced at
the top of this document. The v0 metrics and summary files are
preserved as governance audit trail only and carry explicit
`SUPERSEDED_BY_DELIVERY_RA1` markers.

| Field | FINAL_BOUND (Push B) Value |
|---|---|
| `acceptance_stage` | `FINAL_BOUND` |
| `installed_skill_self_contained` | `true` |
| `portable_only_install_pass` | `true` |
| `installed_resolver_invoked` | `true` |
| `installed_doctor_invoked` | `true` |
| `runtime_ready_pass` | `true` |
| `managed_runtime_only` | `true` |
| `user_override_never_executable` | `true` |
| `resolver_doctor_truth_consistent` | `true` |
| `wrong_repo_no_mutation_pass` | `true` |
| `tracked_runtime_dirty_detection_pass` | `true` |
| `portable_zip_built` | `true` |
| `portable_zip_sha256` | `2131b1501647f822972a4c5a9aa26ce10834807fccab2f782b2a6acb9e8a5f9b` |
| `portable_zip_size_bytes` | `42276` |
| `portable_zip_internal_manifest_pass` | `true` |
| `portable_zip_internal_shasums_pass` | `true` |
| `reproducible_build_local_pass` | `true` |
| `cross_platform_zip_sha_equal` | `false` (see §H root cause) |
| `evidence_commit` | `627afcad75689c44165544cca8deaccc2b54ef5a` (Push A remediation) |
| `linux_ci.run_id` | `33585474656` |
| `linux_ci.status` | `success` |
| `linux_ci.rebuilt_zip_sha256` | `e6292b251f4bb187ff40e4b36e4cbf9d49f09b3ab30c56d1972fe8199dd18b71` |
| `linux_ci.portable_only_install_pass` | `true` |
| `linux_ci.runtime_ready_pass` | `true` |
| `windows_ci.run_id` | `33585474656` |
| `windows_ci.status` | `success` |
| `windows_ci.rebuilt_zip_sha256` | `bb9e9c2ab853849c1c958ac7f0011f23204bfb0eef4d48a925ce17d7d69cbef2` |
| `windows_ci.portable_only_install_pass` | `true` |
| `windows_ci.runtime_ready_pass` | `true` |
| `codex_install_layout_pass` | `true` |
| `codex_discovery_smoke_status` | `NOT_EVALUATED_BY_CI` |
| `live_scientific_search_executed` | `false` |
| `cqc_production_modified` | `false` |
| `mafs_production_modified` | `false` |
| `repository_integration_path` | `PATH_C` |
| `governance_deviation_recorded` | `true` |

`verify_delivery.py` enforces the stage discipline: a `PUSH_A_PREBIND`
commit may carry `NOT_EVALUATED_PENDING_PUSH_A` only on the explicit
whitelist above (CI-evidence fields + the cross-platform equality
field + Push-A identity). Any other field carrying a PENDING marker
remains a hard failure. A `FINAL_BOUND` commit must have every
CI-evidence field concretely bound.

In FINAL_BOUND, `cross_platform_zip_sha_equal: false` is the
recorded state. The `verify_delivery.py` gate will report FAIL on
that field. The metrics file's `_push_b_evidence_notes` documents
the root cause (`.pyc` files in the ZIP). The resolution is
deferred (build_release.py is in the do-not-modify list).

## K. Governance deviation record (RA1 §2)

The previous v0 delivery candidate was merged to `main` (commits
`1b582f5` / `e70f9a2` / `7dcfd5f`) before HO+ChatGPT acceptance.
Per RA1 contract §2, this is recorded as:

```text
RECORDED_GOVERNANCE_DEVIATION:
  delivery candidate merged before HO+ChatGPT acceptance;
  no authorization precedent is established.
```

The merged commits are **not** reverted, force-pushed, rewritten, or
squashed. They remain in `main` history. RA1 supersedes them with a
normal history-preserving correction on `dev/1.0-delivery-ra1`.

The v0 delivery docs (`MAFS_SKILL_1_0_DELIVERY_SUMMARY.md`,
`MAFS_SKILL_1_0_DELIVERY_METRICS.json`,
`MAFS_SKILL_1_0_RETURN_NOTE.md`) are preserved but explicitly marked
`SUPERSEDED_BY_DELIVERY_RA1`. No v0 field is canonical current truth.

## L. Earned / Not Earned

**Earned in RA1:**

- installed Skill is self-contained; the resolver/doctor live next to the SKILL.md on disk
- managed runtime is the only executable truth; user overrides are acquisition sources
- resolver and doctor share one predicate; no silent disagreement
- portable ZIP is byte-reproducible across consecutive local builds
- verify_delivery.py is fail-closed; no hard-coded PASS claims
- CI extracts + installs + executes from the portable artifact, not the dev checkout
- structured Summary is the audit-trail view; metrics remain the source of truth

**Not earned in RA1:**

- actual Codex discovery (an external human Codex session invoking the installed Skill) — `NOT_EVALUATED_BY_CI`
- the real GF scientific replay — explicitly belongs to the next HO step (`HO_REAL_SCENARIO_REPLAY`)
- live scientific search during acceptance — forbidden
- GitHub Release / marketplace / package publication — separately authorized

## M. Original blockers F1–F8

| # | Before Problem | After Meaning | Machine Evidence | Closure Status |
|---|---|---|---|---|
| **F1** | Installed Skill did not contain the bootstrap companion it instructed the agent to call. | The installed Skill carries `scripts/resolve_runtime_dependencies.py`, `scripts/doctor.py`, and `scripts/_runtime_truth.py` next to its SKILL.md. The bootstrap gate references installed paths only. | T1 (`tests/test_ra1_install_self_contained.py`), T2 (in-process import of installed `_runtime_truth`). | CLOSED |
| **F2** | "clean-machine materialization" and "Codex discovery" could pass without proving the named event actually occurred. | The RA1 acceptance gates assert specific state transitions (managed CQC path exists, HEAD == pin, doctor reports `RUNTIME_READY`), not just process exit code. | T3, T4, T6, T7. | CLOSED |
| **F3** | User override with wrong HEAD but containing the pinned commit object could be returned as READY executable runtime. | The executable-runtime predicate checks `is_under_managed_home`; a user-supplied override is at most an acquisition source. The resolver and doctor never return the override as `resolved_path`. | T4, T5, T8. | CLOSED |
| **F4** | The portable ZIP was not reproducible across build environments. | ZipInfo normalization (fixed DOS time, create_system, external_attr, compression level, sorted order, UTF-8, no directory entries) makes two consecutive local builds byte-identical. | T11, T14. | CLOSED (local); cross-platform gate is PENDING_PUSH_A |
| **F5** | CI named "install from portable zip" did not actually install and execute from the extracted portable package. | The CI workflow copies the ZIP into an isolated temp directory, extracts it, runs `install.py FROM THE EXTRACTED ZIP`, then invokes the installed Skill's resolver and doctor. | `.github/workflows/delivery-ci.yml` §19 | CLOSED (locally); CI verification PENDING_PUSH_A |
| **F6** | Canonical Metrics / Summary contained stale or contradicted delivery truth. | The v0 docs are explicitly marked `SUPERSEDED_BY_DELIVERY_RA1`. The only canonical current acceptance pair is the RA1 METRICS + RA1 SUMMARY. | T15 (`tests/test_ra1_zip_reproducible.py`). | CLOSED |
| **F7** | `verify_delivery.py` contained asserted / hard-coded acceptance truth rather than mechanically earned truth. | The verifier reads the metrics file, derives what it can locally (zip exists, sha matches, internal manifest / shasums present), and emits `NOT_EVALUATED` for fields without evidence. It returns non-zero if any REQUIRED field is false or not evaluated. | T10 (test_t10_required_false_returns_nonzero, test_t10_required_missing_returns_nonzero, test_t10_live_scientific_search_true_fails). | CLOSED |
| **F8** | The previous delivery candidate was merged to main before HO+ChatGPT acceptance. | Per RA1 contract §2, the merge is recorded as a `RECORDED_GOVERNANCE_DEVIATION` and is **not** treated as authorization precedent. RA1 is the correct history-preserving correction. The `dev/1.0-delivery-ra1` branch is created; this contract does **not** authorize a merge to main. | `docs/MAFS_SKILL_1_0_DELIVERY_RA1_METRICS.json` `governance_deviation_recorded: true`; `docs/MAFS_SKILL_1_0_DELIVERY_RA1_SUMMARY.md` §K. | CLOSED |

## N. Final RA1 status / Recommended next step

```text
RA1 status:    RA_REQUIRED   (one open product issue remains)
                 | BLOCKED
```

Push A (initial) evidence commit: `0541a90ec29a1adbd9483a5f5ce52c4df3d984b9`
Push A (remediation) evidence commit: `11b5853c171fb7d3e8703579218892af5b366b04`
Push A (CI pattern) evidence commit: `627afcad75689c44165544cca8deaccc2b54ef5a`
Push A CI run: `33585474656`  (ubuntu + windows both success)
Push B evidence commit: **PENDING_PUSH_B** (this commit)

The one open product issue is the cross-platform reproducibility
gap (see §H): the committed portable ZIP and the two CI rebuilt
ZIPs have different SHAs because the ZIP includes `__pycache__/*.pyc`
files. Local reproducibility is verified; cross-platform is not.

Push B is the final evidence-binding commit. It must NOT alter
product/runtime bytes (per the second bounded CI remediation
authorization).

Recommended next step: **`HO_REAL_SCENARIO_REPLAY`** (after
HO+ChatGPT accept this RA1 delivery) **or** **`DELIVERY_RA2`**
(if a second RA cycle is needed to fix the `__pycache__/`
exclusion in `build_release.py`).

— Local Claw / Mavis
