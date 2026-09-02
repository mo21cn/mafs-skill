# tests/legacy_v0/ — Superseded v0 Tests

> **Status:** These tests are **NOT** part of the current acceptance
> surface. They are preserved here for archaeological / audit purposes
> only.

## Why these are here

These four test files were written against the v0 (RA1 first
delivery) API surface. As the codebase evolved, several functions
they call were removed, renamed, or have different signatures:

| Legacy file | Reason superseded |
|---|---|
| `delivery_truth_v0_legacy.py` | Calls `verify_delivery.check_skill_core_files()` / `install.read_version()` / `install.REQUIRED_FILES` — functions that do not exist in the current API. |
| `install_v0_legacy.py` | Tests against an earlier `install.py` shape that pre-dates the `dsh` / `dsh-desktop` targets and the `LEGACY_SKILL_SHADOWING_DETECTED` check. |
| `portable_deployment_v0_legacy.py` | Same v0 API mismatch as `delivery_truth_v0_legacy.py` for `install.read_version()`. |
| `runtime_resolver_v0_legacy.py` | Tests against renamed / removed internals of `resolve_runtime_dependencies.py` (`REPOS_DIR`, `git_head_sha`); the static-guard test for `git reset --hard cwd=str(target)` reflects a v0 contract that has since been re-shaped. |

## Why they were moved (not deleted)

The `MAINTENANCE_ADVISORY_v0.2` evidence gate §5 explicitly required:

> "either explicitly mark/move superseded v0/API-mismatch tests
> outside the current acceptance surface, or if they remain
> current-contract tests, repair them. Do not silently ignore an
> ambiguous active red suite."

These tests are unambiguously **superseded**, not current-contract.
They are kept here so that:

- future refactors can compare the v0 expectations against the
  current contract
- the audit trail is preserved (the Phase 1 audit doc references
  them)
- they are NOT picked up by `unittest discover -p "test_*.py"`,
  which is the local + CI acceptance surface

## Why the names dropped the `test_` prefix

`unittest discover -s tests -p "test_*.py"` only matches files
beginning with `test_`. By dropping the prefix (`delivery_truth_v0_legacy.py`
etc.), these files are no longer discoverable by the standard
acceptance runner, and the acceptance surface reduces cleanly to:

- `tests/test_ra1_*.py` — 4 files / 21 tests
- `tests/test_evidence_id_stable.py` — 6 tests
- `tests/test_provenance_retry.py` — 5 tests
- `tests/test_report_fail_closed.py` — 6 tests
- `tests/test_legacy_shadow.py` — 4 tests

Total: 8 active test files / 42 tests, all green.

## To restore a legacy test to the active surface

If a future refactor makes one of these tests current again, the
correct procedure is:

1. **Repair** the test against the current API (do NOT just rename
   it back to `test_*.py` without updating the body).
2. Add it to the `delivery-ci.yml` "Unit / regression tests" step.
3. Update the `run_local_acceptance.py` globs if needed.
4. Move it out of `legacy_v0/`.

Do not promote a legacy test to the active surface without repair;
that would silently re-introduce v0 API expectations.
