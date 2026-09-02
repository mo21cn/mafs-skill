"""test_provenance_retry.py — regression for advisory §3.A.

The original GF/EM session showed a driver-level bug: when `resolve()`
was retried for a single Q (Q2 with canonical-case DOI), the agent
manually reconstructed the entire `resolved_canonical_evidence.json`,
losing `evidence_id` and `resolver_invocation_id` for the Qs that
were NOT retried (Q1, Q4). Per advisory §3.A:

  - retry can only patch the retried Q
  - resolver_invocation_id MUST be preserved
  - candidate_pointer_id MUST be preserved
  - canonical evidence identity MUST be preserved
  - caller MUST NOT manually reconstruct the whole evidence document

This test simulates a retry and asserts the contract on
`driver_template.patch_one_q`.
"""
from __future__ import annotations

import importlib
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent / "skill" / "mafs-skill-1-0"
REFS = SKILL_ROOT / "references"
if str(REFS) not in sys.path:
    sys.path.insert(0, str(REFS))
try:
    driver_template = importlib.import_module("driver_template")
except ModuleNotFoundError as e:  # pragma: no cover
    raise SystemExit(f"driver_template module not importable: {e}")


def _make_evidence(ws: Path) -> None:
    """Write a synthetic resolved_canonical_evidence.json with Q1/Q2/Q4/Q5."""
    data = {
        "Q1": {
            "status": "RESOLVED",
            "candidate_pointer_id": "CP-002",
            "doi": "10.1038/nn.3741",
            "title": "A spike-timing mechanism for action selection",
            "authors": ["Catherine R von Reyn"],
            "year": 2014,
            "venue": "Nature Neuroscience",
            "source_locator": "https://doi.org/10.1038/nn.3741",
            "evidence_id": "CE-deadbeef00000001",
            "resolver_invocation_id": "RIVR-001",
        },
        "Q2": {
            "status": "RESOLVED",
            "candidate_pointer_id": "CP-030",
            "doi": "10.7554/elife.34272",
            "title": "The functional organization of descending sensory-motor pathways in Drosophila",
            "authors": ["Shigehiro Namiki"],
            "year": 2018,
            "venue": "eLife",
            "source_locator": "https://doi.org/10.7554/elife.34272",
            "evidence_id": "CE-deadbeef00000002",
            "resolver_invocation_id": "RIVR-002",
        },
        "Q4": {
            "status": "RESOLVED",
            "candidate_pointer_id": "CP-089",
            "doi": "10.7554/elife.57443",
            "title": "A connectome and analysis of the adult Drosophila central brain",
            "authors": ["Louis K Scheffer"],
            "year": 2020,
            "venue": "eLife",
            "source_locator": "https://doi.org/10.7554/elife.57443",
            "evidence_id": "CE-deadbeef00000004",
            "resolver_invocation_id": "RIVR-004",
        },
        "Q5": {
            "status": "ENTITY_RESOLUTION_REQUIRED",
            "entity_ids_emitted": False,
        },
    }
    (ws / "resolved_canonical_evidence.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def test_load_existing_preserves_all_qs() -> None:
    """Loading existing evidence should yield the full Q1..Q5 dict."""
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        _make_evidence(ws)
        existing = driver_template.load_existing_evidence(
            ws / "resolved_canonical_evidence.json"
        )
        assert set(existing.keys()) == {"Q1", "Q2", "Q4", "Q5"}, (
            f"existing evidence should have Q1/Q2/Q4/Q5, got {set(existing.keys())}"
        )


def test_patch_only_target_q() -> None:
    """Patching Q2 MUST NOT touch Q1/Q4/Q5 entries."""
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        _make_evidence(ws)
        existing = driver_template.load_existing_evidence(
            ws / "resolved_canonical_evidence.json"
        )
        # Snapshot Q1, Q4, Q5 BEFORE patch
        q1_before = dict(existing["Q1"])
        q4_before = dict(existing["Q4"])
        q5_before = dict(existing["Q5"])
        # Retry Q2 with new invocation (canonical case, fresh ID)
        new_evidence = {
            "canonical": {
                "doi": "10.7554/eLife.34272",
                "title": "The functional organization of descending sensory-motor pathways in Drosophila",
                "authors": ["Shigehiro Namiki"],
                "year": 2018,
                "venue": "eLife",
                "source_locator": "https://doi.org/10.7554/eLife.34272",
            }
        }
        existing = driver_template.patch_one_q(
            existing, "Q2",
            new_evidence=new_evidence,
            resolver_invocation_id="RIVR-002-retry",
            resolver_invocation_status="ok",
        )
        # Q1, Q4, Q5 must be BYTE-IDENTICAL
        assert existing["Q1"] == q1_before, "Q1 was modified by Q2 patch!"
        assert existing["Q4"] == q4_before, "Q4 was modified by Q2 patch!"
        assert existing["Q5"] == q5_before, "Q5 was modified by Q2 patch!"
        # Q2 should now have the new resolver_invocation_id
        assert existing["Q2"]["resolver_invocation_id"] == "RIVR-002-retry", (
            f"Q2 resolver_invocation_id not updated: {existing['Q2']!r}"
        )


def test_patch_preserves_candidate_pointer_id() -> None:
    """Patching must NOT clobber the prior candidate_pointer_id."""
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        _make_evidence(ws)
        existing = driver_template.load_existing_evidence(
            ws / "resolved_canonical_evidence.json"
        )
        # Pretend the new evidence object lacks candidate_pointer_id
        new_evidence = {
            "canonical": {
                "doi": "10.7554/eLife.34272",
                "title": "...",
            }
        }
        before_cp = existing["Q2"].get("candidate_pointer_id")
        existing = driver_template.patch_one_q(
            existing, "Q2",
            new_evidence=new_evidence,
            resolver_invocation_id="RIVR-002-retry",
            resolver_invocation_status="ok",
        )
        after_cp = existing["Q2"].get("candidate_pointer_id")
        assert before_cp == after_cp == "CP-030", (
            f"candidate_pointer_id not preserved: {before_cp!r} -> {after_cp!r}"
        )


def test_patch_evidence_id_derived_from_canonical_not_invocation() -> None:
    """Per advisory §2.1: evidence_id MUST be derived from canonical
    DOI+title, NOT from resolver_invocation_id."""
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        _make_evidence(ws)
        existing = driver_template.load_existing_evidence(
            ws / "resolved_canonical_evidence.json"
        )
        new_evidence = {
            "canonical": {
                "doi": "10.7554/eLife.34272",
                "title": "The functional organization of descending sensory-motor pathways in Drosophila",
            }
        }
        # Patch twice with two different resolver_invocation_ids
        # The evidence_id must be the same.
        existing = driver_template.patch_one_q(
            existing, "Q2",
            new_evidence=new_evidence,
            resolver_invocation_id="RIVR-A",
            resolver_invocation_status="ok",
        )
        eid_a = existing["Q2"]["evidence_id"]
        existing = driver_template.patch_one_q(
            existing, "Q2",
            new_evidence=new_evidence,
            resolver_invocation_id="RIVR-B",
            resolver_invocation_status="ok",
        )
        eid_b = existing["Q2"]["evidence_id"]
        assert eid_a == eid_b and eid_a.startswith("CE-"), (
            f"evidence_id must be stable across resolver_invocation_id changes: "
            f"{eid_a!r} vs {eid_b!r}"
        )


def test_patch_resolver_failed_status() -> None:
    """A failed resolve() must record the failure in-place, not raise."""
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        _make_evidence(ws)
        existing = driver_template.load_existing_evidence(
            ws / "resolved_canonical_evidence.json"
        )
        q1_before = dict(existing["Q1"])
        existing = driver_template.patch_one_q(
            existing, "Q2",
            new_evidence=None,  # resolution failed
            resolver_invocation_id="RIVR-002-fail",
            resolver_invocation_status="not_found",
        )
        assert existing["Q2"]["status"] == "RESOLUTION_FAILED"
        assert existing["Q2"]["invocation_status"] == "not_found"
        # Q1 must still be byte-identical
        assert existing["Q1"] == q1_before, "Q1 was modified by Q2 failed patch!"


def main() -> int:
    tests = [
        test_load_existing_preserves_all_qs,
        test_patch_only_target_q,
        test_patch_preserves_candidate_pointer_id,
        test_patch_evidence_id_derived_from_canonical_not_invocation,
        test_patch_resolver_failed_status,
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
