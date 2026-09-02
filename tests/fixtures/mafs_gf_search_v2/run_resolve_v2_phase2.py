"""P3.7a: run_resolve_v2_phase2.py — uses Phase 2 provenance helpers.

This driver demonstrates the Phase 2 §3.A fix in action: every
patched Q preserves the prior Q's full entry (per `patch_one_q`),
and `evidence_id` is derived from canonical DOI + title via
`derive_evidence_id` (per §2.1).

The v1 driver (run_resolve.py) does NOT use these helpers; it
manually constructs the evidence dict, which is exactly the bug
Phase 2 fixes. By using the v1 driver for the basic flow and
THIS driver for the provenance-closure demo, we show:

  1. v1 driver still works (no regression)
  2. Phase 2 helpers close the provenance gap (no more empty
     evidence_id, no more lost resolver_invocation_id)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

WS = Path(os.environ.get("MAFS_GF_WORKSPACE", r"I:\有趣的项目\mafs_gf_search_v2"))
DSH_SKILL = Path(r"C:\Users\Administrator\AppData\Roaming\dsh-desktop\harness\skills\mafs-skill-1-0")
MAFS_REPO = Path(r"C:\Users\Administrator\.mafs\skill-1.0\repos\mafs-v3-p0")

# Add the hardened Skill's references dir (driver_template.py) and scripts
# dir (derive_evidence_id.py) to sys.path. This is exactly how a real
# operator (or DSH agent) would consume the skill's helper API.
sys.path.insert(0, str(DSH_SKILL / "references"))
sys.path.insert(0, str(DSH_SKILL / "scripts"))
sys.path.insert(0, str(MAFS_REPO / "src"))

import driver_template  # Phase 2 §3.A
import derive_evidence_id  # Phase 2 §2.1

# question -> expected DOI (identity-matched in discovery)
EXPECTED = {
    "Q1": "10.1038/nn.3741",
    "Q2": "10.7554/eLife.34272",
    "Q4": "10.7554/eLife.57443",
}


def find_cp(disc: dict, q: str) -> dict | None:
    """Find identity-matched CandidatePointer for Q in discovery."""
    exp = EXPECTED[q].lower()
    for rung in disc.get(q, {}).get("ladder_rungs", []):
        for cp in rung.get("candidate_pointers", []):
            doi = (cp.get("identifier_hints") or {}).get("doi") or ""
            if doi.lower() == exp:
                return cp
    return None


def main() -> int:
    from mafs_p0.live_crossref import CrossrefReferenceResolver

    # 1. Load the v1 result (which is the existing resolved_canonical_evidence.json
    # written by the v1 driver). The Phase 2 helper is supposed to *patch* it,
    # not reconstruct it. If the v1 result has empty evidence_id, the patch
    # will fill it in via derive_evidence_id.
    evidence_path = WS / "resolved_canonical_evidence.json"
    existing = driver_template.load_existing_evidence(evidence_path)
    print(f"[v2-phase2] loaded existing evidence: {sorted(existing.keys())}")

    # 2. Load discovery (for CandidatePointer lookup)
    disc = json.loads((WS / "discovery_candidate_pointers.json").read_text(encoding="utf-8"))

    # 3. For each selected Q, run resolver and patch using the Phase 2 helper.
    resolver = CrossrefReferenceResolver()
    for q in ("Q1", "Q2", "Q4"):
        cp = find_cp(disc, q)
        if cp is None:
            print(f"[v2-phase2] {q}: no candidate_pointer; preserving prior state")
            continue
        ev, riv, _snap = resolver.resolve(
            candidate_pointer=cp,
            retrieval_invocation_id=cp.get("retrieval_invocation_id", ""),
        )
        if ev is None:
            print(f"[v2-phase2] {q}: resolve FAILED status={riv.get('status')}")
            # record failure in-place
            existing = driver_template.patch_one_q(
                existing, q,
                new_evidence=None,
                resolver_invocation_id=(riv or {}).get("resolver_invocation_id", ""),
                resolver_invocation_status=(riv or {}).get("status", "unknown"),
            )
            continue
        # Per advisory §3.A: only patch the retried Q, preserve all others
        # Per advisory §2.1: evidence_id is derived from canonical DOI+title
        # (NOT from resolver_invocation_id)
        existing = driver_template.patch_one_q(
            existing, q,
            new_evidence=ev,
            resolver_invocation_id=(riv or {}).get("resolver_invocation_id", ""),
            resolver_invocation_status=(riv or {}).get("status", "ok"),
        )
        can = (ev or {}).get("canonical") or {}
        title = can.get("title", "")
        eid = existing[q].get("evidence_id", "")
        rivr = existing[q].get("resolver_invocation_id", "")
        print(f"[v2-phase2] {q}: {can.get('doi','')} -> evidence_id={eid}  "
              f"resolver_invocation_id={rivr}  title={title!r}")

    # 4. Write back the patched evidence
    evidence_path.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"\n[v2-phase2] wrote {evidence_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
