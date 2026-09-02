#!/usr/bin/env python
"""MAFS Skill 1.0 — installer (RA1 contract §6, §4).

Installs the self-contained runtime-capable Skill unit into a target
directory. The installed Skill owns its bootstrap companion (resolver
+ doctor + baseline truth + shared runtime predicate).

Required installer states (RA1 §6):
    INSTALLED
    ALREADY_INSTALLED
    INSTALLATION_CONFLICT
    INSTALL_VERIFY_FAILED
    TARGET_UNRESOLVED

`ALREADY_INSTALLED` means the entire install surface is byte-identical
to the source Skill, not just the original six core files.

Required install surface (RA1 §4):
    <root>/mafs-skill-1-0/
        SKILL.md
        VERSION
        agents/openai.yaml
        references/{BASELINES, CQC_ARTIFACT_CHAIN, MAFS_RUNTIME_BOUNDARY,
                   AUTHORITY_RULES}.md
        release/BASELINES.json
        scripts/_runtime_truth.py
        scripts/resolve_runtime_dependencies.py
        scripts/doctor.py
"""
from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
SKILL_NAME = "mafs-skill-1-0"
SOURCE_SKILL_DIR = PKG / "skill" / SKILL_NAME

# Entire install surface (RA1 §4). Order is informational; install.py
# walks the source tree and copies everything.
REQUIRED_PATHS = (
    "SKILL.md",
    "VERSION",
    "agents/openai.yaml",
    "references/BASELINES.md",
    "references/CQC_ARTIFACT_CHAIN.md",
    "references/MAFS_RUNTIME_BOUNDARY.md",
    "references/AUTHORITY_RULES.md",
    "release/BASELINES.json",
    "scripts/_runtime_truth.py",
    "scripts/resolve_runtime_dependencies.py",
    "scripts/doctor.py",
)


def validate_source() -> list[str]:
    missing: list[str] = []
    for rel in REQUIRED_PATHS:
        if not (SOURCE_SKILL_DIR / rel).is_file():
            missing.append(rel)
    return missing


def codex_target() -> Path:
    import os
    env = os.environ.get("CODEX_HOME", "").strip()
    if env:
        return Path(env) / "skills"
    return Path.home() / ".codex" / "skills"


def agents_target() -> Path:
    return Path.home() / ".agents" / "skills"


def dsh_target() -> Path:
    """DSH Desktop global skills directory.

    Per MAINTENANCE_ADVISORY_v0.2 §3.E, DSH is a first-class deployment
    target. Path resolution is **deterministic**, **documented**, and
    **overrideable** (via DSH_HOME).

    Resolution order:
      1. $DSH_HOME/skills  (if DSH_HOME is set and non-empty)
      2. %APPDATA%\\dsh-desktop\\harness\\skills (Windows)
      3. $HOME/Library/Application Support/dsh-desktop/harness/skills (macOS)
      4. $XDG_CONFIG_HOME/dsh-desktop/harness/skills  (Linux; default
         $XDG_CONFIG_HOME = ~/.config)

    This function does NOT depend on whether DSH is actually installed;
    it always returns a deterministic path. If the user picks the
    dsh target on a machine without DSH, the install still proceeds;
    the harness will discover the skill when it is started.
    """
    import os
    env = os.environ.get("DSH_HOME", "").strip()
    if env:
        return Path(env) / "skills"
    if sys.platform == "win32":
        return Path(os.environ["APPDATA"]) / "dsh-desktop" / "harness" / "skills"
    if sys.platform == "darwin":
        return (Path.home() / "Library" / "Application Support"
                / "dsh-desktop" / "harness" / "skills")
    cfg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    base = Path(cfg) if cfg else (Path.home() / ".config")
    return base / "dsh-desktop" / "harness" / "skills"


