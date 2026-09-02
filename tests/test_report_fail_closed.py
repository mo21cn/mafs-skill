"""test_report_fail_closed.py — regression for advisory §2.2 / §3.C.

A final REPORT.md is **fail-closed**: any forbidden overclaim
("does not exist", "不存在", "没有这篇", etc.) MUST cause the validator
to exit non-zero and block release. The validator must ALSO require
the bounded-language pattern ("bounded search" or similar) to be
present, and it must verify per-Q row alignment with the artifact
status.
"""
from __future__ import annotations

import importlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFS = HERE.parent / "skill" / "mafs-skill-1-0" / "references"
VALIDATOR = REFS / "report_validation.py"
if not VALIDATOR.is_file():  # pragma: no cover
    raise SystemExit(f"report_validation.py not found at {VALIDATOR}")


def _write_evidence(ws: Path) -> None:
    (ws / "resolved_canonical_evidence.json").write_text(json.dumps({
        "Q1": {"status": "RESOLVED",
               "doi": "10.1038/nn.3741",
               "title": "A spike-timing mechanism for action selection"},
        "Q2": {"status": "RESOLVED"},
        "Q3": {"status": "NO_CANONICAL_CANDIDATE"},
        "Q4": {"status": "RESOLVED"},
        "Q5": {"status": "ENTITY_RESOLUTION_REQUIRED"},
    }, indent=2) + "\n", encoding="utf-8")


def _run_validator(ws: Path, report_text: str) -> tuple[int, str, str]:
    (ws / "REPORT.md").write_text(report_text, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), str(ws / "REPORT.md"),
         "--workspace", str(ws)],
        capture_output=True, text=True, cwd=str(ws),
    )
    return proc.returncode, proc.stdout, proc.stderr


# ---------------- passing reports ----------------

def test_pass_clean_report() -> None:
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        _write_evidence(ws)
        report = """
# Test Report

The bounded search recovered canonical evidence for the selected Qs.

## §3. Per-question status

| Q | Question | Identity | Status |
|---|---|---|---|
| Q1 | ... | 10.1038/nn.3741 | paper identity **RECOVERED** (DOI `10.1038/nn.3741`); the source content was not re-rendered in this run. |
| Q2 | ... | ... | paper identity **RECOVERED** |
| Q3 | ... | none | no canonical candidate recovered under the bounded search; the current evidence supports likely conflation with `Scheffer 2020`. |
| Q4 | ... | ... | paper identity **RECOVERED** |
| Q5 | ... | n/a | **ENTITY_RESOLUTION_REQUIRED** — the MAFS scholarly stack has no dataset adapter for this entity class. Operator-supplied seeds are marked `HISTORICAL_ENTITY_ANCHOR_UNVERIFIED`; no entity IDs are fabricated into the resolved results. |

## §4. Honest conclusion

This run did not assert global non-existence anywhere; bounded search
absence is the only negative claim made.
"""
        rc, out, err = _run_validator(ws, report)
        assert rc == 0, f"clean report should pass: stdout={out!r} stderr={err!r}"
        assert "REPORT VALIDATION PASS" in out


# ---------------- forbidden overclaim ----------------

def test_fail_does_not_exist() -> None:
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        _write_evidence(ws)
        report = """
# Test Report

The bounded search was performed.

| Q | Question | Status |
|---|---|---|
| Q3 | ... | The von Reyn 2020 paper **does not exist**. |
| Q5 | ... | **ENTITY_RESOLUTION_REQUIRED** |
"""
        rc, out, err = _run_validator(ws, report)
        assert rc != 0, f"overclaim 'does not exist' should fail: stdout={out!r} stderr={err!r}"
        assert "FORBIDDEN_OVERCLAIM" in err
        assert "does not exist" in err


def test_fail_chinese_bu_cun_zai() -> None:
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        _write_evidence(ws)
        report = """
# Test Report

The bounded search was performed.

| Q | Question | Status |
|---|---|---|
| Q3 | ... | 这篇论文不存在。 |
| Q5 | ... | **ENTITY_RESOLUTION_REQUIRED** |
"""
        rc, out, err = _run_validator(ws, report)
        assert rc != 0, f"overclaim '不存在' should fail: stdout={out!r} stderr={err!r}"
        assert "FORBIDDEN_OVERCLAIM" in err


# ---------------- missing bounded language ----------------

def test_fail_missing_bounded_language() -> None:
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        _write_evidence(ws)
        report = """
# Test Report

| Q | Question | Status |
|---|---|---|
| Q1 | ... | RECOVERED |
| Q5 | ... | **ENTITY_RESOLUTION_REQUIRED** |
"""
        rc, out, err = _run_validator(ws, report)
        assert rc != 0, f"missing bounded language should fail: stdout={out!r} stderr={err!r}"
        assert "MISSING_BOUNDED_LANGUAGE" in err


# ---------------- per-Q row alignment ----------------

def test_fail_q3_row_missing_conflation_language() -> None:
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        _write_evidence(ws)
        report = """
# Test Report (bounded search performed)

| Q | Question | Status |
|---|---|---|
| Q3 | ... | No candidate was found. |
| Q5 | ... | **ENTITY_RESOLUTION_REQUIRED** |
"""
        rc, out, err = _run_validator(ws, report)
        assert rc != 0, f"Q3 row missing conflation language should fail: stdout={out!r} stderr={err!r}"
        assert "Q3" in err and "conflation" in err


def test_fail_q5_row_missing_marker() -> None:
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        _write_evidence(ws)
        report = """
# Test Report (bounded search performed)

| Q | Question | Status |
|---|---|---|
| Q3 | ... | no canonical candidate recovered under the bounded search; the current evidence supports likely conflation. |
| Q5 | ... | out of scope |
"""
        rc, out, err = _run_validator(ws, report)
        assert rc != 0, f"Q5 row missing ENTITY_RESOLUTION_REQUIRED marker should fail: stdout={out!r} stderr={err!r}"
        assert "Q5" in err and "ENTITY_RESOLUTION_REQUIRED" in err


# ---------------- run-all ----------------

def main() -> int:
    tests = [
        test_pass_clean_report,
        test_fail_does_not_exist,
        test_fail_chinese_bu_cun_zai,
        test_fail_missing_bounded_language,
        test_fail_q3_row_missing_conflation_language,
        test_fail_q5_row_missing_marker,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
    if failed:
        print(f"\n{failed}/{len(tests)} tests FAILED")
        return 1
    print(f"\nAll {len(tests)} tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
