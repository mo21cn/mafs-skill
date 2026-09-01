#!/usr/bin/env python
"""MAFS Skill 1.0 — deterministic portable release builder (RA1 §15).

The same committed product bytes must generate the same ZIP SHA-256
on Windows, Linux, and across repeated local builds.

Normalizations applied (RA1 §15):
    file ordering                sorted
    POSIX archive paths          forward slashes only
    ZIP timestamps               fixed (1980-01-01 00:00:00)
    ZIP creator system           fixed (0 = MS-DOS / FAT)
    external_attr / file perms   fixed
    compression                  ZIP_DEFLATED + fixed compresslevel
    filename encoding            UTF-8 (no host codepage leak)
    directory entries            not emitted (member-only)

Minimal portable surface (RA1 §16):
    mafs-skill/
    ├── VERSION
    ├── README.md
    ├── skill/
    ├── scripts/
    │   ├── install.py
    │   ├── resolve_runtime_dependencies.py
    │   └── doctor.py
    └── release/
        ├── BASELINES.json
        ├── DELIVERY_MANIFEST.json
        └── SHA256SUMS.txt

Internal SHA256SUMS.txt covers portable content only; it does NOT
include the final ZIP (RA1 §17 — no self-hash loop).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import time
import zipfile
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
DIST = PKG / "dist"
BASELINES = PKG / "release" / "BASELINES.json"
MANIFEST_OUT = PKG / "release" / "DELIVERY_MANIFEST.json"
SHASUMS_OUT = PKG / "release" / "SHA256SUMS.txt"

# Fixed ZipInfo normalization values (RA1 §15).
FIXED_DOS_TIME = (1980, 1, 1, 0, 0, 0)  # 1980-01-01 00:00:00 (DOS epoch)
FIXED_CREATE_SYSTEM = 0                  # MS-DOS / FAT
FIXED_COMPRESS_LEVEL = 9
FIXED_EXTERNAL_ATTR = 0o644 << 16       # regular file, rw-r--r--

# Minimal portable surface (RA1 §16). Tests, build scripts, and
# delivery docs do NOT go into the portable ZIP.
PORTABLE_INCLUDE = (
    "VERSION",
    "README.md",
    "skill",
    "scripts/install.py",
    "scripts/resolve_runtime_dependencies.py",
    "scripts/doctor.py",
    "release/BASELINES.json",
    "release/DELIVERY_MANIFEST.json",
    "release/SHA256SUMS.txt",
)


def file_sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def canonical_file_list() -> list[tuple[Path, str]]:
    """Return [(abs_path, arcname_in_zip), ...] sorted by arcname.

    Skips paths that do not exist (so the build does not crash on
    missing optional files). The arcname always uses forward slashes
    and is rooted under `mafs-skill/`.
    """
    out: list[tuple[Path, str]] = []
    for rel in PORTABLE_INCLUDE:
        src = PKG / rel
        if not src.exists():
            print(f"  WARN: missing {rel}, skipping", file=sys.stderr)
            continue
        if src.is_dir():
            for p in sorted(src.rglob("*")):
                if p.is_file():
                    arcname = (Path("mafs-skill") / rel / p.relative_to(src)).as_posix()
                    out.append((p, arcname))
        else:
            arcname = (Path("mafs-skill") / rel).as_posix()
            out.append((src, arcname))
    out.sort(key=lambda pair: pair[1])
    return out


def make_zipinfo(arcname: str) -> zipfile.ZipInfo:
    """Build a fully-normalized ZipInfo header for `arcname`.

    All platform-specific / time-specific fields are pinned to fixed
    values so that the resulting ZIP bytes are byte-identical across
    Windows / Linux / repeated local builds.
    """
    info = zipfile.ZipInfo(filename=arcname, date_time=FIXED_DOS_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = FIXED_CREATE_SYSTEM
    info.create_version = 20  # 2.0 (required for ZIP_DEFLATED)
    info.extract_version = 20
    info.external_attr = FIXED_EXTERNAL_ATTR
    info.flag_bits = 0  # no bit-11 (UTF-8); we control the bytes anyway
    info.internal_attr = 0
    return info


def build_zip(version: str) -> tuple[Path, str]:
    DIST.mkdir(parents=True, exist_ok=True)
    zip_path = DIST / f"MAFS_Skill_{version}_Portable.zip"
    if zip_path.exists():
        zip_path.unlink()

    files = canonical_file_list()

    # First write to a BytesIO buffer, then write the buffer's bytes
    # atomically to disk. This guarantees the file we hash is the file
    # the user sees (no half-written artifacts on interrupted builds).
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=FIXED_COMPRESS_LEVEL) as zf:
        for src, arcname in files:
            data = src.read_bytes()
            info = make_zipinfo(arcname)
            zf.writestr(info, data)

    zip_bytes = buf.getvalue()
    zip_path.write_bytes(zip_bytes)
    sha = file_sha256(zip_path)
    sha_path = zip_path.with_suffix(zip_path.suffix + ".sha256")
    sha_path.write_text(f"{sha}  {zip_path.name}\n", encoding="utf-8")
    return zip_path, sha


def write_shasums(zip_path: Path, zip_sha: str) -> None:
    """Hash the portable INTERNAL content only (RA1 §17).

    Does NOT include the final ZIP and does NOT include itself
    (no self-hash loop)."""
    files = canonical_file_list()
    lines: list[str] = []
    for src, arcname in files:
        # Exclude the final ZIP and the SHA256SUMS file itself.
        if arcname.endswith("MAFS_Skill_1.0.0_Portable.zip"):
            continue
        if arcname.endswith("release/SHA256SUMS.txt"):
            continue
        # SHA over the canonical on-disk bytes, reported with the
        # same arcname that appears inside the ZIP.
        lines.append(f"{file_sha256(src)}  {arcname}")
    SHASUMS_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(version: str, zip_path: Path, zip_sha: str) -> None:
    """Manifest describes portable content and frozen pins. It does
    NOT contain the final ZIP hash (RA1 §17)."""
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
        "portable_includes": [
            "mafs-skill/VERSION",
            "mafs-skill/README.md",
            "mafs-skill/skill/",
            "mafs-skill/scripts/install.py",
            "mafs-skill/scripts/resolve_runtime_dependencies.py",
            "mafs-skill/scripts/doctor.py",
            "mafs-skill/release/BASELINES.json",
            "mafs-skill/release/DELIVERY_MANIFEST.json",
            "mafs-skill/release/SHA256SUMS.txt",
        ],
        "python_external_bootstrap_dependencies": [],
        "git_required": True,
        "offline_complete": False,
        "no_self_hash_loop": True,
    }
    MANIFEST_OUT.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    args = ap.parse_args(argv)

    version = (PKG / "VERSION").read_text(encoding="utf-8").strip()
    # Manifest and SHASUMS must be written BEFORE the zip, so that
    # their canonical bytes are included in the zip.
    write_manifest(version, None, None)  # type: ignore[arg-type]
    write_shasums(Path("(pending)"), "")  # placeholder
    zip_path, zip_sha = build_zip(version)
    # Re-write the SHA manifest with the now-real zip bytes captured
    # (the SHASUMS inside the zip still points to internal content
    # only; the final zip hash lives in the external .sha256 file).
    write_shasums(zip_path, zip_sha)
    # Re-build the zip with the finalized SHASUMS contents
    zip_path, zip_sha = build_zip(version)

    print(f"BUILT: {zip_path} (sha256={zip_sha[:16]}...)")
    print(f"MANIFEST: {MANIFEST_OUT}")
    print(f"SHASUMS: {SHASUMS_OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
