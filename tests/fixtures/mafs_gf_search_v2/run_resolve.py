#!/usr/bin/env python
"""MAFS Skill 1.0 — resolve() phase for the GF/EM run.

Resolves the three explicitly-selected identity-recovered CandidatePointers
(Q1 von Reyn 2014, Q2 Namiki 2018, Q4 Scheffer 2020) via the production
CrossrefReferenceResolver, emitting CanonicalEvidence objects. No auto-selection
(Q3 produced no candidate; Q5 is ENTITY_RESOLUTION_REQUIRED and never emits an
entity ID).
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

WS = Path(os.environ.get("MAFS_GF_WORKSPACE", r"I:\有趣的项目\mafs_gf_search_v2"))
MAFS_REPO = Path(r"C:\Users\Administrator\.mafs\skill-1.0\repos\mafs-v3-p0")
sys.path.insert(0, str(MAFS_REPO / "src"))

# question -> expected DOI (identity-matched in discovery)
EXPECTED = {
    "Q1": "10.1038/nn.3741",
    "Q2": "10.7554/eLife.34272",
    "Q4": "10.7554/eLife.57443",
}


def find_cp(disc: dict, q: str) -> dict | None:
    """Return the CandidatePointer in the discovery rungs whose DOI matches."""
    exp = EXPECTED[q].lower()
    for rung in disc.get(q, {}).get("ladder_rungs", []):
        for cp in rung.get("candidate_pointers", []):
            doi = (cp.get("identifier_hints") or {}).get("doi") or ""
            if doi.lower() == exp:
                return cp
    return None


def main() -> int:
    from mafs_p0.live_crossref import CrossrefReferenceResolver
    disc = json.loads((WS / "discovery_candidate_pointers.json").read_text(encoding="utf-8"))
    resolver = CrossrefReferenceResolver()
    evidence_out = {}
    for q in ("Q1", "Q2", "Q4"):
        cp = find_cp(disc, q)
        if cp is None:
            evidence_out[q] = {"status": "NO_CANDIDATE"}
            print(f"[resolve] {q}: no identity-matched candidate pointer")
            continue
        ev, riv, snap = resolver.resolve(
            candidate_pointer=cp,
            retrieval_invocation_id=cp.get("retrieval_invocation_id", ""),
        )
        if ev is None:
            evidence_out[q] = {"status": "RESOLUTION_FAILED",
                               "invocation_status": riv.get("status")}
            print(f"[resolve] {q} {cp['identifier_hints']['doi']}: FAILED "
                  f"status={riv.get('status')}")
            continue
        can = ev["canonical"]
        evidence_out[q] = {
            "status": "RESOLVED",
            "candidate_pointer_id": cp["candidate_pointer_id"],
            "doi": can["doi"],
            "title": can["title"],
            "authors": can["authors"],
            "year": can["year"],
            "venue": can["venue"],
            "source_locator": can["source_locator"],
            "evidence_id": ev["evidence_id"],
            "resolver_invocation_id": ev["provenance"]["resolver_invocation_id"],
        }
        print(f"[resolve] {q} {can['doi']}: RECOVERED canonical -> "
              f"'{can['title']}' ({', '.join(can['authors'][:2])}..., {can['year']})")
    # Q5: no entity IDs ever emitted (fabrication invariant).
    evidence_out["Q5"] = {
        "status": "ENTITY_RESOLUTION_REQUIRED",
        "entity_ids_emitted": False,
        "note": "Production stack has no FlyWire/VFB/hemibrain adapter; "
                "HO-supplied IDs are HISTORICAL_ENTITY_ANCHOR_UNVERIFIED. "
                "No entity IDs fabricated.",
    }
    (WS / "resolved_canonical_evidence.json").write_text(
        json.dumps(evidence_out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n[resolve] wrote {WS / 'resolved_canonical_evidence.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
