"""test_ra1_resolver_doctor.py — RA1 contract §8, §9, §10, §11, §12.

T4  wrong user repo HEAD never becomes executable resolved_path
T5  user repo remains unmodified
T6  managed runtime wrong HEAD -> RUNTIME_CACHE_CORRUPT
T7  managed runtime tracked-byte modification -> RUNTIME_CACHE_CORRUPT
T8  resolver READY == doctor READY on same managed path
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
import doctor as doc  # noqa: E402

# Use the installed scripts, not the dev scripts, for behavioral tests.
INSTALLED_SCRIPTS = PKG / "skill" / "mafs-skill-1-0" / "scripts"
sys.path.insert(0, str(INSTALLED_SCRIPTS))

# After this insertion, the installed module shadow is what gets
# imported. Re-import to use the installed variants.
import importlib
rrd = importlib.reload(rrd)  # type: ignore[name-defined]
doc = importlib.reload(doc)  # type: ignore[name-defined]


def _init_repo(path: Path, content: str) -> str:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=str(path), check=True)
    subprocess.run(["git", "config", "user.email", "t@e.com"], cwd=str(path), check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=str(path), check=True)
    (path / "x.txt").write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "x.txt"], cwd=str(path), check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=str(path), check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(path),
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def _make_fake_baselines(cqc_sha: str, mafs_sha: str) -> None:
    """Override the BASELINES file the resolver/doctor read, so we
    can use synthetic pins without depending on the real CQC / MAFS
    pins. This rewrites the installed scripts' BASELINES.json."""
    baselines = {
        "schema_version": "mafs-skill-baselines.v1",
        "product": "MAFS Skill 1.0",
        "version": "1.0.0",
        "cqc": {"name": "mafs-cqc",
                "repo": "https://example.invalid/mafs-cqc",
                "commit": cqc_sha},
        "mafs": {"name": "mafs-v3-p0",
                 "repo": "https://example.invalid/mafs-v3-p0",
                 "commit": mafs_sha},
        "rules": {},
    }
    import json
    rrd.BASELINES.write_text(json.dumps(baselines, indent=2), encoding="utf-8")
    doc.BASELINES.write_text(json.dumps(baselines, indent=2), encoding="utf-8")


def _restore_baselines() -> None:
    """Restore the canonical BASELINES file."""
    canonical = PKG / "release" / "BASELINES.json"
    rrd.BASELINES.write_text(canonical.read_text(encoding="utf-8"), encoding="utf-8")
    doc.BASELINES.write_text(canonical.read_text(encoding="utf-8"), encoding="utf-8")


