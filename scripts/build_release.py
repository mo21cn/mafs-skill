#!/usr/bin/env python
"""MAFS Skill 1.0 — portable release builder (contract §19).

Produces:
    dist/MAFS_Skill_<VERSION>_Portable.zip
    dist/MAFS_Skill_<VERSION>_Portable.zip.sha256

The zip is installable without cloning `mafs-skill`. It contains the
package / install / bootstrap material, but NOT copies of the CQC /
MAFS repositories. This is not vendoring (contract §19 final note).

Stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
DIST = PKG / "dist"
BASELINES = PKG / "release" / "BASELINES.json"
MANIFEST_OUT = PKG / "release" / "DELIVERY_MANIFEST.json"
SHASUMS_OUT = PKG / "release" / "SHA256SUMS.txt"

# What we include in the zip (paths relative to PKG).
# We intentionally exclude `dist/` itself and `.git/`.
ZIP_INCLUDE = [
    "VERSION",
    "README.md",
    "skill",
    "scripts",
    "release/BASELINES.json",
    "tests",
    "docs",
    ".github/workflows/delivery-ci.yml",
]


def file_sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def build_zip(version: str) -> tuple[Path, str]:
    DIST.mkdir(parents=True, exist_ok=True)
    zip_path = DIST / f"MAFS_Skill_{version}_Portable.zip"
    # Use a deterministic compression mode; do not store absolute paths
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel in ZIP_INCLUDE:
            src = PKG / rel
            if not src.exists():
                print(f"  WARN: missing {rel}, skipping", file=sys.stderr)
                continue
            if src.is_dir():
                for p in sorted(src.rglob("*")):
                    if p.is_file():
                        arcname = Path("mafs-skill") / rel / p.relative_to(src)
                        zf.write(p, arcname.as_posix())
            else:
                arcname = Path("mafs-skill") / rel
                zf.write(src, arcname.as_posix())
    sha = file_sha256(zip_path)
    sha_path = zip_path.with_suffix(zip_path.suffix + ".sha256")
    sha_path.write_text(f"{sha}  {zip_path.name}\n", encoding="utf-8")
    return zip_path, sha


def build_manifest(version: str, zip_path: Path, zip_sha: str) -> dict:
    baselines = json.loads(BASELINES.read_text(encoding="utf-8"))
    manifest = {
        "schema_version": "mafs-skill-delivery-manifest.v1",
        "product": "MAFS Skill 1.0",
        "version": version,
        "machine_name": "mafs-skill-1-0",
        "cqc": {
            "repo": baselines["cqc"]["repo"],
            "pin": baselines["cqc"]["commit"],
        },
        "mafs": {
            "repo": baselines["mafs"]["repo"],
            "pin": baselines["mafs"]["commit"],
        },
        "required_files": [
            "VERSION",
            "README.md",
            "skill/mafs-skill-1-0/SKILL.md",
            "skill/mafs-skill-1-0/agents/openai.yaml",
            "skill/mafs-skill-1-0/references/BASELINES.md",
            "skill/mafs-skill-1-0/references/CQC_ARTIFACT_CHAIN.md",
            "skill/mafs-skill-1-0/references/MAFS_RUNTIME_BOUNDARY.md",
            "skill/mafs-skill-1-0/references/AUTHORITY_RULES.md",
            "scripts/install.py",
            "scripts/resolve_runtime_dependencies.py",
            "scripts/doctor.py",
            "scripts/verify_delivery.py",
            "scripts/build_release.py",
        ],
        "bootstrap_scripts": [
            "scripts/install.py",
            "scripts/resolve_runtime_dependencies.py",
            "scripts/doctor.py",
            "scripts/verify_delivery.py",
            "scripts/build_release.py",
        ],
        "python_external_bootstrap_dependencies": [],
        "git_required": True,
        "offline_complete": False,
        "portable_package": {
            "path": str(zip_path.relative_to(PKG)),
            "sha256": zip_sha,
            "size_bytes": zip_path.stat().st_size,
        },
        "no_self_hash_loop": True,
    }
    return manifest


def write_shasums(version: str, zip_path: Path, zip_sha: str) -> None:
    lines = []
    for rel in (
        "VERSION",
        "README.md",
        "release/BASELINES.json",
        "skill/mafs-skill-1-0/SKILL.md",
        "scripts/install.py",
        "scripts/resolve_runtime_dependencies.py",
        "scripts/doctor.py",
        "scripts/verify_delivery.py",
        "scripts/build_release.py",
    ):
        p = PKG / rel
        if p.is_file():
            lines.append(f"{file_sha256(p)}  {rel}")
    # Append the zip itself
    lines.append(f"{zip_sha}  dist/{zip_path.name}")
    SHASUMS_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    args = ap.parse_args(argv)

    version = (PKG / "VERSION").read_text(encoding="utf-8").strip()
    zip_path, zip_sha = build_zip(version)
    manifest = build_manifest(version, zip_path, zip_sha)
    MANIFEST_OUT.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_shasums(version, zip_path, zip_sha)
    print(f"BUILT: {zip_path} (sha256={zip_sha[:16]}...)")
    print(f"MANIFEST: {MANIFEST_OUT}")
    print(f"SHASUMS: {SHASUMS_OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
