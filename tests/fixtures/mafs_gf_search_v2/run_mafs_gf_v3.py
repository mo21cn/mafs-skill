"""run_mafs_gf_v3.py — planning-artifact-consuming driver.

Per `MAFS-SKILL-1.0-PHASE-3-FINAL-v0.1` §2 / §3 / §4:

  - Externalizes the model-authored Axis / SearchOrder into
    mafs_planning.json (loaded from PLANNING_PATH env var, default
    `WS/mafs_planning.json`).
  - The driver does NOT hardcode the effective scientific plan.
  - The driver is a small deterministic parser/adapter: it reads
    the artifact, executes what it specifies, and never
    reinterprets or improves scientific meaning.
  - Q5's ENTITY_RESOLUTION_REQUIRED boundary is recognized via
    `search_intent == null && query_re == null` in the artifact.
  - The artifact's SHA-256 is recorded in
    `dsh_integration_trace_v3.json` per advisory §16.

This file is the planning-consuming counterpart of the v1/v2
`run_mafs_gf.py` (which kept the plan inline in
`_search_orders()`).
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
PLANNING_PATH = Path(os.environ.get("MAFS_PLANNING_PATH", str(WS / "mafs_planning.json")))

sys.path.insert(0, str(MAFS_REPO / "src"))
sys.path.insert(0, str(CQC_REPO / "integration" / "mafs_v3"))
sys.path.insert(0, str(CQC_REPO / "scripts"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_planning(path: Path) -> dict:
    """Load and validate the planning artifact.

    The driver is a small deterministic parser/adapter; it may NOT
    reinterpret or improve scientific meaning. Any unexpected
    shape raises (fail-closed).
    """
    if not path.is_file():
        raise SystemExit(f"PLANNING_ARTIFACT_MISSING: {path}")
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    if data.get("schema_version") != "mafs-skill-planning.v1":
        raise SystemExit(f"PLANNING_ARTIFACT_SCHEMA_UNSUPPORTED: {data.get('schema_version')!r}")
    if data.get("authored_by") != "model":
        raise SystemExit(f"PLANNING_ARTIFACT_AUTHOR_NOT_MODEL: {data.get('authored_by')!r}")
    if not isinstance(data.get("axes"), list) or not data["axes"]:
        raise SystemExit("PLANNING_ARTIFACT_AXES_MISSING")
    if not isinstance(data.get("search_orders"), list) or not data["search_orders"]:
        raise SystemExit("PLANNING_ARTIFACT_SEARCH_ORDERS_MISSING")
    return data


def build_binding():
    from adapter import build_binding as bb, READY
    cqs = WS / "cqs.json"
    srp = WS / "srp.json"
    env = WS / "budget_envelope.json"
    src_cqs = CQC_REPO / "examples" / "outputs" / "cqs_A_gf_em.json"
    cqs.write_bytes(src_cqs.read_bytes())
    cqs_sha = sha(cqs)
    cqs_id = json.loads(cqs.read_text(encoding="utf-8"))["artifact_id"]
    srp_data = json.loads(srp.read_text(encoding="utf-8"))
    srp_data["source_cqs_id"] = cqs_id
    srp_data["source_cqs_sha256"] = cqs_sha
    srp.write_text(json.dumps(srp_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    srp_sha = sha(srp)
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
    # Per lineage_glue.md, augment the binding with the planning pointer
    planning_sha = sha(PLANNING_PATH)
    b["mafs_planning_pointer"] = {
        "artifact": str(PLANNING_PATH),
        "artifact_sha256": planning_sha,
        "schema_version": "mafs-skill-planning.v1",
    }
    (WS / "integration_binding.json").write_text(
        json.dumps(b, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[binding] status={b['status']} active_routes={len(b['active_routes'])} "
          f"held={len(b['held_conditional_routes'])} "
          f"mafs_planning_pointer={planning_sha[:16]}...")
    return b


def _compile_query(qre: dict) -> str:
    from mafs_p0.query_compiler.pubmed_ebsco import compile_for_demo
    out = compile_for_demo(qre)
    return out.get("rendered_query", "") if isinstance(out, dict) else str(out)


def _intent(**kw) -> dict:
    from mafs_p0.crossref_renderer import SearchIntent
    return SearchIntent(author=kw.get("author"), year=kw.get("year"),
                        title=kw.get("title"), concepts=list(kw.get("concepts") or []))


def run_discovery(planning: dict):
    """Execute the model-authored planning via MAFS.

    The driver iterates over the artifact's `search_orders` in
    artifact order. For Q1-Q4 it builds ladder rungs via Crossref.
    Q5 (search_intent == null && query_re == null) is treated as
    the entity-resolution boundary and gets a short-circuit
    ENTITY_RESOLUTION_REQUIRED entry (no discovery).
    """
    from mafs_p0.crossref_renderer import render_intent
    from mafs_p0.live_crossref import CrossrefRetrievalProvider

    provider = CrossrefRetrievalProvider()
    out = {}
    for so in planning["search_orders"]:
        qlabel = so["question_label"]
        sid = so["mafs_search_order_id"]
        exp_doi = so.get("expected_doi")
        exp_pmid = so.get("expected_pmid")
        intent_kw = so.get("search_intent")
        qre = so.get("query_re")
        # Q5 entity-resolution boundary
        if intent_kw is None and qre is None:
            out[qlabel] = {
                "search_order_id": sid,
                "mafs_axis_id": so.get("mafs_axis_id"),
                "compiled_query": None,
                "expected_doi": None,
                "expected_pmid": None,
                "status": "ENTITY_RESOLUTION_REQUIRED",
                "rationale": ("Q5 boundary preserved per planning artifact: "
                              "MAFS scholarly stack has no FlyWire / VFB / "
                              "hemibrain dataset adapter. The exact body IDs "
                              "are HISTORICAL_ENTITY_ANCHOR_UNVERIFIED."),
                "entity_anchor_references": [
                    "E1-FlyWire-v783-right-GF", "E2-FlyWire-v783-left-GF",
                    "E3-hemibrain-v1.2.1-right-GF"
                ],
            }
            continue
        compiled = _compile_query(qre)
        it = _intent(**(intent_kw or {}))
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
            except Exception as e:
                rung_results.append({"rendering_path": rq.rendering_path,
                                     "error": f"{type(e).__name__}: {e}"})
        out[qlabel] = {
            "search_order_id": sid,
            "mafs_axis_id": so.get("mafs_axis_id"),
            "compiled_query": compiled,
            "expected_doi": exp_doi,
            "expected_pmid": exp_pmid,
            "ladder_rungs": rung_results,
        }
    return out


def main() -> int:
    print("=" * 64)
    print("MAFS Skill 1.0 — GF / EM search run (v3, planning-consumed)")
    print("=" * 64)
    print(f"  planning : {PLANNING_PATH}")
    print(f"  planning SHA-256: {sha(PLANNING_PATH)}")
    planning = load_planning(PLANNING_PATH)
    print(f"  axes    : {len(planning['axes'])}")
    print(f"  orders  : {len(planning['search_orders'])}")
    binding = build_binding()
    if binding is None:
        return 1
    disc = run_discovery(planning)
    (WS / "discovery_candidate_pointers.json").write_text(
        json.dumps(disc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n[discovery] wrote {WS / 'discovery_candidate_pointers.json'}")
    for ql in ("Q1", "Q2", "Q3", "Q4", "Q5"):
        d = disc.get(ql, {})
        if d.get("status") == "ENTITY_RESOLUTION_REQUIRED":
            print(f"[discovery] {ql}: status=ENTITY_RESOLUTION_REQUIRED (boundary preserved)")
            continue
        matched = None
        for rung in d.get("ladder_rungs", []):
            for cp in rung.get("candidate_pointers", []):
                doi = ((cp.get("identifier_hints") or {}).get("doi") or "").lower()
                pmid = (cp.get("identifier_hints") or {}).get("pmid") or ""
                exp_d = (d.get("expected_doi") or "").lower()
                exp_p = d.get("expected_pmid") or ""
                if exp_d and doi == exp_d:
                    matched = doi; break
                if exp_p and pmid == exp_p:
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
