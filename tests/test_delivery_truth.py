"""test_delivery_truth.py — delivery truth acceptance (contract §34, §38)."""
from __future__ import annotations

import hashlib
import json
import sys
import unittest
import zipfile
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "scripts"))

import build_release  # noqa: E402
import install  # noqa: E402
import verify_delivery  # noqa: E402


class TestDeliveryTruth(unittest.TestCase):
    def test_pins_match_baselines(self) -> None:
        baselines = json.loads((PKG / "release" / "BASELINES.json").read_text(encoding="utf-8"))
        self.assertEqual(len(baselines["cqc"]["commit"]), 40)
        self.assertEqual(len(baselines["mafs"]["commit"]), 40)
        self.assertTrue(baselines["cqc"]["commit"].startswith("b34a122"))
        self.assertTrue(baselines["mafs"]["commit"].startswith("cd09699"))

    def test_canonical_skill_core_present(self) -> None:
        self.assertTrue(verify_delivery.check_skill_core_files())

    def test_no_vendor_or_submodule(self) -> None:
        self.assertTrue(verify_delivery.check_no_vendor())
        self.assertTrue(verify_delivery.check_no_submodule())

    def test_no_external_python_bootstrap_dependency(self) -> None:
        import re as _re
        forbid = ("yaml", "requests", "pydantic", "gitpython", "urllib3")
        for py in (PKG / "scripts").glob("*.py"):
            text = py.read_text(encoding="utf-8")
            for line in text.splitlines():
                stripped = line.lstrip()
                if stripped.startswith("#"):
                    continue
                for f in forbid:
                    if _re.match(rf"^(import|from)\s+{f}(\b|$)", stripped):
                        self.fail(f"forbidden import in {py.name}: {line!r}")

    def test_no_codex_specific_path_in_core(self) -> None:
        self.assertTrue(verify_delivery.check_no_codex_path_in_core())

    def test_zip_skill_core_byte_consistent_with_repo(self) -> None:
        """Contract §34: portable zip Skill core must be byte-consistent
        with the repository Skill core."""
        version = install.read_version()
        zip_path, _ = build_release.build_zip(version)
        with zipfile.ZipFile(zip_path) as zf:
            zf_skill = zf.read("mafs-skill/skill/mafs-skill-1-0/SKILL.md")
        repo_skill = (PKG / "skill" / "mafs-skill-1-0" / "SKILL.md").read_bytes()
        self.assertEqual(
            hashlib.sha256(zf_skill).hexdigest(),
            hashlib.sha256(repo_skill).hexdigest(),
            "SKILL.md bytes differ between repo and portable zip",
        )

    def test_release_manifest_has_required_keys(self) -> None:
        m = json.loads((PKG / "release" / "DELIVERY_MANIFEST.json").read_text(encoding="utf-8"))
        for k in (
            "product", "version", "machine_name",
            "cqc", "mafs", "required_files", "bootstrap_scripts",
            "python_external_bootstrap_dependencies", "git_required",
            "offline_complete", "portable_package",
        ):
            self.assertIn(k, m, f"manifest missing key: {k}")
        self.assertEqual(m["python_external_bootstrap_dependencies"], [])
        self.assertTrue(m["git_required"])
        self.assertFalse(m["offline_complete"])

    def test_sha256sums_covers_zip(self) -> None:
        sums = (PKG / "release" / "SHA256SUMS.txt").read_text(encoding="utf-8")
        self.assertIn("dist/MAFS_Skill_1.0.0_Portable.zip", sums)


if __name__ == "__main__":
    unittest.main()
