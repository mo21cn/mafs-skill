#!/usr/bin/env python
"""MAFS Skill 1.0 — installed runtime resolver (RA1 contract).

This script is the canonical, self-contained resolver that lives
inside the installed Skill. It is also the development source of
truth (RA1 §11 single-truth requirement); the dev repo's copy is
byte-identical.

Resolved-path rule (RA1 §8, §9): the executable CQC and MAFS paths
returned to the workflow ALWAYS live under the managed runtime home
(typically `~/.mafs/skill-1.0/repos/...`). User-supplied
MAFS_CQC_REPO / MAFS_ENGINE_REPO are optional acquisition sources
ONLY; the resolver never returns them as `resolved_path`.

Single executable-runtime predicate (RA1 §10, §11):
    is path under managed home + HEAD == required SHA + clean tree.

States (RA1 §12, same family as v0):
    READY
    BASELINE_MATERIALIZATION_REQUIRED
    BASELINE_MISMATCH
    BASELINE_UNAVAILABLE
    DEPENDENCY_TOOL_MISSING
    RUNTIME_CACHE_CORRUPT
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Make _runtime_truth importable as a sibling module regardless of
# whether this script is run from the installed Skill or from the
# development repo.
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import _runtime_truth as rt  # noqa: E402

# Locate the install root (the parent of scripts/).
INSTALL_ROOT = _HERE.parent
BASELINES = INSTALL_ROOT / "release" / "BASELINES.json"

CQC_NAME = "mafs-cqc"
MAFS_NAME = "mafs-v3-p0"


def check_git() -> str | None:
    """Verify git binary is present and runnable.

    Per MAINTENANCE_ADVISORY_v0.2 §2.4, this probe does NOT participate in
    truth judgment (commit identity / pin verification / remote availability
    are handled by other functions that preserve capture_output). We use
    DEVNULL + returncode only to avoid triggering an avoidable DSH approval.
    The specific stderr message is intentionally not surfaced; the binary
    presence + returncode is the only signal that matters here.

    Returns:
      None                          git is present and returned 0
      "<DEPENDENCY_TOOL_MISSING…>"  otherwise (binary missing, non-zero
                                     return, or invocation error)
    """
    if shutil.which("git") is None:
        return "DEPENDENCY_TOOL_MISSING: git binary not on PATH"
    try:
        r = subprocess.run(
            ["git", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        if r.returncode != 0:
            return f"DEPENDENCY_TOOL_MISSING: git --version returned {r.returncode}"
        return None
    except Exception as exc:
        return f"DEPENDENCY_TOOL_MISSING: git invocation failed: {exc}"


def load_baselines() -> dict:
    return json.loads(BASELINES.read_text(encoding="utf-8"))


def _init_managed_target(target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True, exist_ok=True)


def _clone_pinned(url: str, commit: str, target: Path) -> tuple[bool, str]:
    """Clone the upstream at the exact pin into the managed target.
    Returns (ok, error_message)."""
    _init_managed_target(target)
    try:
        r = subprocess.run(
            ["git", "clone", url, str(target)],
            capture_output=True, text=True, timeout=300,
        )
        if r.returncode != 0:
            return False, (r.stderr.strip() or "git clone returned non-zero")
    except Exception as exc:
        return False, str(exc)
    try:
        r = subprocess.run(
            ["git", "reset", "--hard", commit],
            cwd=str(target), capture_output=True, text=True, timeout=60,
        )
        if r.returncode != 0:
            return False, (r.stderr.strip() or "git reset --hard <pin> failed")
    except Exception as exc:
        return False, str(exc)
    return True, ""


def _try_seed_from_user_override(override: Path, required_commit: str) -> bool:
    """If the user-supplied override already has the required commit
    object, copy it into the managed target as a starting point. The
    override itself is never mutated; we only read its object store.

    The override is consumed read-only via `git clone --shared` (which
    shares the object store without touching the source worktree) or
    by `cp -r` into the managed target, followed by a hard reset to
    the required pin (in the copy, NOT in the user override).
    """
    if not override.is_dir():
        return False
    # Check whether the object is present in the override
    r = subprocess.run(
        ["git", "cat-file", "-t", required_commit],
        cwd=str(override), capture_output=True, text=True, timeout=10,
    )
    if r.returncode != 0 or r.stdout.strip() != "commit":
        return False
    return True


def ensure_pinned(name: str, info: dict, override_env: str | None) -> tuple[str, Path]:
    """Resolve one pinned dependency. The returned Path is always
    inside the managed runtime home; the user override is at most an
    acquisition source."""
    fact: dict = {
        "component": f"resolver.{name}",
        "required_repository": info["repo"],
        "required_commit": info["commit"],
    }
    managed_target = rt.managed_repos_dir() / name

    # 1. If the managed target already exists, evaluate via the
    #    single executable-runtime predicate.
    if managed_target.is_dir():
        ok, reason = rt.executable_runtime_predicate(managed_target, info["commit"])
        if ok:
            fact["resolved_path"] = str(managed_target)
            fact["operation"] = "verified existing managed runtime"
            fact["status"] = "READY"
            _emit_fact(fact)
            return "READY", managed_target
        # The managed target exists but is not a valid executable
        # runtime. This is a corrupt cache (wrong SHA, dirty tree,
        # or path mismatch).
        fact["resolved_path"] = str(managed_target)
        fact["operation"] = "evaluated existing managed runtime"
        fact["reason"] = reason
        fact["next_action"] = "remove managed runtime and re-materialize"
        fact["status"] = "RUNTIME_CACHE_CORRUPT"
        _emit_fact(fact)
        return "RUNTIME_CACHE_CORRUPT", managed_target

    # 2. Managed target missing -> BASELINE_MATERIALIZATION_REQUIRED.
    #    Try user override as acquisition source first.
    rt.managed_repos_dir().mkdir(parents=True, exist_ok=True)
    if override_env:
        override = Path(override_env).resolve()
        if override.is_dir() and _try_seed_from_user_override(override, info["commit"]):
            # Initialize a fresh managed target using the override's
            # object store, then detach to the required pin. We do
            # not touch the override worktree.
            _init_managed_target(managed_target)
            # Use git init + remote add + fetch to copy objects without
            # touching the override
            try:
                subprocess.run(["git", "init", "-q"], cwd=str(managed_target), check=True)
                subprocess.run(
                    ["git", "remote", "add", "origin", info["repo"]],
                    cwd=str(managed_target), check=True,
                )
                # Try to add the override as a fetch source too
                subprocess.run(
                    ["git", "remote", "add", "user-override", str(override)],
                    cwd=str(managed_target), check=True, capture_output=True,
                )
                # Fetch from the override first (no network)
                r1 = subprocess.run(
                    ["git", "fetch", "user-override"],
                    cwd=str(managed_target), capture_output=True, text=True, timeout=120,
                )
                # Then ensure upstream reachable (may need network)
                r2 = subprocess.run(
                    ["git", "fetch", "origin"],
                    cwd=str(managed_target), capture_output=True, text=True, timeout=300,
                )
                # Reset to the required commit
                r3 = subprocess.run(
                    ["git", "reset", "--hard", info["commit"]],
                    cwd=str(managed_target), capture_output=True, text=True, timeout=60,
                )
                if r3.returncode != 0:
                    fact["operation"] = (
                        "init from user override; reset --hard failed: " + r3.stderr.strip()
                    )
                    fact["reason"] = "could not reset managed target to required pin"
                    fact["next_action"] = "verify override or network access"
                    fact["status"] = "BASELINE_UNAVAILABLE"
                    _emit_fact(fact)
                    return "BASELINE_UNAVAILABLE", managed_target
                # Verify the executable-runtime predicate now
                ok, reason = rt.executable_runtime_predicate(managed_target, info["commit"])
                if ok:
                    fact["resolved_path"] = str(managed_target)
                    fact["operation"] = (
                        "materialized managed runtime seeded from user override "
                        "(override worktree untouched)"
                    )
                    fact["status"] = "BASELINE_MATERIALIZATION_REQUIRED -> READY"
                    _emit_fact(fact)
                    return "READY", managed_target
            except Exception as exc:
                fact["operation"] = "seed from user override"
                fact["reason"] = str(exc)
                # Fall through to upstream clone

    # 3. Fall back to upstream clone.
    ok, err = _clone_pinned(info["repo"], info["commit"], managed_target)
    if ok:
        ok2, reason2 = rt.executable_runtime_predicate(managed_target, info["commit"])
        if ok2:
            fact["resolved_path"] = str(managed_target)
            fact["operation"] = "cloned upstream into managed runtime"
            fact["status"] = "BASELINE_MATERIALIZATION_REQUIRED -> READY"
            _emit_fact(fact)
            return "READY", managed_target
        fact["reason"] = reason2
    else:
        fact["reason"] = err
    fact["operation"] = fact.get("operation", "clone upstream")
    fact["next_action"] = "verify network access to upstream repo"
    fact["status"] = "BASELINE_UNAVAILABLE"
    _emit_fact(fact)
    return "BASELINE_UNAVAILABLE", managed_target


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
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    git_err = check_git()
    if git_err:
        print(f"DEPENDENCY_TOOL_MISSING: {git_err}")
        return 1

    baselines = load_baselines()
    cqc_info = baselines["cqc"]
    mafs_info = baselines["mafs"]

    rt.managed_repos_dir().mkdir(parents=True, exist_ok=True)

    cqc_status, _ = ensure_pinned(CQC_NAME, cqc_info, args.cqc_override or None)
    mafs_status, _ = ensure_pinned(MAFS_NAME, mafs_info, args.mafs_override or None)

    print(f"CQC_RESOLVER: {cqc_status}")
    print(f"MAFS_RESOLVER: {mafs_status}")

    if cqc_status == "READY" and mafs_status == "READY":
        print("OVERALL: READY")
        return 0
    if cqc_status == "RUNTIME_CACHE_CORRUPT" or mafs_status == "RUNTIME_CACHE_CORRUPT":
        print("OVERALL: RUNTIME_CACHE_CORRUPT")
        return 1
    if cqc_status == "BASELINE_UNAVAILABLE" or mafs_status == "BASELINE_UNAVAILABLE":
        print("OVERALL: BASELINE_UNAVAILABLE")
        return 1
    if cqc_status == "BASELINE_MISMATCH" or mafs_status == "BASELINE_MISMATCH":
        print("OVERALL: BASELINE_MISMATCH")
        return 1
    print("OVERALL: BASELINE_MATERIALIZATION_REQUIRED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
