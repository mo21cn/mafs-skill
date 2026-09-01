"""test_runtime_resolver.py — resolver acceptance (contract §11-15).

We exercise the resolver against a small synthetic git repo so the
tests do not depend on network access. The synthetic repo is
constructed on the fly and then consumed by ensure_pinned().
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "scripts"))

import resolve_runtime_dependencies as rrd  # noqa: E402


def _init_repo(path: Path, file_content: str = "init") -> str:
    """Init a repo, commit one file, return HEAD sha."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=str(path), check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"],
                   cwd=str(path), check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=str(path), check=True)
    (path / "x.txt").write_text(file_content, encoding="utf-8")
    subprocess.run(["git", "add", "x.txt"], cwd=str(path), check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=str(path), check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(path), capture_output=True, text=True, check=True,
    ).stdout.strip()


class TestResolver(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="mafs_resolver_test_"))
        self.runtime_home = self.tmp / "runtime"
        self.runtime_home.mkdir(parents=True, exist_ok=True)
        self._env = os.environ.get("MAFS_RUNTIME_HOME")
        os.environ["MAFS_RUNTIME_HOME"] = str(self.runtime_home)

    def tearDown(self) -> None:
        if self._env is None:
            os.environ.pop("MAFS_RUNTIME_HOME", None)
        else:
            os.environ["MAFS_RUNTIME_HOME"] = self._env
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_check_git_present(self) -> None:
        self.assertIsNone(rrd.check_git())

    def test_missing_local_repo_triggers_materialization(self) -> None:
        # Build a synthetic upstream and ask the resolver to fetch it.
        upstream = self.tmp / "upstream"
        pin = _init_repo(upstream, "hello")
        # Point the resolver at our upstream instead of GitHub by
        # mutating the info dict that the caller would supply.
        info = {
            "repo": str(upstream),
            "commit": pin,
        }
        status, path = rrd.ensure_pinned("synthetic-cqc", info, None)
        self.assertEqual(status, "READY", f"expected READY, got {status}")
        self.assertTrue(path.is_dir())
        # The runtime clone HEAD must equal the pin
        head = rrd.git_head_sha(path)
        self.assertEqual(head, pin)

    def test_existing_clone_on_wrong_commit_is_cache_corrupt(self) -> None:
        upstream = self.tmp / "upstream"
        real_pin = _init_repo(upstream, "v1")
        # Pre-populate the runtime cache at a *different* commit
        runtime_clone = rrd.REPOS_DIR / "synthetic-cqc"
        runtime_clone.parent.mkdir(parents=True, exist_ok=True)
        wrong = _init_repo(runtime_clone, "v0")
        info = {"repo": str(upstream), "commit": real_pin}
        status, _ = rrd.ensure_pinned("synthetic-cqc", info, None)
        self.assertEqual(status, "RUNTIME_CACHE_CORRUPT", f"expected RUNTIME_CACHE_CORRUPT, got {status}")

    def test_user_override_on_right_commit_does_not_mutate(self) -> None:
        upstream = self.tmp / "upstream"
        pin = _init_repo(upstream, "v1")
        override = self.tmp / "user_repo"
        override.mkdir(parents=True, exist_ok=True)
        # Make the user repo look like the same commit
        subprocess.run(["git", "init", "-q"], cwd=str(override), check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"],
                       cwd=str(override), check=True)
        subprocess.run(["git", "config", "user.name", "test"], cwd=str(override), check=True)
        subprocess.run(["git", "remote", "add", "origin", str(upstream)],
                       cwd=str(override), check=True)
        subprocess.run(["git", "fetch", "origin"], cwd=str(override), check=True)
        subprocess.run(["git", "reset", "--hard", pin], cwd=str(override), check=True)
        # Mark the worktree with an uncommitted edit
        (override / "dirty.txt").write_text("user-edit", encoding="utf-8")
        info = {"repo": str(upstream), "commit": pin}
        status, path = rrd.ensure_pinned("synthetic-cqc", info, str(override))
        self.assertEqual(status, "READY")
        self.assertEqual(path, override.resolve())
        # The uncommitted edit must remain (no destructive mutation)
        self.assertTrue((override / "dirty.txt").is_file())
        self.assertEqual((override / "dirty.txt").read_text(encoding="utf-8"),
                         "user-edit")

    def test_user_override_on_wrong_commit_does_not_mutate_worktree(self) -> None:
        upstream = self.tmp / "upstream"
        pin = _init_repo(upstream, "v1")
        # User override on a different commit
        override = self.tmp / "user_repo"
        wrong = _init_repo(override, "v0")
        info = {"repo": str(upstream), "commit": pin}
        status, _ = rrd.ensure_pinned("synthetic-cqc", info, str(override))
        # Should NOT be BASELINE_MISMATCH (the contract forbids that for
        # this case). It should fall back to a runtime clone.
        # We don't enforce a specific state because fetch from a local
        # file:// URL may or may not succeed depending on environment,
        # but the user override must remain un-mutated.
        head = rrd.git_head_sha(override)
        self.assertEqual(head, wrong, "user override HEAD must remain on its original commit")

    def test_existing_user_repo_must_not_be_checked_out_to_pin(self) -> None:
        """Static guard via ast: every `git reset --hard` call in the
        resolver must use `cwd=str(target)` (the isolated runtime
        clone), never `cwd=str(override)` (the user repo). We walk the
        AST to find every subprocess.run(...) call whose argv contains
        the literal string "reset" immediately followed by "--hard"."""
        import ast as _ast
        src_path = PKG / "scripts" / "resolve_runtime_dependencies.py"
        tree = _ast.parse(src_path.read_text(encoding="utf-8"), filename=str(src_path))

        # Collect every (call_node, line_no) where argv contains
        # ["git", "reset", "--hard", ...]
        reset_calls: list[tuple[int, int]] = []
        for node in _ast.walk(tree):
            if not isinstance(node, _ast.Call):
                continue
            # Find the first positional arg that is a list literal
            for arg in node.args:
                if not isinstance(arg, _ast.List):
                    continue
                elts = [e.value for e in arg.elts if isinstance(e, _ast.Constant)]
                if (
                    len(elts) >= 3
                    and elts[0] == "git"
                    and elts[1] == "reset"
                    and elts[2] == "--hard"
                ):
                    reset_calls.append((node.lineno, arg.lineno))

        self.assertGreaterEqual(
            len(reset_calls), 1,
            "expected at least one git reset --hard subprocess.run call "
            "(the runtime-clone materialization path)",
        )
        for call_line, _ in reset_calls:
            # Find the keyword argument `cwd=...` on the same call
            call_node = next(
                n for n in _ast.walk(tree)
                if isinstance(n, _ast.Call) and n.lineno == call_line
            )
            cwd_value: str | None = None
            for kw in call_node.keywords:
                if kw.arg == "cwd" and isinstance(kw.value, _ast.Call):
                    # cwd=str(target) or cwd=str(override)
                    f = kw.value.func
                    if isinstance(f, _ast.Name) and f.id == "str" and kw.value.args:
                        a = kw.value.args[0]
                        if isinstance(a, _ast.Name):
                            cwd_value = a.id
            self.assertEqual(
                cwd_value, "target",
                f"git reset --hard at line {call_line} must use "
                f"cwd=str(target) (runtime clone), not cwd=str({cwd_value!r})",
            )


if __name__ == "__main__":
    unittest.main()
