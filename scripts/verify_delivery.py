#!/usr/bin/env python
"""MAFS Skill 1.0 — fail-closed delivery acceptance gate (RA1 §21).

This script does NOT claim PASS for anything it cannot mechanically
verify. Where evidence is absent, it emits `NOT_EVALUATED`. It returns
non-zero exit when any REQUIRED acceptance field is false or not
evaluated.

Required machine evidence:
  - docs/MAFS_SKILL_1_0_DELIVERY_RA1_METRICS.json
  - dist/MAFS_Skill_1.0.0_Portable.zip (must exist)
  - dist/MAFS_Skill_1.0.0_Portable.zip.sha256 (must match the file)

Plus structural checks it can perform locally.

It does NOT call git, NOT hit the network, NOT verify CQC / MAFS
integrity directly. It only reads the metrics file and the local
package artifacts and emits a verdict.
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


def file_sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def derive_local() -> dict:
    """Derive what we can from the local package alone. Anything we
    cannot verify is reported as NOT_EVALUATED."""
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
        return {
            "_missing": True,
            "error": f"metrics file not present: {METRICS}",
        }
    return json.loads(METRICS.read_text(encoding="utf-8"))


def evaluate(derived: dict, metrics: dict) -> tuple[int, dict]:
    """Return (exit_code, verdict).

    The verdict includes:
      - `derived_*` from the local package
      - `metrics_*` from RA1 metrics file
      - `not_evaluated` list of fields the deliverer did not provide
      - `failing` list of REQUIRED fields that are false
      - `passing` list of REQUIRED fields that are true
    """
    verdict: dict = {
        "schema_version": "mafs-skill-delivery-verify.v1",
        "derived": derived,
        "metrics": {} if metrics.get("_missing") else metrics,
        "not_evaluated": [],
        "failing": [],
        "passing": [],
    }

    # Required local (derivable) fields
    required_derivable = [
        ("portable_zip_built", derived["portable_zip_built"]),
        ("portable_zip_internal_manifest_present",
         derived["portable_zip_internal_manifest_present"]),
        ("portable_zip_internal_shasums_present",
         derived["portable_zip_internal_shasums_present"]),
        ("external_zip_sha256_present", derived["external_zip_sha256_present"]),
        ("external_zip_sha256_matches", derived["external_zip_sha256_matches"]),
    ]
    for name, ok in required_derivable:
        if ok:
            verdict["passing"].append(name)
        else:
            verdict["failing"].append(name)

    # Required metrics fields (from RA1 §22 machine-truth model)
    if metrics.get("_missing"):
        verdict["not_evaluated"].append("metrics_file")
    else:
        # Each REQUIRED field from §22 must be present and either true
        # or a known not-evaluated marker.
        # Polarity note: most fields are "this happened" (true = pass).
        # A handful are "this was avoided" (false = pass): a true value
        # for those means we broke a contract invariant.
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
        ]
        negative_metrics = [
            # The Skill MUST NOT have modified upstream production
            # repos. true => we modified production => contract violation.
            "cqc_production_modified",
            "mafs_production_modified",
            "live_scientific_search_executed",
        ]
        for name in positive_metrics:
            if name not in metrics:
                verdict["not_evaluated"].append(name)
                continue
            v = metrics[name]
            if v is True:
                verdict["passing"].append(name)
            elif v is False:
                verdict["failing"].append(name)
            else:
                if isinstance(v, str) and v.startswith("NOT_EVALUATED"):
                    verdict["not_evaluated"].append(name)
                else:
                    verdict["failing"].append(name)
        for name in negative_metrics:
            if name not in metrics:
                verdict["not_evaluated"].append(name)
                continue
            v = metrics[name]
            if v is False:
                verdict["passing"].append(name)
            elif v is True:
                verdict["failing"].append(name)
            else:
                if isinstance(v, str) and v.startswith("NOT_EVALUATED"):
                    verdict["not_evaluated"].append(name)
                else:
                    verdict["failing"].append(name)

        # codex_discovery_smoke_status must be NOT_EVALUATED_BY_CI or true
        dsm = metrics.get("codex_discovery_smoke_status")
        if dsm == "NOT_EVALUATED_BY_CI":
            verdict["passing"].append("codex_discovery_smoke_status")
        elif dsm is True:
            verdict["passing"].append("codex_discovery_smoke_status")
        else:
            verdict["failing"].append("codex_discovery_smoke_status")

    # Exit code: 0 only if all REQUIRED derivable fields pass AND no
    # REQUIRED metrics field is unevaluated or failing.
    if verdict["failing"] or verdict["not_evaluated"]:
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
        if rc == 0:
            print("VERDICT: PASS")
        else:
            print("VERDICT: FAIL")
    return rc


if __name__ == "__main__":
    sys.exit(main())
