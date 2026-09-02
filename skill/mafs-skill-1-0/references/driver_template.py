"""driver_template.py — canonical driver pattern for MAFS Skill 1.0 tasks.

This is a TEMPLATE, not a runtime script. Copy it into your workspace and
adapt the question graph / search orders to your narrative. Per
MAINTENANCE_ADVISORY_v0.2 §8 (STOP driver pattern) and §3.A (resolver
provenance closure), the canonical driver MUST:

  1. Build the CQC chain (CQS -> SRP -> BudgetEnvelope -> IntegrationBinding)
  2. Run MAFS discover() and emit discovery_candidate_pointers.json
  3. **In the same process**, print a bounded STOP checkpoint summary
     (avoids the read-after-write subprocess that triggers an avoidable
     DSH approval)
  4. After explicit human selection, run resolve() and emit
     resolved_canonical_evidence.json — but for the SELECTED Qs only
  5. **Retry semantics**: if a single Q's resolve() needs a re-run, use
     `retry_resolve_one()` from this template to patch only that Q's
     entry, never overwrite the whole evidence file. This is the
     closure required by advisory §3.A.

The driver MUST NOT have auto-select or auto-resolve authority. The
STOP-then-explicit-selection flow is the epistemic checkpoint; the
template preserves it.

This file is intentionally stdlib-only (Python 3.10+).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

# --- compatibility-layer backfill (per advisory §2.1) ----------------------
# The MAFS frozen pin's `live_crossref._build_canonical_evidence` returns
# `evidence_id=""`. We do NOT modify the pin. Instead, when wrapping the
# resolver output at the driver layer, we backfill `evidence_id` from the
# canonical DOI + title — a value that is stable across repeated
# resolutions of the same evidence and INDEPENDENT of
# resolver_invocation_id.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
try:
    from derive_evidence_id import (  # type: ignore
        derive_evidence_id,
        extract_canonical_fields,
    )
    _HAVE_DERIVE = True
except Exception:  # pragma: no cover
    _HAVE_DERIVE = False
    derive_evidence_id = None  # type: ignore
    extract_canonical_fields = None  # type: ignore


# --- retry provenance closure (per advisory §3.A) ------------------------

def load_existing_evidence(path: Path) -> dict[str, Any]:
    """Load the existing resolved_canonical_evidence.json if present.

    Returns an empty dict if the file does not exist. Returns the parsed
    dict otherwise. The driver MUST preserve every other Q's entry from
    this dict when retrying a single Q.
    """
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def patch_one_q(
    existing: dict[str, Any],
    q: str,
    *,
    new_evidence: dict[str, Any] | None,
    resolver_invocation_id: str,
    resolver_invocation_status: str,
) -> dict[str, Any]:
    """Patch exactly one Q's evidence entry; preserve all others.

    Per advisory §3.A:
      - retry can only patch the retried Q
      - resolver_invocation_id MUST be preserved (per-call identity)
      - candidate_pointer_id MUST be preserved (from prior resolve)
      - canonical evidence identity MUST be preserved
    The patched Q's evidence_id is derived from canonical DOI + title
    (NOT from resolver_invocation_id) per advisory §2.1.
    """
    if q not in existing:
        existing[q] = {}
    prior = dict(existing[q])
    if new_evidence is None:
        prior["status"] = "RESOLUTION_FAILED"
        prior["invocation_status"] = resolver_invocation_status
        existing[q] = prior
        return existing
    can = (new_evidence or {}).get("canonical") or {}
    doi = str(can.get("doi") or prior.get("doi") or "")
    title = str(can.get("title") or prior.get("title") or "")
    # Build the new entry, preserving pre-existing identity fields.
    entry: dict[str, Any] = {
        "status": "RESOLVED",
        "candidate_pointer_id": prior.get("candidate_pointer_id") or
                                (new_evidence.get("candidate_pointer_id") or ""),
        "doi": doi or prior.get("doi", ""),
        "title": title or prior.get("title", ""),
        "authors": can.get("authors") or prior.get("authors") or [],
        "year": can.get("year") or prior.get("year"),
        "venue": can.get("venue") or prior.get("venue"),
        "source_locator": can.get("source_locator") or prior.get("source_locator", ""),
        "resolver_invocation_id": resolver_invocation_id,
        # evidence_id is derived from canonical content (NOT invocation id)
        "evidence_id": (
            derive_evidence_id(doi=doi, title=title)
            if (_HAVE_DERIVE and (doi or title))
            else prior.get("evidence_id", "")
        ),
    }
    existing[q] = entry
    return existing


def retry_resolve_one(
    *,
    q: str,
    candidate_pointer: dict[str, Any],
    workspace: Path,
    mafs_repo_pythonpath: str,
) -> int:
    """Resolve a single Q and patch only that Q's evidence entry.

    This is the closure for advisory §3.A "retry preserves existing Q1/Q4
    provenance / retry only patches target Q / caller must not manually
    reconstruct the whole evidence document".

    Returns the resolver invocation's status (string). Does NOT raise on
    resolver failure; it records the failure in-place and returns.
    """
    if not _HAVE_DERIVE:
        print(f"[retry] derive_evidence_id not importable; "
              f"evidence_id will be left empty for {q}", file=sys.stderr)

    sys.path.insert(0, mafs_repo_pythonpath)
    try:
        from mafs_p0.live_crossref import CrossrefReferenceResolver
    except Exception as e:  # pragma: no cover
        print(f"[retry] cannot import CrossrefReferenceResolver: {e}",
              file=sys.stderr)
        return "import_failed"

    resolver = CrossrefReferenceResolver()
    ev, riv, _snap = resolver.resolve(
        candidate_pointer=candidate_pointer,
        retrieval_invocation_id=candidate_pointer.get("retrieval_invocation_id", ""),
    )

    evidence_path = workspace / "resolved_canonical_evidence.json"
    existing = load_existing_evidence(evidence_path)
    rivr_id = (riv or {}).get("resolver_invocation_id", "")
    rivr_status = (riv or {}).get("status", "unknown")
    existing = patch_one_q(
        existing, q,
        new_evidence=ev,
        resolver_invocation_id=rivr_id,
        resolver_invocation_status=rivr_status,
    )
    evidence_path.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[retry] {q}: patched evidence entry, "
          f"resolver_invocation_id={rivr_id} status={rivr_status}")
    return rivr_status


# --- STOP driver pattern (per advisory §8) -------------------------------

def emit_stop_checkpoint(
    *,
    discovery_path: Path,
    expected_per_q: dict[str, dict[str, str]],
) -> None:
    """Print a bounded STOP checkpoint summary in the same process that
    wrote the discovery artifact (advisory §8).

    This avoids the read-after-write subprocess pattern that previously
    triggered an avoidable DSH approval at step 31 of the original
    session. The summary is human-readable, prints to stdout, and does
    NOT ask the user to confirm (that's the harness's ask_user_question
    job, not the driver's).
    """
    disc = json.loads(discovery_path.read_text(encoding="utf-8"))
    print()
    print("=" * 64)
    print("STOP CHECKPOINT (no auto-select, no auto-resolve)")
    print("=" * 64)
    for q in sorted(disc.keys()):
        d = disc[q]
        expected = expected_per_q.get(q, {})
        expected_doi = expected.get("doi") or "n/a"
        expected_pmid = expected.get("pmid") or "n/a"
        # Find first matched candidate (if any)
        matched = "n/a"
        if d.get("status") == "ENTITY_RESOLUTION_REQUIRED":
            matched = "ENTITY_RESOLUTION_REQUIRED"
        else:
            for rung in d.get("ladder_rungs") or []:
                for cp in rung.get("candidate_pointers") or []:
                    hints = cp.get("identifier_hints") or {}
                    doi = (hints.get("doi") or "").lower()
                    pmid = (hints.get("pmid") or "")
                    if expected_doi != "n/a" and doi == expected_doi.lower():
                        matched = doi
                        break
                    if expected_pmid != "n/a" and pmid == expected_pmid:
                        matched = pmid
                        break
                if matched != "n/a":
                    break
        print(f"  {q}: status={d.get('status', 'DISCOVERED')} "
              f"expected={expected_doi}/{expected_pmid} match={matched}")
    print()
    print("Awaiting explicit human selection (Q1,Q2,Q4 default) ...")
    print("(Use the harness's ask_user_question to collect selection. "
          "Do NOT auto-select from this driver.)")


# --- main: an opinionated, single-process driver skeleton ----------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="MAFS Skill 1.0 canonical driver (template).",
    )
    ap.add_argument("--workspace", type=Path, required=True,
                    help="Workspace directory for outputs.")
    ap.add_argument("--mafs-repo", type=Path, required=True,
                    help="Path to the materialized mafs-v3-p0 repo root.")
    ap.add_argument("--cqc-repo", type=Path, required=True,
                    help="Path to the materialized mafs-cqc repo root.")
    ap.add_argument("--mode", choices=("discover", "resolve", "retry"),
                    default="discover",
                    help="Driver phase to run. Default: discover.")
    ap.add_argument("--retry-q", default=None,
                    help="For --mode=retry, the Q label to retry (e.g. Q2).")
    ap.add_argument("--retry-cp-source", type=Path, default=None,
                    help="For --mode=retry, path to discovery_candidate_pointers.json "
                         "to pull the candidate pointer for the retried Q.")
    args = ap.parse_args()

    ws: Path = args.workspace.resolve()
    ws.mkdir(parents=True, exist_ok=True)

    if args.mode == "discover":
        # 1. build CQC chain
        # 2. run MAFS discover
        # 3. write discovery_candidate_pointers.json
        # 4. emit STOP checkpoint in the SAME process
        #
        # The body of each step is narrative-specific and is intentionally
        # left to the user / agent to fill in. See the GF/EM
        # ma_archive_gf_search/run_mafs_gf.py for a worked example.
        print("[driver] DISCOVER mode: implement per-narrative; see template docstring.")
        return 0

    if args.mode == "resolve":
        # 1. read discovery_candidate_pointers.json
        # 2. for each explicitly-selected Q (passed via stdin / harness),
        #    call resolver and patch evidence using patch_one_q
        # 3. write resolved_canonical_evidence.json
        # 4. do NOT emit STOP here (resolve is post-STOP)
        print("[driver] RESOLVE mode: implement per-narrative.")
        return 0

    if args.mode == "retry":
        if not args.retry_q or not args.retry_cp_source:
            print("[driver] --mode=retry requires --retry-q and --retry-cp-source",
                  file=sys.stderr)
            return 2
        disc = json.loads(args.retry_cp_source.read_text(encoding="utf-8"))
        q_data = disc.get(args.retry_q) or {}
        cp = None
        for rung in q_data.get("ladder_rungs") or []:
            for cand in rung.get("candidate_pointers") or []:
                cp = cand
                break
            if cp:
                break
        if cp is None:
            print(f"[driver] no candidate_pointer for {args.retry_q}",
                  file=sys.stderr)
            return 3
        status = retry_resolve_one(
            q=args.retry_q,
            candidate_pointer=cp,
            workspace=ws,
            mafs_repo_pythonpath=str((args.mafs_repo / "src").resolve()),
        )
        return 0 if status == "ok" else 4

    return 0


if __name__ == "__main__":
    sys.exit(main())
