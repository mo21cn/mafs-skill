"""test_install.py — installer acceptance (contract §7 + §8)."""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "scripts"))

import install  # noqa: E402


class TestInstall(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="mafs_install_test_"))
        self.target = self.tmp / "skills"
        self.target.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_validate_source_no_missing(self) -> None:
        self.assertEqual(install.validate_source(), [])

    def test_read_version(self) -> None:
        self.assertEqual(install.read_version(), "1.0.0")

    def test_dry_run_codex(self) -> None:
        rc = install.main([
            "--target", "codex",
            "--target-dir", str(self.target),
            "--dry-run",
        ])
        self.assertEqual(rc, 0)
        self.assertFalse((self.target / "mafs-skill-1-0").exists())

    def test_install_then_already_installed(self) -> None:
        rc1 = install.main(["--target", "codex", "--target-dir", str(self.target)])
        self.assertEqual(rc1, 0)
        installed = self.target / "mafs-skill-1-0"
        self.assertTrue(installed.is_dir())
        # Second run: byte-identical -> ALREADY_INSTALLED, exit 0
        rc2 = install.main(["--target", "codex", "--target-dir", str(self.target)])
        self.assertEqual(rc2, 0)

    def test_installation_conflict_when_dir_exists_and_differs(self) -> None:
        rc1 = install.main(["--target", "codex", "--target-dir", str(self.target)])
        self.assertEqual(rc1, 0)
        # Corrupt one file under the install
        (self.target / "mafs-skill-1-0" / "SKILL.md").write_text("corrupted", encoding="utf-8")
        # Re-running must NOT clobber: it must report INSTALLATION_CONFLICT
        rc2 = install.main(["--target", "codex", "--target-dir", str(self.target)])
        self.assertEqual(rc2, 1)

    def test_no_target_is_error(self) -> None:
        with self.assertRaises(SystemExit):
            install.main([])

    def test_required_files_present_after_install(self) -> None:
        install.main(["--target", "codex", "--target-dir", str(self.target)])
        for rel in install.REQUIRED_FILES:
            self.assertTrue((self.target / "mafs-skill-1-0" / rel).is_file(),
                            f"missing {rel}")


if __name__ == "__main__":
    unittest.main()
