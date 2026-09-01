#!/usr/bin/env python
"""MAFS Skill 1.0 — runtime dependency resolver (contract §11-15).

stdlib-only (contract §9). The only allowed external system tool is
`git`. The resolver never interprets scientific intent, never
modifies CQS / SRP / BudgetEnvelope, never auto-selects a
CandidatePointer.

States reported on stdout:

    READY
    BASELINE_MATERIALIZATION_REQUIRED
    BASELINE_MISMATCH
    BASELINE_UNAVAILABLE
    DEPENDENCY_TOOL_MISSING
    RUNTIME_CACHE_CORRUPT

For each of the two pinned dependencies (cqc, mafs), the resolver
writes a fact record:

    status
    component
    required_repository
    required_commit
    resolved_path
    operation
    reason
    next_action

Forbidden against user repositories (§13):

    git checkout <pin>
    git reset --hard
    git clean
    forced pull
    branch switch
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


def state_dir() -> Path:
    return runtime_home() / "state"


def logs_dir() -> Path:
    return runtime_home() / "logs"


# Backward-compatible module-level aliases (lazily resolved)
def __getattr__(name):
    if name == "RUNTIME_HOME":
        return runtime_home()
    if name == "REPOS_DIR":
        return repos_dir()
    if name == "STATE_DIR":
        return state_dir()
    if name == "LOGS_DIR":
        return logs_dir()
    raise AttributeError(name)


CQC_NAME = "mafs-cqc"
MAFS_NAME = "mafs-v3-p0"


def check_git() -> str | None:
    """Return None if git is available; else DEPENDENCY_TOOL_MISSING."""
    if shutil.which("git") is None:
        return "DEPENDENCY_TOOL_MISSING: git binary not on PATH"
    try:
        r = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            return f"DEPENDENCY_TOOL_MISSING: git --version failed: {r.stderr.strip()}"
        return None
    except Exception as exc:
        return f"DEPENDENCY_TOOL_MISSING: git invocation failed: {exc}"


def load_baselines() -> dict:
    return json.loads(BASELINES.read_text(encoding="utf-8"))


def git_head_sha(repo: Path) -> str | None:
    """Return 40-char SHA of repo's HEAD, or None on error."""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo), capture_output=True, text=True, timeout=15,
        )
        if r.returncode != 0:
            return None
        return r.stdout.strip()
    except Exception:
        return None


def git_object_present(repo: Path, sha: str) -> bool:
    """True if the given commit object exists in repo (object store)."""
    try:
        r = subprocess.run(
            ["git", "cat-file", "-t", sha],
            cwd=str(repo), capture_output=True, text=True, timeout=10,
        )
        return r.returncode == 0 and r.stdout.strip() == "commit"
    except Exception:
        return False


def clone_pinned(url: str, commit: str, target: Path, fact: dict) -> str | None:
    """Clone the repo at the exact commit (detached). Return None on
    success or an error string on failure."""
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = subprocess.run(
            ["git", "clone", url, str(target)],
            capture_output=True, text=True, timeout=300,
        )
        if r.returncode != 0:
            fact["operation"] = "git clone"
            fact["reason"] = r.stderr.strip() or "git clone returned non-zero"
            return "BASELINE_UNAVAILABLE"
    except Exception as exc:
        fact["operation"] = "git clone"
        fact["reason"] = str(exc)
        return "BASELINE_UNAVAILABLE"
    # Move HEAD to the pinned commit (detached) — only on the
    # isolated runtime clone, never on a user repo
    try:
        r = subprocess.run(
            ["git", "reset", "--hard", commit],
            cwd=str(target), capture_output=True, text=True, timeout=60,
        )
        if r.returncode != 0:
            fact["operation"] = "git reset --hard <pin>"
            fact["reason"] = r.stderr.strip() or "reset failed"
            return "BASELINE_UNAVAILABLE"
    except Exception as exc:
        fact["operation"] = "git reset --hard <pin>"
        fact["reason"] = str(exc)
        return "BASELINE_UNAVAILABLE"
    return None


