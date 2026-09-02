#!/usr/bin/env python
"""MAFS Skill 1.0 — installed runtime doctor (RA1 contract).

Self-contained doctor that lives inside the installed Skill. Uses the
same `executable_runtime_predicate` as the resolver, so the two
cannot disagree on whether a given runtime is executable (RA1 §11).

Resolved-path rule (RA1 §8): the doctor never reports a user
override as `resolved_path`. Only paths under the managed runtime
home may appear as resolved.

Overall states (RA1 §12):
    RUNTIME_READY
    RUNTIME_MATERIALIZATION_REQUIRED
    RUNTIME_BLOCKED
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import _runtime_truth as rt  # noqa: E402

INSTALL_ROOT = _HERE.parent
BASELINES = INSTALL_ROOT / "release" / "BASELINES.json"

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
    # Also check the install root (the same directory as this script)
    candidates.append(INSTALL_ROOT)
    for c in candidates:
        if c.is_dir() and (c / "SKILL.md").is_file():
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


def report_dep(name: str, info: dict) -> dict:
    """Report a managed-runtime dependency. The doctor NEVER looks at
    a user override; only the managed runtime home is consulted."""
    target = rt.managed_repos_dir() / name
    record = {
        "name": name,
        "required_commit": info["commit"],
        "required_repository": info["repo"],
        "resolved_path": "",
        "git_head": "",
        "status": "RUNTIME_MATERIALIZATION_REQUIRED",
    }
    if target.is_dir():
        head = rt.head_sha(target)
        if head:
            record["git_head"] = head
        # Use the same executable-runtime predicate the resolver uses.
        ok, reason = rt.executable_runtime_predicate(target, info["commit"])
        if ok:
            record["resolved_path"] = str(target)
            record["status"] = "READY"
        else:
            record["resolved_path"] = str(target)
            record["status"] = f"RUNTIME_BLOCKED ({reason})"
    return record


def overall_state(cqc: dict, mafs: dict, gv: str) -> str:
    if gv == "MISSING" or gv.startswith("ERROR"):
        return "RUNTIME_BLOCKED (git unavailable)"
    if cqc["status"] == "READY" and mafs["status"] == "READY":
        return "RUNTIME_READY"
    if (
        cqc["status"] == "RUNTIME_MATERIALIZATION_REQUIRED"
        or mafs["status"] == "RUNTIME_MATERIALIZATION_REQUIRED"
    ):
        return "RUNTIME_MATERIALIZATION_REQUIRED"
    return "RUNTIME_BLOCKED"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="emit machine JSON")
    args = ap.parse_args(argv)

    skill_path = find_installed_skill()
    try:
        version = (INSTALL_ROOT / "VERSION").read_text(encoding="utf-8").strip()
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
        "runtime_home": str(rt.runtime_home()),
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
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
