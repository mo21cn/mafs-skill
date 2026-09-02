"""test_portable_deployment.py — portable zip / generic install (contract §19, §27)."""
from __future__ import annotations

import hashlib
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "scripts"))

import build_release  # noqa: E402
import install  # noqa: E402


def _file_sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


class TestPortableDeployment(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="mafs_portable_test_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_build_release_produces_zip_and_sha(self) -> None:
        version = install.read_version()
        zip_path, zip_sha = build_release.build_zip(version)
        self.assertTrue(zip_path.is_file())
        self.assertTrue(zip_path.with_suffix(zip_path.suffix + ".sha256").is_file())
        # Recompute and confirm
        self.assertEqual(_file_sha256(zip_path), zip_sha)

    def test_zip_contains_canonical_skill_core(self) -> None:
        version = install.read_version()
        zip_path, _ = build_release.build_zip(version)
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
        self.assertIn("mafs-skill/skill/mafs-skill-1-0/SKILL.md", names)
        self.assertIn("mafs-skill/scripts/install.py", names)
        self.assertIn("mafs-skill/release/BASELINES.json", names)

    def test_install_from_zip_into_generic_target(self) -> None:
        version = install.read_version()
        zip_path, _ = build_release.build_zip(version)
        # Extract zip into a clean tmp dir
        extract_root = self.tmp / "extracted"
        extract_root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_root)
        # The extracted layout has the skill under mafs-skill/...
        target = self.tmp / "agent_skills" / "mafs-skill-1-0"
        # Copy the canonical skill core from the extracted tree
        src_core = extract_root / "mafs-skill" / "skill" / "mafs-skill-1-0"
        shutil.copytree(src_core, target)
        self.assertTrue((target / "SKILL.md").is_file())
        self.assertTrue((target / "agents" / "openai.yaml").is_file())

    def test_no_codex_specific_path_in_core_skill_md(self) -> None:
        core = PKG / "skill" / "mafs-skill-1-0" / "SKILL.md"
        text = core.read_text(encoding="utf-8")
        self.assertNotIn("\\.codex\\skills", text)
        self.assertNotIn("/.codex/skills", text)

    def test_no_external_python_bootstrap_dependency(self) -> None:
        # Build a small forbidden-import scanner: the bootstrap scripts
        # must not `import yaml` / `import requests` / `import pydantic`
        # / `import gitpython` / `import urllib3`. We match only on lines
        # that are actual statements (not comments / docstrings).
        import re as _re
        forbid = ("yaml", "requests", "pydantic", "gitpython", "urllib3")
        for py in (PKG / "scripts").glob("*.py"):
            text = py.read_text(encoding="utf-8")
            # Strip line-leading comments and string literals that mention
            # the package names. We keep this simple: any line that starts
            # (after optional whitespace) with `import <name>` or
            # `from <name> import` is a violation.
            for line in text.splitlines():
                stripped = line.lstrip()
                if stripped.startswith("#"):
                    continue
                for f in forbid:
                    if _re.match(rf"^(import|from)\s+{f}(\b|$)", stripped):
                        self.fail(f"forbidden import in {py.name}: {line!r}")

    def test_no_vendor_or_submodule(self) -> None:
        self.assertFalse((PKG / "cqc").exists())
        self.assertFalse((PKG / "mafs").exists())
        self.assertFalse((PKG / "vendor").exists())
        self.assertEqual(list(PKG.glob("**/.gitmodules")), [])


if __name__ == "__main__":
    unittest.main()
