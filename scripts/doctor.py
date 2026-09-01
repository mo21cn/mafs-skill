#!/usr/bin/env python
"""MAFS Skill 1.0 — runtime doctor (contract §16).

Reports the runtime state of the Skill without performing any
scientific execution. The doctor NEVER alters state; it only reads.

Overall states (contract §16):

    RUNTIME_READY
    RUNTIME_MATERIALIZATION_REQUIRED
    RUNTIME_BLOCKED

No scientific execution.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
BASELINES = PKG / "release" / "BASELINES.json"


def runtime_home() -> Path:
    return Path(os.environ.get(
        "MAFS_RUNTIME_HOME",
        str(Path(os.path.expanduser("~")) / ".mafs" / "skill-1.0"),
    ))


def repos_dir() -> Path:
    return runtime_home() / "repos"


def __getattr__(name):
    if name == "RUNTIME_HOME":
        return runtime_home()
    if name == "REPOS_DIR":
        return repos_dir()
    raise AttributeError(name)

CQC_NAME = "mafs-cqc"
MAFS_NAME = "mafs-v3-p0"


def find_installed_skill() -> str | None:
    """Look for an installed Skill under common targets. Stdlib only."""
    candidates: list[Path] = []
    env_codex = os.environ.get("CODEX_HOME", "").strip()
    if env_codex:
        candidates.append(Path(env_codex) / "skills" / "mafs-skill-1-0")
    home = Path(os.path.expanduser("~"))
    candidates.append(home / ".codex" / "skills" / "mafs-skill-1-0")
    candidates.append(home / ".agents" / "skills" / "mafs-skill-1-0")
    for c in candidates:
        if c.is_dir():
            return str(c)
    return None


def git_version() -> str:
    if shutil.which("git") is None:
        return "MISSING"
    try:
        r = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or "UNKNOWN"
    except Exception as exc:
        return f"ERROR: {exc}"


def git_head_sha(repo: Path) -> str | None:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo), capture_output=True, text=True, timeout=10,
        )
        if r.returncode != 0:
            return None
        return r.stdout.strip()
    except Exception:
        return None


def report_dep(name: str, info: dict) -> dict:
    target = repos_dir() / name
    record = {
        "name": name,
        "required_commit": info["commit"],
        "required_repository": info["repo"],
        "resolved_path": "",
        "git_head": "",
        "status": "RUNTIME_MATERIALIZATION_REQUIRED",
    }
    # Check user override first
    override = os.environ.get(
        "MAFS_CQC_REPO" if name == "mafs-cqc" else "MAFS_ENGINE_REPO", ""
    ).strip()
    if override:
        ovp = Path(override)
        if ovp.is_dir():
            head = git_head_sha(ovp)
            if head:
                record["resolved_path"] = str(ovp)
                record["git_head"] = head
                if head == info["commit"]:
                    record["status"] = "READY (override)"
                else:
                    record["status"] = "RUNTIME_BLOCKED (override commit mismatch)"
                return record
    if target.is_dir():
        record["resolved_path"] = str(target)
        head = git_head_sha(target)
        if head:
            record["git_head"] = head
            if head == info["commit"]:
                record["status"] = "READY"
            else:
                record["status"] = "RUNTIME_BLOCKED (commit mismatch)"
        else:
            record["status"] = "RUNTIME_BLOCKED (HEAD unreadable)"
    return record


def overall_state(cqc: dict, mafs: dict, gv: str) -> str:
    if gv == "MISSING":
        return "RUNTIME_BLOCKED (git missing)"
    if cqc["status"].startswith("READY") and mafs["status"].startswith("READY"):
        return "RUNTIME_READY"
    if (
        cqc["status"].startswith("RUNTIME_MATERIALIZATION_REQUIRED")
        or mafs["status"].startswith("RUNTIME_MATERIALIZATION_REQUIRED")
    ):
        return "RUNTIME_MATERIALIZATION_REQUIRED"
    return "RUNTIME_BLOCKED"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="emit machine JSON")
    args = ap.parse_args(argv)

    skill_path = find_installed_skill()
    try:
        version = (PKG / "VERSION").read_text(encoding="utf-8").strip()
    except Exception:
        version = "UNKNOWN"
    baselines = json.loads(BASELINES.read_text(encoding="utf-8"))

    gv = git_version()
    cqc = report_dep(CQC_NAME, baselines["cqc"])
    mafs = report_dep(MAFS_NAME, baselines["mafs"])
    overall = overall_state(cqc, mafs, gv)

    record = {
        "skill_version": version,
        "installed_skill_path": skill_path or "",
        "runtime_home": str(runtime_home()),
        "git": gv,
        "cqc": cqc,
        "mafs": mafs,
        "overall_state": overall,
    }
    if args.json:
        print(json.dumps(record, indent=2, ensure_ascii=False))
    else:
        print(f"skill_version:        {record['skill_version']}")
        print(f"installed_skill_path: {record['installed_skill_path'] or '(not installed)'}")
        print(f"runtime_home:         {record['runtime_home']}")
        print(f"git:                  {record['git']}")
        print(f"cqc.required_commit:  {cqc['required_commit']}")
        print(f"cqc.resolved_path:    {cqc['resolved_path'] or '(absent)'}")
        print(f"cqc.git_head:         {cqc['git_head'] or '(n/a)'}")
        print(f"cqc.status:           {cqc['status']}")
        print(f"mafs.required_commit: {mafs['required_commit']}")
        print(f"mafs.resolved_path:   {mafs['resolved_path'] or '(absent)'}")
        print(f"mafs.git_head:        {mafs['git_head'] or '(n/a)'}")
        print(f"mafs.status:          {mafs['status']}")
        print(f"overall_state:        {overall}")

    if overall == "RUNTIME_READY":
        return 0
    if overall == "RUNTIME_MATERIALIZATION_REQUIRED":
        return 0  # Not an error: tells the caller to run resolve_runtime_dependencies
    return 1


if __name__ == "__main__":
    sys.exit(main())