def fetch_into_existing(repo: Path, commit: str, fact: dict) -> str | None:
    """If the user supplied a pre-existing repo but it doesn't yet have
    the pinned commit object, try a non-destructive fetch.

    We NEVER do `git checkout <pin>`, `git reset --hard`, `git clean`,
    or branch switch in a user repo. If we cannot fetch the exact
    commit safely, the caller falls back to an isolated runtime clone.
    """
    try:
        # `git fetch origin` is non-destructive to the worktree
        r = subprocess.run(
            ["git", "fetch", "origin"],
            cwd=str(repo), capture_output=True, text=True, timeout=300,
        )
        # A fetch failure is not fatal: we may still have the object
        # locally. We only care whether the commit object is present.
        fact["operation"] = "git fetch origin (read-only; on user repo if overridden)"
    except Exception as exc:
        fact["operation"] = "git fetch origin"
        fact["reason"] = str(exc)
        # Fall through: still check whether the object is present
    if git_object_present(repo, commit):
        return None
    return "BASELINE_UNAVAILABLE"


def ensure_pinned(name: str, info: dict, override_env: str | None) -> tuple[str, Path]:
    """Resolve one pinned dependency. Return (status, path)."""
    fact: dict = {
        "component": f"resolver.{name}",
        "required_repository": info["repo"],
        "required_commit": info["commit"],
    }
    runtime_clone = repos_dir() / name

    # If an isolated runtime clone already exists at the right SHA, we
    # are done. This is the cheap happy path.
    if runtime_clone.is_dir():
        head = git_head_sha(runtime_clone)
        if head == info["commit"]:
            fact["resolved_path"] = str(runtime_clone)
            fact["operation"] = "verified existing runtime clone"
            fact["status"] = "READY"
            _emit_fact(fact)
            return "READY", runtime_clone
        # Existing runtime clone is on a wrong SHA — corrupt cache
        fact["resolved_path"] = str(runtime_clone)
        fact["operation"] = "verified existing runtime clone"
        fact["reason"] = (
            f"runtime clone HEAD={head!r} but required={info['commit']!r}"
        )
        fact["next_action"] = "remove runtime cache and re-materialize"
        fact["status"] = "RUNTIME_CACHE_CORRUPT"
        _emit_fact(fact)
        return "RUNTIME_CACHE_CORRUPT", runtime_clone

    # Honor optional override (read-only against user repo)
    if override_env:
        override = Path(override_env).resolve()
        if override.is_dir():
            head = git_head_sha(override)
            if head == info["commit"]:
                fact["resolved_path"] = str(override)
                fact["operation"] = (
                    "verified user-supplied override (read-only; "
                    "no checkout, no reset, no clean, no branch switch)"
                )
                fact["status"] = "READY"
                _emit_fact(fact)
                return "READY", override
            # User repo on a different commit — do NOT touch it
            if git_object_present(override, info["commit"]):
                # Object reachable without checkout; safe to consume
                fact["resolved_path"] = str(override)
                fact["operation"] = (
                    "user override has required commit object; "
                    "consumed read-only without checkout"
                )
                fact["status"] = "READY"
                _emit_fact(fact)
                return "READY", override
            # Wrong commit; try a non-destructive fetch
            fetch_status = fetch_into_existing(override, info["commit"], fact)
            if fetch_status is None:
                fact["resolved_path"] = str(override)
                fact["operation"] = (
                    "fetched into user override (read-only) and "
                    "verified required commit object"
                )
                fact["status"] = "READY"
                _emit_fact(fact)
                return "READY", override
            # Fall through: still missing, and we won't mutate the user
            # repo. We materialize an isolated runtime clone instead.
            fact["reason"] = (
                "user override missing required commit and no destructive "
                "mutation permitted; materializing isolated runtime clone"
            )
            err = clone_pinned(info["repo"], info["commit"], runtime_clone, fact)
            if err is None:
                fact["resolved_path"] = str(runtime_clone)
                fact["operation"] = "isolated runtime clone (user repo untouched)"
                fact["status"] = "READY"
                _emit_fact(fact)
                return "READY", runtime_clone
            fact["status"] = err
            fact["next_action"] = "verify network access to upstream repo"
            _emit_fact(fact)
            return err, runtime_clone
        # Override path does not exist
        fact["reason"] = f"override path does not exist: {override}"
        fact["next_action"] = "unset override or fix the path"
        fact["status"] = "BASELINE_MISMATCH"
        _emit_fact(fact)
        return "BASELINE_MISMATCH", override

    # No override; check the default runtime home first
    if not runtime_clone.parent.is_dir():
        try:
            runtime_clone.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            fact["reason"] = f"cannot create runtime repos dir: {exc}"
            fact["next_action"] = "check $MAFS_RUNTIME_HOME permissions"
            fact["status"] = "RUNTIME_CACHE_CORRUPT"
            _emit_fact(fact)
            return "RUNTIME_CACHE_CORRUPT", runtime_clone

    # First-time materialization
    fact["operation"] = "isolated runtime clone (first time)"
    err = clone_pinned(info["repo"], info["commit"], runtime_clone, fact)
    if err is None:
        fact["resolved_path"] = str(runtime_clone)
        fact["status"] = "BASELINE_MATERIALIZATION_REQUIRED -> READY"
        _emit_fact(fact)
        return "READY", runtime_clone
    fact["status"] = err
    fact["next_action"] = "verify network access to upstream repo"
    _emit_fact(fact)
    return err, runtime_clone