def check_legacy_skill_shadow() -> None:
    """Per MAINTENANCE_ADVISORY_v0.2 §2.3 / §3.D, detect the OMX-era
    legacy `multi_axis_falsification_search` skill in the active Codex
    discovery surface. Emit a warning; do NOT auto-move or auto-delete.

    A successful detection is non-fatal. The user is responsible for
    running the archive step manually (the advisory gives explicit
    authorization to do so).

    Respects `CODEX_HOME` env var (same as `codex_target`).
    """
    import os
    env = os.environ.get("CODEX_HOME", "").strip()
    codex_root = Path(env) if env else Path.home() / ".codex"
    codex_skills = codex_root / "skills"
    legacy = codex_skills / "multi_axis_falsification_search"
    if not legacy.is_dir():
        return
    archive_target = (codex_root / "skills-archive"
                      / "multi_axis_falsification_search-v0.1")
    print(
        f"LEGACY_SKILL_SHADOWING_DETECTED: {legacy}",
        file=sys.stderr,
    )
    print(
        "  presence in active Codex discovery may cause semantic shadowing "
        "with mafs-skill-1-0",
        file=sys.stderr,
    )
    print(
        f"  recommended: move to {archive_target}",
        file=sys.stderr,
    )
    print(
        "  installer does NOT auto-move; user must run manually "
        "(see MAINTENANCE_ADVISORY_v0.2 §2.3)",
        file=sys.stderr,
    )


def resolve_target(args: argparse.Namespace) -> tuple[str, Path]:
    if args.target_dir:
        return "explicit", Path(args.target_dir).resolve()
    if args.target == "codex":
        return "codex", codex_target()
    if args.target == "agents":
        return "agents", agents_target()
    if args.target in ("dsh", "dsh-desktop"):
        return "dsh", dsh_target()
    raise SystemExit("resolve_target: no target selected (logic error)")


def _gather_all_files(src: Path) -> list[Path]:
    """Return a sorted list of all regular files under `src`."""
    out: list[Path] = []
    for p in sorted(src.rglob("*")):
        if p.is_file():
            out.append(p)
    return out


def is_byte_identical(src: Path, dst: Path) -> bool:
    """True iff every file under src has a byte-identical counterpart
    under dst at the same relative path."""
    if not dst.is_dir():
        return False
    cmp = filecmp.dircmp(str(src), str(dst))
    if cmp.left_only or cmp.right_only or cmp.diff_files:
        return False
    for sub in cmp.subdirs.values():
        if sub.left_only or sub.right_only or sub.diff_files:
            return False
    return True


def emit(status: str, **fields) -> None:
    print("INSTALL_RESULT_BEGIN")
    print(f"status: {status}")
    for k, v in fields.items():
        print(f"{k}: {v}")
    print("INSTALL_RESULT_END")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--target", choices=("codex", "agents", "dsh", "dsh-desktop"))
    ap.add_argument("--target-dir")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if not args.target and not args.target_dir:
        ap.error("one of --target or --target-dir is required")

    missing = validate_source()
    if missing:
        for m in missing:
            print(f"MISSING_REQUIRED_FILE: {m}", file=sys.stderr)
        return 3

    # Legacy Codex skill shadow detection (per advisory §2.3 / §3.D).
    # Always run; non-fatal. Only relevant for codex target but emit
    # for any target so the user sees it.
    check_legacy_skill_shadow()

    try:
        kind, target_root = resolve_target(args)
    except Exception as exc:
        emit("TARGET_UNRESOLVED", reason=str(exc),
             next_action="check --target or --target-dir")
        return 4

    target_dir = target_root / SKILL_NAME

    # 1. Byte-identical -> ALREADY_INSTALLED (RA1 §6: entire surface)
    if is_byte_identical(SOURCE_SKILL_DIR, target_dir):
        print(f"ALREADY_INSTALLED: {target_dir}")
        return 0

    # 2. Target exists but differs -> INSTALLATION_CONFLICT
    if target_dir.exists():
        emit(
            "INSTALLATION_CONFLICT",
            resolved_path=str(target_dir),
            reason="target_dir exists and is not byte-identical to source",
            next_action="remove target_dir or pick a different --target-dir",
        )
        return 1

    # 3. Dry-run
    if args.dry_run:
        print(f"DRY_RUN: would install {SOURCE_SKILL_DIR} -> {target_dir}")
        return 0

    # 4. Install
    target_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE_SKILL_DIR, target_dir)

    # 5. Mechanical verification: every required path must exist
    for rel in REQUIRED_PATHS:
        if not (target_dir / rel).is_file():
            emit(
                "INSTALL_VERIFY_FAILED",
                missing_file=rel,
                resolved_path=str(target_dir),
            )
            shutil.rmtree(target_dir, ignore_errors=True)
            return 5

    print(f"INSTALLED: {target_dir}")
    print(f"installed_paths: {len(REQUIRED_PATHS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
