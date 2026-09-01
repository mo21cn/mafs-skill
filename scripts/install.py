#!/usr/bin/env python
"""MAFS Skill 1.0 — portable installer (contract §7 + §8).

stdlib-only (contract §9). Never modifies source repositories. Never
silently overwrites an unrelated skill.

Usage:
    python scripts/install.py --target codex
    python scripts/install.py --target agents
    python scripts/install.py --target-dir <PATH>
    python scripts/install.py --target codex --dry-run

Exit codes (machine-readable):
    0  INSTALLED  (fresh install) or ALREADY_INSTALLED (byte-identical)
    1  INSTALLATION_CONFLICT  (same path differs)
    2  bad arguments
    3  missing required file in source
    4  unable to determine target directory
"""
from __future__ import annotations

import argparse
import filecmp
import hashlib
import os
import shutil
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
SKILL_NAME = "mafs-skill-1-0"
SOURCE_SKILL_DIR = PKG / "skill" / SKILL_NAME
REQUIRED_FILES = (
    "SKILL.md",
    "agents/openai.yaml",
    "references/BASELINES.md",
    "references/CQC_ARTIFACT_CHAIN.md",
    "references/MAFS_RUNTIME_BOUNDARY.md",
    "references/AUTHORITY_RULES.md",
)


def read_version() -> str:
    return (PKG / "VERSION").read_text(encoding="utf-8").strip()


def validate_source() -> list[str]:
    """Return list of missing required files (empty = OK)."""
    missing: list[str] = []
    for rel in REQUIRED_FILES:
        if not (SOURCE_SKILL_DIR / rel).is_file():
            missing.append(rel)
    return missing


def codex_target() -> Path:
    """Honor $CODEX_HOME/skills; else <home>/.codex/skills on Windows
    or <home>/.codex/skills on POSIX. We do not silently fall back to
    .agents/skills when Codex is the actual consumer."""
    env = os.environ.get("CODEX_HOME", "").strip()
    if env:
        return Path(env) / "skills"
    home = Path(os.path.expanduser("~"))
    return home / ".codex" / "skills"


def agents_target() -> Path:
    """Use $HOME/.agents/skills as the contract specifies."""
    home = Path(os.path.expanduser("~"))
    return home / ".agents" / "skills"


def resolve_target(args: argparse.Namespace) -> tuple[str, Path]:
    """Return (kind, target_dir)."""
    if args.target_dir:
        return "explicit", Path(args.target_dir).resolve()
    if args.target == "codex":
        return "codex", codex_target()
    if args.target == "agents":
        return "agents", agents_target()
    raise SystemExit("resolve_target: no target selected (logic error)")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def is_byte_identical(src: Path, dst: Path) -> bool:
    """True if both paths exist and every file under src has a byte-
    identical counterpart under dst with the same relative path."""
    if not dst.is_dir():
        return False
    cmp = filecmp.dircmp(str(src), str(dst))
    if cmp.left_only or cmp.right_only or cmp.diff_files:
        return False
    for sub in cmp.subdirs.values():
        if sub.left_only or sub.right_only or sub.diff_files:
            return False
    return True


def report_failure(status: str, **fields) -> int:
    record = {"status": status, "component": "installer"}
    record.update(fields)
    print("INSTALL_RESULT_BEGIN")
    for k, v in record.items():
        print(f"{k}: {v}")
    print("INSTALL_RESULT_END")
    return 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--target", choices=("codex", "agents"),
                    help="named install target")
    ap.add_argument("--target-dir", help="explicit target directory")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would happen; do not write")
    args = ap.parse_args(argv)

    if not args.target and not args.target_dir:
        ap.error("one of --target or --target-dir is required")

    version = read_version()
    missing = validate_source()
    if missing:
        for m in missing:
            print(f"  MISSING_REQUIRED_FILE: {m}", file=sys.stderr)
        return 3

    try:
        kind, target_root = resolve_target(args)
    except Exception as exc:
        return report_failure(
            "TARGET_UNRESOLVED", reason=str(exc), next_action="check --target or --target-dir"
        )

    target_dir = target_root / SKILL_NAME

    if is_byte_identical(SOURCE_SKILL_DIR, target_dir):
        print(f"ALREADY_INSTALLED: {target_dir}")
        return 0

    if target_dir.exists():
        # Same path exists but differs — refuse to clobber unrelated skill
        return report_failure(
            "INSTALLATION_CONFLICT",
            resolved_path=str(target_dir),
            reason="target_dir exists and is not byte-identical to source",
            next_action="remove target_dir or pick a different --target-dir",
        )

    if args.dry_run:
        print(f"DRY_RUN: would install {SOURCE_SKILL_DIR} -> {target_dir}")
        return 0

    target_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE_SKILL_DIR, target_dir)

    # Verify the install: every required file must exist in target
    for rel in REQUIRED_FILES:
        if not (target_dir / rel).is_file():
            return report_failure(
                "INSTALL_VERIFY_FAILED",
                missing_file=rel,
                resolved_path=str(target_dir),
            )

    print(f"INSTALLED: {target_dir}")
    print(f"version: {version}")
    print(f"required_files: {len(REQUIRED_FILES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
