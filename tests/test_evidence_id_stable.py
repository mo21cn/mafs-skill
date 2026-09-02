"""test_evidence_id_stable.py — regression for advisory §2.1.

The MAFS frozen pin's `live_crossref.py:519` returns
`CanonicalEvidence.evidence_id` as an empty string. The skill-layer
compatibility helper `derive_evidence_id` must:

  - Produce a stable value across repeated resolution of the same
    canonical evidence (same DOI + title -> same evidence_id).
  - Be INDEPENDENT of `resolver_invocation_id` (per advisory §2.1
    explicit prohibition of `hash(doi + resolver_invocation_id + title)`).

These tests are stdlib-only; they do NOT require the MAFS pin to be
materialized, because they target the skill-layer helper directly.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

# Find the skill-layer derive_evidence_id module. We import it by
# adding the inner scripts dir to sys.path; if the file isn't found
# (e.g. test running from a different cwd), we use importlib.
HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "skill" / "mafs-skill-1-0" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
try:
    derive_evidence_id = importlib.import_module("derive_evidence_id")
except ModuleNotFoundError as e:  # pragma: no cover
    raise SystemExit(f"derive_evidence_id module not importable: {e}")


def test_same_doi_title_same_id() -> None:
    """Same canonical DOI + title -> same evidence_id (any number of times)."""
    a = derive_evidence_id.derive_evidence_id(doi="10.1038/nn.3741",
                                              title="A spike-timing mechanism for action selection")
    b = derive_evidence_id.derive_evidence_id(doi="10.1038/nn.3741",
                                              title="A spike-timing mechanism for action selection")
    c = derive_evidence_id.derive_evidence_id(doi="10.1038/nn.3741",
                                              title="A spike-timing mechanism for action selection")
    assert a == b == c, f"derive_evidence_id is not stable: {a!r} {b!r} {c!r}"
    assert a.startswith("CE-") and len(a) == len("CE-") + 16, f"unexpected shape: {a!r}"


def test_different_title_different_id() -> None:
    """Different titles -> different evidence_id, even if DOI matches."""
    a = derive_evidence_id.derive_evidence_id(doi="10.1038/nn.3741",
                                              title="A spike-timing mechanism for action selection")
    b = derive_evidence_id.derive_evidence_id(doi="10.1038/nn.3741",
                                              title="Something completely different")
    assert a != b, f"title variation not detected: {a!r} == {b!r}"


def test_doi_url_normalization() -> None:
    """URL-prefixed DOI is normalized to the bare DOI."""
    a = derive_evidence_id.derive_evidence_id(doi="10.1038/nn.3741",
                                              title="A spike-timing mechanism for action selection")
    b = derive_evidence_id.derive_evidence_id(doi="https://doi.org/10.1038/nn.3741",
                                              title="A spike-timing mechanism for action selection")
    c = derive_evidence_id.derive_evidence_id(doi="HTTPS://DX.DOI.ORG/10.1038/NN.3741",
                                              title="A spike-timing mechanism for action selection")
    assert a == b == c, f"DOI URL prefix not normalized: {a!r} {b!r} {c!r}"


def test_title_whitespace_normalization() -> None:
    """Title internal whitespace + case is normalized."""
    a = derive_evidence_id.derive_evidence_id(doi="10.1038/nn.3741",
                                              title="A spike-timing mechanism for action selection")
    b = derive_evidence_id.derive_evidence_id(doi="10.1038/nn.3741",
                                              title="  A   spike-timing   mechanism   for   action   selection  ")
    c = derive_evidence_id.derive_evidence_id(doi="10.1038/nn.3741",
                                              title="A SPIKE-TIMING MECHANISM FOR ACTION SELECTION")
    assert a == b == c, f"title whitespace/case not normalized: {a!r} {b!r} {c!r}"


def test_resolver_invocation_id_independence() -> None:
    """The helper MUST NOT take resolver_invocation_id at all.

    Per MAINTENANCE_ADVISORY_v0.2 §2.1 explicit prohibition. We assert
    the function signature has no `resolver_invocation_id` parameter,
    which is the strongest possible "independence" guarantee.
    """
    import inspect
    sig = inspect.signature(derive_evidence_id.derive_evidence_id)
    assert "resolver_invocation_id" not in sig.parameters, (
        f"derive_evidence_id signature must not take resolver_invocation_id, "
        f"but signature is {sig!r}"
    )


def test_empty_inputs_rejected() -> None:
    """Both empty -> ValueError (no minted identity for nothing)."""
    try:
        derive_evidence_id.derive_evidence_id(doi="", title="")
    except ValueError:
        return
    raise AssertionError("derive_evidence_id accepted empty doi and title")


def main() -> int:
    tests = [
        test_same_doi_title_same_id,
        test_different_title_different_id,
        test_doi_url_normalization,
        test_title_whitespace_normalization,
        test_resolver_invocation_id_independence,
        test_empty_inputs_rejected,
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
