"""Shared runtime-truth predicate (RA1 §10, §11).

Used by both the development scripts and the installed Skill scripts.
When installed, `_runtime_truth.py` lives next to its callers; in the
development repository it lives under scripts/. Either way it is
imported as a sibling module.

The predicate answers the single question: is `repo_path` an executable
managed-runtime checkout at the exact required 40-char SHA, with a
clean tracked worktree?
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


def runtime_home() -> Path:
    return Path(os.environ.get(
        "MAFS_RUNTIME_HOME",
        str(Path(os.path.expanduser("~")) / ".mafs" / "skill-1.0"),
    ))


def managed_repos_dir() -> Path:
    return runtime_home() / "repos"


def is_under_managed_home(repo_path: Path) -> bool:
    """True iff repo_path is inside the managed runtime home."""
    try:
        repo_path.resolve().relative_to(managed_repos_dir().resolve())
        return True
    except ValueError:
        return False


def head_sha(repo: Path) -> str | None:
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


def tracked_worktree_clean(repo: Path) -> bool:
    """True iff `git diff --quiet HEAD --` and `git diff --cached --quiet
    HEAD --` both return 0. Untracked files are allowed (they are not
    in the tracked worktree bytes)."""
    try:
        r1 = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--"],
            cwd=str(repo), capture_output=True, timeout=15,
        )
        if r1.returncode != 0:
            return False
        r2 = subprocess.run(
            ["git", "diff", "--cached", "--quiet", "HEAD", "--"],
            cwd=str(repo), capture_output=True, timeout=15,
        )
        return r2.returncode == 0
    except Exception:
        return False


def executable_runtime_predicate(repo_path: Path, required_sha: str) -> tuple[bool, str]:
    """The single executable-runtime predicate (RA1 §10).

    A managed dependency is executable only when ALL of:

        1. repo_path is inside the managed runtime home
        2. HEAD == required 40-char SHA
        3. tracked worktree bytes are clean against HEAD

    Returns (ok, reason). reason is "" when ok is True.
    """
    if not is_under_managed_home(repo_path):
        return False, f"path {repo_path} is not under managed runtime home {managed_repos_dir()}"
    sha = head_sha(repo_path)
    if sha is None:
        return False, "git rev-parse HEAD failed"
    if sha != required_sha:
        return False, f"HEAD={sha[:12]}... != required {required_sha[:12]}..."
    if not tracked_worktree_clean(repo_path):
        return False, "tracked worktree bytes are dirty against HEAD"
    return True, ""
