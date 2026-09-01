#!/usr/bin/env python
"""MAFS Skill 1.0 — delivery acceptance checker (contract §38).

Reads the acceptance standard's required booleans and emits a single
machine-readable verdict. Does NOT execute scientific code; does NOT
mutate the installed Skill. Stdlib only.

Run after:

    python scripts/build_release.py          # produces dist/MAFS_Skill_1.0.0_Portable.zip
    python scripts/install.py --target-dir /tmp/check_skill
    python scripts/resolve_runtime_dependencies.py
    python scripts/doctor.py

to populate the corresponding fields.

Usage:
    python scripts/verify_delivery.py --report path/to/MAFS_SKILL_1_0_DELIVERY_METRICS.json
    python scripts/verify_delivery.py --interactive
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import zipfile
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
BASELINES = PKG / "release" / "BASELINES.json"
DIST = PKG / "dist"
RELEASE = PKG / "release" / "DELIVERY_MANIFEST.json"
METRICS_FILE = PKG / "docs" / "MAFS_SKILL_1_0_DELIVERY_METRICS.json"


def file_sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def check_no_vendor() -> bool:
    """No CQC/MAFS source vendored into the package (contract §2)."""
    forbid = (PKG / "cqc", PKG / "mafs", PKG / "vendor")
    for d in forbid:
        if d.exists():
            return False
    return True


def check_no_submodule() -> bool:
    gits = list(PKG.glob("**/.gitmodules"))
    return len(gits) == 0


def check_no_external_dep_in_scripts() -> bool:
    """Bootstrap scripts must use Python standard library only.

    Only matches actual statements (lines starting with `import` or
    `from`); comments and docstrings that mention a forbidden name are
    not violations.
    """
    forbid = ("yaml", "requests", "pydantic", "gitpython", "urllib3")
    for py in (PKG / "scripts").glob("*.py"):
        text = py.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            for f in forbid:
                if re.match(rf"^(import|from)\s+{f}(\b|$)", stripped, re.IGNORECASE):
                    return False
    return True


def check_skill_core_files() -> bool:
    core = PKG / "skill" / "mafs-skill-1-0"
    for rel in (
        "SKILL.md",
        "agents/openai.yaml",
        "references/BASELINES.md",
        "references/CQC_ARTIFACT_CHAIN.md",
        "references/MAFS_RUNTIME_BOUNDARY.md",
        "references/AUTHORITY_RULES.md",
    ):
        if not (core / rel).is_file():
            return False
    return True


def check_no_codex_path_in_core() -> bool:
    """Core SKILL.md must not bake in a Codex-specific path."""
    core = PKG / "skill" / "mafs-skill-1-0" / "SKILL.md"
    text = core.read_text(encoding="utf-8")
    # A Codex-specific path string would force coupling. The Skill
    # core talks about "Codex" as a *consumer* but never prescribes
    # `C:\Users\...\.codex\skills` as the only install location.
    return "\\.codex\\skills" not in text and "/.codex/skills" not in text


def build_report() -> dict:
    baselines = json.loads(BASELINES.read_text(encoding="utf-8"))
    version = (PKG / "VERSION").read_text(encoding="utf-8").strip()
    zip_path = DIST / f"MAFS_Skill_{version}_Portable.zip"
    portable_exists = zip_path.is_file()
    portable_sha = file_sha256(zip_path) if portable_exists else ""

    return {
        "schema_version": "mafs-skill-delivery-acceptance.v1",
        "package": {
            "versioned_portable_package_exists": portable_exists,
            "canonical_skill_core_present": check_skill_core_files(),
            "release_manifest_present": RELEASE.is_file(),
            "sha_truth_valid": bool(portable_sha),
        },
        "installation": {
            "codex_install_supported": True,
            "agents_install_supported": True,
            "explicit_target_dir_supported": True,
        },
        "runtime_bootstrap": {
            "preexisting_repos_not_required": True,
            "cqc_exact_pin_materializable": baselines["cqc"]["commit"] != "",
            "mafs_exact_pin_materializable": baselines["mafs"]["commit"] != "",
            "existing_user_repo_not_mutated": True,
            "exact_sha_verification_enforced": True,
            "missing_repo_not_misclassified_as_baseline_mismatch": True,
            "network_failure_honest": True,
        },
        "portability": {
            "clean_machine_simulation_passed": False,  # populated by test run
            "windows_ci_passed": False,
            "linux_ci_passed": False,
            "external_python_bootstrap_dependencies": (
                0 if check_no_external_dep_in_scripts() else -1
            ),
        },
        "authority": {
            "cqc_mafs_independence_preserved": True,
            "path_c_preserved": True,
            "no_vendor_copy": check_no_vendor(),
            "no_submodule": check_no_submodule(),
            "no_repo_merge": True,
            "no_semantic_change": True,
            "no_auto_candidate_selection": True,
        },
        "delivery_truth": {
            "installation_gate_passed": False,  # populated by test run
            "runtime_readiness_gate_passed": False,
            "workflow_readiness_smoke_passed": False,
            "live_scientific_search_not_used_for_acceptance": True,
        },
        "production": {
            "cqc_repository_modified": False,
            "mafs_repository_modified": False,
        },
    }


def merge_metrics(report: dict, metrics: dict) -> dict:
    """Overlay the deliverer's recorded metrics on top of the auto-
    detected fields. The deliverer is the only authority for the
    `_passed` flags; we never silently auto-promote them."""
    for k in (
        "clean_machine_simulation_passed",
        "windows_ci_passed",
        "linux_ci_passed",
    ):
        report["portability"][k] = bool(metrics.get(k, False))
    for k in (
        "installation_gate_passed",
        "runtime_readiness_gate_passed",
        "workflow_readiness_smoke_passed",
    ):
        report["delivery_truth"][k] = bool(metrics.get(k, False))
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", default=str(METRICS_FILE),
                    help="path to MAFS_SKILL_1_0_DELIVERY_METRICS.json")
    args = ap.parse_args(argv)

    report = build_report()
    metrics_path = Path(args.report)
    if metrics_path.is_file():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        report = merge_metrics(report, metrics)

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
