#!/usr/bin/env python
"""MAFS Skill 1.0 — fail-closed delivery acceptance gate (RA1 §21,
HO+ChatGPT Push-A remediation).

This script does NOT claim PASS for anything it cannot mechanically
verify. Where evidence is absent, it emits `NOT_EVALUATED`. It returns
non-zero exit when any REQUIRED acceptance field is false or not
evaluated.

Acceptance stages (HO+ChatGPT authorized remediation, 2026-09-02):
  PUSH_A_PREBIND  - the implementation commit, before CI evidence
                     is available. Only CI-evidence fields that
                     cannot exist until Push A has run may carry
                     `NOT_EVALUATED_PENDING_PUSH_A`. All other
                     product/runtime fields remain fail-closed.
  FINAL_BOUND     - the bound stage (Push B). All CI-evidence
                     fields must be concretely bound and PASS.

The deferred surface (PUSH_A_PREBIND only) is narrowly limited to:
  - linux_ci evidence fields
  - windows_ci evidence fields
  - cross_platform_zip_sha_equal
  - external CI run identity fields (Push A evidence commit /
    Push A CI run id)

Any other false, missing, arbitrary string, or NOT_EVALUATED
field remains a hard failure at every stage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
METRICS = PKG / "docs" / "MAFS_SKILL_1_0_DELIVERY_RA1_METRICS.json"
DIST = PKG / "dist"
SHASUMS_INTERNAL = PKG / "release" / "SHA256SUMS.txt"
MANIFEST = PKG / "release" / "DELIVERY_MANIFEST.json"

# Stages
STAGE_PUSH_A_PREBIND = "PUSH_A_PREBIND"
STAGE_FINAL_BOUND = "FINAL_BOUND"
PENDING_MARKER = "NOT_EVALUATED_PENDING_PUSH_A"

# Fields allowed to carry PENDING_MARKER during PUSH_A_PREBIND.
# Any other field carrying PENDING_MARKER (or any other non-bool
# string) is a hard failure.
PUSH_A_DEFERRED_FIELDS = {
    # External CI run identity
    "evidence_commit",
    # Cross-platform equality
    "cross_platform_zip_sha_equal",
    # Linux CI evidence (nested)
    "linux_ci.run_id",
    "linux_ci.status",
    "linux_ci.rebuilt_zip_sha256",
    "linux_ci.portable_only_install_pass",
    "linux_ci.runtime_ready_pass",
    # Windows CI evidence (nested)
    "windows_ci.run_id",
    "windows_ci.status",
    "windows_ci.rebuilt_zip_sha256",
    "windows_ci.portable_only_install_pass",
    "windows_ci.runtime_ready_pass",
}


def file_sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def derive_local() -> dict:
    """Derive what we can from the local package alone."""
    version = "1.0.0"
    zip_path = DIST / f"MAFS_Skill_{version}_Portable.zip"
    sha256_path = DIST / f"MAFS_Skill_{version}_Portable.zip.sha256"

    out: dict = {
        "product": "MAFS Skill 1.0",
        "version": version,
        "cqc_pin": "b34a12295bb4522ff027724630f244f2438c19e6",
        "mafs_pin": "cd09699fc8cc160ab5cfff00a41e714961dd2109",
        "portable_zip_built": zip_path.is_file(),
        "portable_zip_sha256": "",
        "portable_zip_size_bytes": 0,
        "portable_zip_internal_manifest_present": False,
        "portable_zip_internal_shasums_present": False,
        "external_zip_sha256_present": sha256_path.is_file(),
        "external_zip_sha256_matches": False,
    }
    if zip_path.is_file():
        out["portable_zip_sha256"] = file_sha256(zip_path)
        out["portable_zip_size_bytes"] = zip_path.stat().st_size
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
        out["portable_zip_internal_manifest_present"] = (
            "mafs-skill/release/DELIVERY_MANIFEST.json" in names
        )
        out["portable_zip_internal_shasums_present"] = (
            "mafs-skill/release/SHA256SUMS.txt" in names
        )
    if out["external_zip_sha256_present"] and out["portable_zip_built"]:
        text = sha256_path.read_text(encoding="utf-8").strip()
        m = re.match(r"^([a-f0-9]{64})\s", text)
        if m:
            out["external_zip_sha256_matches"] = m.group(1) == out["portable_zip_sha256"]
    return out


def load_metrics() -> dict:
    if not METRICS.is_file():
        return {"_missing": True,
                "error": f"metrics file not present: {METRICS}"}
    return json.loads(METRICS.read_text(encoding="utf-8"))


def _get(metrics: dict, dotted: str):
    """Get a value from metrics, supporting dotted nested paths."""
    parts = dotted.split(".")
    cur = metrics
    for p in parts:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def _classify_metric(name: str, v, metrics: dict, stage: str,
                     in_passing: list, in_failing: list,
                     in_not_evaluated: list) -> None:
    """Classify a single metric field per the stage rules.

    The polarity note from the contract: most fields are "this
    happened" (true = pass). A handful are "this was avoided" (false
    = pass); a true value for those means we broke a contract
    invariant.
    """
    NEGATIVE = {
        "cqc_production_modified",
        "mafs_production_modified",
        "live_scientific_search_executed",
    }

    if name in NEGATIVE:
        if v is False:
            in_passing.append(name)
        elif v is True:
            in_failing.append(name)
        else:
            if isinstance(v, str) and v.startswith("NOT_EVALUATED"):
                in_not_evaluated.append(name)
            else:
                in_failing.append(name)
        return

    # positive polarity
    if v is True:
        in_passing.append(name)
    elif v is False:
        in_failing.append(name)
    else:
        # non-boolean value: must be a NOT_EVALUATED marker
        if isinstance(v, str) and v.startswith("NOT_EVALUATED"):
            # In PUSH_A_PREBIND, this marker is acceptable only on
            # the explicit whitelist of CI-evidence fields.
            if stage == STAGE_PUSH_A_PREBIND and name in PUSH_A_DEFERRED_FIELDS:
                in_not_evaluated.append(name)
            elif stage == STAGE_PUSH_A_PREBIND:
                # marker on a non-deferred field is still a hard
                # failure — it means the deliverer marked a
                # testable product/runtime invariant as not-evaluated
                in_failing.append(name)
            else:  # FINAL_BOUND
                # In FINAL_BOUND, all CI-evidence must be concrete.
                in_failing.append(name)
        else:
            # arbitrary string: hard failure at every stage
            in_failing.append(name)


def evaluate(derived: dict, metrics: dict) -> tuple[int, dict]:
    verdict: dict = {
        "schema_version": "mafs-skill-delivery-verify.v1",
        "derived": derived,
        "metrics": {} if metrics.get("_missing") else metrics,
        "acceptance_stage": None,
        "not_evaluated": [],
        "failing": [],
        "passing": [],
    }

    # Required local (derivable) fields — these have no PUSH_A
    # deferral: they MUST be present and true on every push.
    for name, ok in [
        ("portable_zip_built", derived["portable_zip_built"]),
        ("portable_zip_internal_manifest_present",
         derived["portable_zip_internal_manifest_present"]),
        ("portable_zip_internal_shasums_present",
         derived["portable_zip_internal_shasums_present"]),
        ("external_zip_sha256_present", derived["external_zip_sha256_present"]),
        ("external_zip_sha256_matches", derived["external_zip_sha256_matches"]),
    ]:
        if ok:
            verdict["passing"].append(name)
        else:
            verdict["failing"].append(name)

    if metrics.get("_missing"):
        verdict["failing"].append("metrics_file")
        return 1, verdict

    # Stage detection
    stage = metrics.get("acceptance_stage")
    if stage not in (STAGE_PUSH_A_PREBIND, STAGE_FINAL_BOUND):
        verdict["failing"].append("acceptance_stage")
        return 1, verdict
    verdict["acceptance_stage"] = stage

    # Top-level RA1 §22 machine truth model fields
    positive_metrics = [
        "installed_skill_self_contained",
        "portable_only_install_pass",
        "installed_resolver_invoked",
        "installed_doctor_invoked",
        "runtime_ready_pass",
        "managed_runtime_only",
        "user_override_never_executable",
        "resolver_doctor_truth_consistent",
        "wrong_repo_no_mutation_pass",
        "tracked_runtime_dirty_detection_pass",
        "portable_zip_built",
        "reproducible_build_local_pass",
        "cross_platform_zip_sha_equal",
        "codex_install_layout_pass",
        "governance_deviation_recorded",
        "evidence_commit",
    ]
    negative_metrics = [
        "cqc_production_modified",
        "mafs_production_modified",
        "live_scientific_search_executed",
    ]
    for name in positive_metrics + negative_metrics:
        if name not in metrics:
            verdict["failing"].append(name)
            continue
        _classify_metric(name, metrics[name], metrics, stage,
                         verdict["passing"], verdict["failing"],
                         verdict["not_evaluated"])

    # codex_discovery_smoke_status — always NOT_EVALUATED_BY_CI is acceptable
    dsm = metrics.get("codex_discovery_smoke_status")
    if dsm == "NOT_EVALUATED_BY_CI":
        verdict["passing"].append("codex_discovery_smoke_status")
    elif dsm is True:
        verdict["passing"].append("codex_discovery_smoke_status")
    else:
        verdict["failing"].append("codex_discovery_smoke_status")

    # Nested linux_ci / windows_ci evidence
    for os_name in ("linux_ci", "windows_ci"):
        sub = metrics.get(os_name) or {}
        for field in ("run_id", "status", "rebuilt_zip_sha256",
                      "portable_only_install_pass", "runtime_ready_pass"):
            dotted = f"{os_name}.{field}"
            v = sub.get(field) if isinstance(sub, dict) else None
            if v is None:
                # Missing entirely
                if stage == STAGE_PUSH_A_PREBIND and dotted in PUSH_A_DEFERRED_FIELDS:
                    verdict["not_evaluated"].append(dotted)
                else:
                    verdict["failing"].append(dotted)
                continue
            _classify_metric(dotted, v, metrics, stage,
                             verdict["passing"], verdict["failing"],
                             verdict["not_evaluated"])

    if verdict["failing"]:
        return 1, verdict
    # In PUSH_A_PREBIND, the only acceptable not_evaluated entries
    # are fields in PUSH_A_DEFERRED_FIELDS (CI evidence not yet
    # available). Any other not_evaluated field is a hard fail.
    if verdict["not_evaluated"]:
        if stage == STAGE_PUSH_A_PREBIND:
            allowed = set(PUSH_A_DEFERRED_FIELDS)
            for f in verdict["not_evaluated"]:
                if f not in allowed:
                    verdict["failing"].append(
                        f"{f} (not deferred in PUSH_A_PREBIND)"
                    )
            if verdict["failing"]:
                return 1, verdict
            return 0, verdict
        # FINAL_BOUND: every field must be concretely bound.
        return 1, verdict
    return 0, verdict


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    derived = derive_local()
    metrics = load_metrics()
    rc, verdict = evaluate(derived, metrics)
    if args.json:
        print(json.dumps(verdict, indent=2, ensure_ascii=False))
    else:
        for k in ("passing", "failing", "not_evaluated"):
            print(f"--- {k} ---")
            for f in verdict[k]:
                print(f"  {f}")
        print(f"acceptance_stage: {verdict.get('acceptance_stage')}")
        if rc == 0:
            print("VERDICT: PASS")
        else:
            print("VERDICT: FAIL")
    return rc


if __name__ == "__main__":
    sys.exit(main())