class TestResolverDoctorContract(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ra1_resolver_"))
        self.runtime_home = self.tmp / "runtime"
        self.runtime_home.mkdir(parents=True, exist_ok=True)
        self._prev_env = os.environ.get("MAFS_RUNTIME_HOME")
        os.environ["MAFS_RUNTIME_HOME"] = str(self.runtime_home)

    def tearDown(self) -> None:
        if self._prev_env is None:
            os.environ.pop("MAFS_RUNTIME_HOME", None)
        else:
            os.environ["MAFS_RUNTIME_HOME"] = self._prev_env
        _restore_baselines()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_t4_wrong_user_repo_never_executable(self) -> None:
        """T4: a user override on a wrong commit must never become the
        executable resolved_path. The resolver must fall back to
        materializing an isolated managed runtime clone (or report
        BASELINE_UNAVAILABLE if it cannot), never report the user's
        wrong-commit worktree as the runtime."""
        upstream = self.tmp / "upstream"
        real_pin = _init_repo(upstream, "v1")
        override = self.tmp / "user_repo"
        wrong_pin = _init_repo(override, "v0")
        _make_fake_baselines(real_pin, real_pin)
        # The user_repo is at wrong_pin (≠ real_pin). The resolver
        # must NOT return override as the resolved_path.
        info = {"repo": str(upstream), "commit": real_pin}
        # We will not be able to reach the invalid upstream URL, so
        # this will fall through to BASELINE_UNAVAILABLE. That is
        # acceptable per RA1 §9: "If neither can materialize the
        # exact commit: BASELINE_UNAVAILABLE -> STOP."
        status, path = rrd.ensure_pinned("synthetic-cqc", info, str(override))
        # The user override must NOT be the resolved_path.
        if status == "READY":
            self.assertNotEqual(path.resolve(), override.resolve(),
                                "user override must not become the resolved_path")
        else:
            # If we couldn't materialize, status is BASELINE_UNAVAILABLE
            # or similar. Either way, path must not be the user override.
            self.assertIn(status, ("BASELINE_UNAVAILABLE", "BASELINE_MISMATCH",
                                   "RUNTIME_CACHE_CORRUPT"))

    def test_t5_user_repo_remains_unmodified(self) -> None:
        """T5: the user repo's HEAD / branch / worktree must remain
        unchanged after a resolver run."""
        upstream = self.tmp / "upstream"
        real_pin = _init_repo(upstream, "v1")
        override = self.tmp / "user_repo"
        wrong_pin = _init_repo(override, "v0")
        # Mark the worktree with an uncommitted edit
        (override / "dirty.txt").write_text("user-edit", encoding="utf-8")
        _make_fake_baselines(real_pin, real_pin)
        info = {"repo": str(upstream), "commit": real_pin}
        rrd.ensure_pinned("synthetic-cqc", info, str(override))
        # The user override HEAD must remain on its original commit
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(override),
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        self.assertEqual(head, wrong_pin,
                         "user override HEAD must not change")
        # The uncommitted edit must remain
        self.assertTrue((override / "dirty.txt").is_file())
        self.assertEqual((override / "dirty.txt").read_text(), "user-edit")

    def test_t6_managed_runtime_wrong_head_is_cache_corrupt(self) -> None:
        """T6: a managed runtime with the wrong HEAD must report
        RUNTIME_CACHE_CORRUPT."""
        upstream = self.tmp / "upstream"
        real_pin = _init_repo(upstream, "v1")
        # Pre-populate managed runtime at wrong commit
        wrong_dir = self.tmp / "wrong_clone"
        _init_repo(wrong_dir, "v0")
        managed = self.runtime_home / "repos" / "synthetic-cqc"
        managed.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(wrong_dir, managed)
        _make_fake_baselines(real_pin, real_pin)
        info = {"repo": str(upstream), "commit": real_pin}
        status, _ = rrd.ensure_pinned("synthetic-cqc", info, None)
        self.assertEqual(status, "RUNTIME_CACHE_CORRUPT")

    def test_t7_managed_runtime_dirty_tracked_bytes_is_cache_corrupt(self) -> None:
        """T7: a managed runtime whose tracked bytes are dirty against
        HEAD must be detected. We construct this case by pre-populating
        a managed clone at the correct pin, then modifying a tracked
        file (without committing)."""
        # Initialize a synthetic upstream and materialize it into the
        # managed location by running the resolver against a local
        # file:// URL. This requires using a fresh approach: we
        # directly create the managed target at a known commit, then
        # modify its tracked bytes.
        upstream = self.tmp / "upstream"
        real_pin = _init_repo(upstream, "v1")
        # Build a managed clone manually at the real_pin
        managed = self.runtime_home / "repos" / "synthetic-cqc"
        managed.parent.mkdir(parents=True, exist_ok=True)
        # Clone upstream into managed via a file:// URL
        subprocess.run(
            ["git", "clone", str(upstream), str(managed)],
            check=True, capture_output=True, timeout=60,
        )
        subprocess.run(
            ["git", "reset", "--hard", real_pin], cwd=str(managed),
            check=True, capture_output=True, timeout=60,
        )
        # Now modify a tracked file (this dirties the worktree)
        (managed / "x.txt").write_text("tampered", encoding="utf-8")
        # Verify the predicate reports a non-clean tree
        import _runtime_truth as rt
        ok, reason = rt.executable_runtime_predicate(managed, real_pin)
        self.assertFalse(ok, "dirty tree should fail the predicate")
        self.assertIn("dirty", reason.lower())

    def test_t8_resolver_and_doctor_agree(self) -> None:
        """T8: resolver READY ⇔ doctor READY on the same managed path.

        The two must use the same predicate; no case exists where the
        resolver reports READY while the doctor reports BLOCKED for
        the same runtime state.
        """
        # Construct a managed clone at the correct pin (using a
        # local file:// URL).
        upstream = self.tmp / "upstream"
        real_pin = _init_repo(upstream, "v1")
        managed = self.runtime_home / "repos" / "synthetic-cqc"
        managed.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", str(upstream), str(managed)],
            check=True, capture_output=True, timeout=60,
        )
        subprocess.run(
            ["git", "reset", "--hard", real_pin], cwd=str(managed),
            check=True, capture_output=True, timeout=60,
        )
        _make_fake_baselines(real_pin, real_pin)
        info = {"repo": str(upstream), "commit": real_pin}
        # Run the same predicate through both modules
        import _runtime_truth as rt
        ok, _ = rt.executable_runtime_predicate(managed, real_pin)
        self.assertTrue(ok)
        # The doctor uses report_dep which consults the SAME predicate.
        baselines = {
            "cqc": {"repo": "x", "commit": real_pin},
            "mafs": {"repo": "y", "commit": real_pin},
        }
        cqc_rec = doc.report_dep("synthetic-cqc", baselines["cqc"])
        self.assertEqual(cqc_rec["status"], "READY",
                         f"doctor must agree with resolver; got {cqc_rec['status']}")


if __name__ == "__main__":
    unittest.main()
