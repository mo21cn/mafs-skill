#!/usr/bin/env python
"""MAFS Skill 1.0 runner for the GF / EM narrative (von Reyn et al. 2014/2020).

Executes the frozen workflow tail: build the CQCMAFSIntegrationBinding via the
CQC adapter, then run MAFS discover() for Q1-Q4 through the production Crossref
provider, short-circuiting Q5 as ENTITY_RESOLUTION_REQUIRED. Produces
CandidatePointers for the STOP cognitive checkpoint.

Read-only with respect to the managed CQC / MAFS repos (import + call only).
"""
from __future__ import annotations
import hashlib
import json
import os
import sys
from pathlib import Path

WS = Path(os.environ.get("MAFS_GF_WORKSPACE", r"I:\有趣的项目\mafs_gf_search_v2"))
MAFS_REPO = Path(r"C:\Users\Administrator\.mafs\skill-1.0\repos\mafs-v3-p0")
CQC_REPO = Path(r"C:\Users\Administrator\.mafs\skill-1.0\repos\mafs-cqc")

sys.path.insert(0, str(MAFS_REPO / "src"))
sys.path.insert(0, str(CQC_REPO / "integration" / "mafs_v3"))
sys.path.insert(0, str(CQC_REPO / "scripts"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_binding():
    from adapter import build_binding as bb, READY
    cqs = WS / "cqs.json"
    srp = WS / "srp.json"
    env = WS / "budget_envelope.json"
    # 1. Copy the validated CQS into the workspace for a self-contained chain.
    src_cqs = CQC_REPO / "examples" / "outputs" / "cqs_A_gf_em.json"
    cqs.write_bytes(src_cqs.read_bytes())
    cqs_sha = sha(cqs)
    cqs_id = json.loads(cqs.read_text(encoding="utf-8"))["artifact_id"]
    # 2. Backfill SRP's source_cqs_* from the actual CQS bytes (verify_source_chain
    #    requires SHA256(CQS file) and CQS.artifact_id).
    srp_data = json.loads(srp.read_text(encoding="utf-8"))
    srp_data["source_cqs_id"] = cqs_id
    srp_data["source_cqs_sha256"] = cqs_sha
    srp.write_text(json.dumps(srp_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    srp_sha = sha(srp)
    # 3. Backfill SRP hash into the envelope (must match the actual SRP file bytes).
    env_data = json.loads(env.read_text(encoding="utf-8"))
    env_data["source_srp_sha256"] = srp_sha
    env.write_text(json.dumps(env_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    env_sha = sha(env)
    print(f"[chain] CQS sha256={cqs_sha[:16]}... SRP sha256={srp_sha[:16]}... ENV sha256={env_sha[:16]}...")
    res = bb(case_id="GF-EM-A", cqs_path=cqs, srp_path=srp, envelope_path=env,
             caller_planning=None)
    if res.code != "OK":
        print(f"[binding] FAIL code={res.code} errors={res.errors}")
        return None
    b = res.binding
    b["status"] = "READY_FOR_MAFS_PREFLIGHT"
    (WS / "integration_binding.json").write_text(
        json.dumps(b, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[binding] status={b['status']} active_routes={len(b['active_routes'])} "
          f"held={len(b['held_conditional_routes'])}")
    return b


def _compile_query(qre: dict) -> str:
    from mafs_p0.query_compiler.pubmed_ebsco import compile_for_demo
    out = compile_for_demo(qre)
    return out.get("rendered_query", "") if isinstance(out, dict) else str(out)


def _intent(**kw) -> dict:
    from mafs_p0.crossref_renderer import SearchIntent, render_intent, rendered_query_to_audit_dict
    it = SearchIntent(author=kw.get("author"), year=kw.get("year"),
                      title=kw.get("title"), concepts=list(kw.get("concepts") or []))
    return it


def _search_orders():
    """Q1-Q4 search orders + intents (mirrors the frozen gf_em question graph)."""
    orders = [
        ("SO-Q1-vonReyn-2014", "Q1", "10.1038/nn.3741", "24908103",
         {"author": "von Reyn", "year": 2014, "title": "spike-timing action selection",
          "concepts": ["Drosophila", "giant fiber"]},
         {"op": "AND", "children": [{"op": "PHRASE", "phrase": "von Reyn"},
                                    {"op": "PHRASE", "phrase": "giant fiber"},
                                    {"op": "PHRASE", "phrase": "Drosophila"}]}),
        ("SO-Q2-Namiki-2018", "Q2", "10.7554/eLife.34272", "29943730",
         {"author": "Namiki", "year": 2018, "title": "descending sensory-motor pathways",
          "concepts": ["Drosophila", "descending neuron", "nomenclature"]},
         {"op": "AND", "children": [{"op": "PHRASE", "phrase": "Namiki"},
                                    {"op": "PHRASE", "phrase": "descending neuron"},
                                    {"op": "OR", "children": [{"op": "PHRASE", "phrase": "nomenclature"},
                                                             {"op": "PHRASE", "phrase": "giant fiber"}]}]}),
        ("SO-Q3-vonReyn-2020", "Q3", None, None,
         {"author": "von Reyn", "year": 2020, "title": "giant fiber",
          "concepts": ["Drosophila"]},
         {"op": "AND", "children": [{"op": "PHRASE", "phrase": "von Reyn"},
                                    {"op": "PHRASE", "phrase": "2020"},
                                    {"op": "PHRASE", "phrase": "Drosophila"},
                                    {"op": "PHRASE", "phrase": "giant fiber"}]}),
        ("SO-Q4-Scheffer-2020", "Q4", "10.7554/eLife.57443", "32880371",
         {"author": "Scheffer", "year": 2020, "title": "connectome adult Drosophila central brain",
          "concepts": ["hemibrain"]},
         {"op": "AND", "children": [{"op": "PHRASE", "phrase": "Scheffer"},
                                    {"op": "OR", "children": [{"op": "PHRASE", "phrase": "hemibrain"},
                                                             {"op": "PHRASE", "phrase": "connectome"}]}]}),
    ]
    return orders


def run_discovery():
    from mafs_p0.crossref_renderer import render_intent, rendered_query_to_audit_dict
    from mafs_p0.live_crossref import CrossrefRetrievalProvider
    provider = CrossrefRetrievalProvider()
    out = {}
    for sid, qlabel, exp_doi, exp_pmid, intent_kw, qre in _search_orders():
        compiled = _compile_query(qre)
        it = _intent(**intent_kw)
        rendered = render_intent(it, compiled_query=compiled, top_k=5)
        rung_results = []
        for rq in rendered:
            try:
                cands, ri, snap = provider.discover(
                    search_order_id=sid, url_params=rq.url_params,
                    rendering_path=rq.rendering_path, top_k=5)
                rung_results.append({
                    "rendering_path": rq.rendering_path,
                    "candidate_count": len(cands),
                    "candidate_pointers": cands,
                    "invocation_status": ri["status"],
                    "http_status": ri["response"]["http_status"],
                    "url": rq.url_params,
                })
            except Exception as e:  # pragma: no cover
                rung_results.append({"rendering_path": rq.rendering_path,
                                     "error": f"{type(e).__name__}: {e}"})
        out[qlabel] = {
            "search_order_id": sid,
            "compiled_query": compiled,
            "expected_doi": exp_doi,
            "expected_pmid": exp_pmid,
            "ladder_rungs": rung_results,
        }
    return out


def main() -> int:
    print("=" * 64)
    print("MAFS Skill 1.0 — GF / EM search run (von Reyn 2014/2020)")
    print("=" * 64)
    binding = build_binding()
    disc = run_discovery()
    # Q5 short-circuit (no dataset adapter)
    disc["Q5"] = {
        "search_order_id": "SO-Q5-entity",
        "compiled_query": None,
        "expected_doi": None,
        "expected_pmid": None,
        "status": "ENTITY_RESOLUTION_REQUIRED",
        "rationale": ("Production MAFS v3.0 scholarly stack lacks FlyWire / VFB / hemibrain "
                      "dataset adapters. The exact GF (DNp01) body IDs in FlyWire v783 and "
                      "hemibrain v1.2.1 cannot be resolved by this stack. HO-supplied seeds "
                      "are HISTORICAL_ENTITY_ANCHOR_UNVERIFIED per entity_anchor_oracle.json."),
        "entity_anchor_references": [
            "E1-FlyWire-v783-right-GF", "E2-FlyWire-v783-left-GF",
            "E3-hemibrain-v1.2.1-right-GF"],
    }
    (WS / "discovery_candidate_pointers.json").write_text(
        json.dumps(disc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n[discovery] wrote {WS / 'discovery_candidate_pointers.json'}")
    # Summarize matched identity per question.
    for ql in ("Q1", "Q2", "Q3", "Q4"):
        d = disc.get(ql, {})
        matched = None
        for rung in d.get("ladder_rungs", []):
            for cp in rung.get("candidate_pointers", []):
                doi = (cp.get("identifier_hints") or {}).get("doi") or ""
                pmid = (cp.get("identifier_hints") or {}).get("pmid") or ""
                if d.get("expected_doi") and doi.lower() == d["expected_doi"].lower():
                    matched = doi; break
                if d.get("expected_pmid") and pmid == d["expected_pmid"]:
                    matched = pmid; break
            if matched:
                break
        print(f"[discovery] {ql} expected={d.get('expected_doi') or d.get('expected_pmid')} "
              f"identity_match={'YES' if matched else 'NO'} top_candidate={matched or 'n/a'}")
    print("\n[STOP] cognitive checkpoint reached. CandidatePointers emitted; "
          "no auto-selection, no auto-resolve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