def _emit_fact(fact: dict) -> None:
    print("RESOLVER_FACT_BEGIN")
    for k in (
        "status", "component", "required_repository", "required_commit",
        "resolved_path", "operation", "reason", "next_action",
    ):
        v = fact.get(k, "")
        print(f"{k}: {v}")
    print("RESOLVER_FACT_END")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cqc-override", default=os.environ.get("MAFS_CQC_REPO", ""))
    ap.add_argument("--mafs-override", default=os.environ.get("MAFS_ENGINE_REPO", ""))
    ap.add_argument("--quiet", action="store_true",
                    help="emit only the final summary line per dependency")
    args = ap.parse_args(argv)

    git_err = check_git()
    if git_err:
        print(f"DEPENDENCY_TOOL_MISSING: {git_err}")
        return 1

    baselines = load_baselines()
    cqc_info = baselines["cqc"]
    mafs_info = baselines["mafs"]

    repos_dir().mkdir(parents=True, exist_ok=True)
    state_dir().mkdir(parents=True, exist_ok=True)
    logs_dir().mkdir(parents=True, exist_ok=True)

    cqc_status, _ = ensure_pinned(CQC_NAME, cqc_info, args.cqc_override or None)
    mafs_status, _ = ensure_pinned(MAFS_NAME, mafs_info, args.mafs_override or None)

    print(f"CQC_RESOLVER: {cqc_status}")
    print(f"MAFS_RESOLVER: {mafs_status}")

    if cqc_status == "READY" and mafs_status == "READY":
        print("OVERALL: READY")
        return 0
    if cqc_status in ("RUNTIME_CACHE_CORRUPT",) or mafs_status in ("RUNTIME_CACHE_CORRUPT",):
        print("OVERALL: RUNTIME_CACHE_CORRUPT")
        return 1
    if cqc_status in ("BASELINE_UNAVAILABLE",) or mafs_status in ("BASELINE_UNAVAILABLE",):
        print("OVERALL: BASELINE_UNAVAILABLE")
        return 1
    if cqc_status in ("BASELINE_MISMATCH",) or mafs_status in ("BASELINE_MISMATCH",):
        print("OVERALL: BASELINE_MISMATCH")
        return 1
    if cqc_status in ("BASELINE_MATERIALIZATION_REQUIRED",) or mafs_status in (
        "BASELINE_MATERIALIZATION_REQUIRED",
    ):
        print("OVERALL: BASELINE_MATERIALIZATION_REQUIRED")
        return 0
    print("OVERALL: UNKNOWN")
    return 1


if __name__ == "__main__":
    sys.exit(main())
