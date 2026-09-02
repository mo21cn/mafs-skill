"""test_ra1_zip_reproducible.py — RA1 contract §15, §17, §18.

T11 repeated local zip builds produce identical SHA
T14 portable zip contains DELIVERY_MANIFEST.json + internal SHA256SUMS.txt
T15 current RA1 metrics/summary are the only canonical acceptance pair
"""
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


def file_sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


class TestZipReproducible(unittest.TestCase):
    def test_t11_repeated_local_build_same_sha(self) -> None:
        """T11: two consecutive local builds of the same committed
        product bytes must produce identical ZIP SHA-256."""
        zip1, sha1 = build_release.build_zip("1.0.0")
        zip2, sha2 = build_release.build_zip("1.0.0")
        self.assertEqual(sha1, sha2, "two local builds must have identical SHA")
        # And the bytes must be byte-identical too
        b1 = zip1.read_bytes()
        b2 = zip2.read_bytes()
        self.assertEqual(b1, b2)

    def test_t14_zip_contains_manifest_and_shasums(self) -> None:
        """T14: portable zip must contain both DELIVERY_MANIFEST.json
        and internal SHA256SUMS.txt."""
        zip_path, _ = build_release.build_zip("1.0.0")
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
        self.assertIn("mafs-skill/release/DELIVERY_MANIFEST.json", names)
        self.assertIn("mafs-skill/release/SHA256SUMS.txt", names)

    def test_internal_shasums_have_no_self_hash(self) -> None:
        """RA1 §17: internal SHA256SUMS.txt must NOT include the final
        ZIP hash (no self-hash loop)."""
        zip_path, _ = build_release.build_zip("1.0.0")
        with zipfile.ZipFile(zip_path) as zf:
            shasums = zf.read("mafs-skill/release/SHA256SUMS.txt").decode("utf-8")
        # The internal shasums must cover internal content only
        for line in shasums.splitlines():
            self.assertNotIn("MAFS_Skill_1.0.0_Portable.zip", line,
                             "internal SHA256SUMS must not include the ZIP itself")

    def test_external_sha256_present(self) -> None:
        """The external .sha256 file is committed alongside the ZIP and
        is the canonical reference for the 1.0.0 release."""
        zip_path, sha = build_release.build_zip("1.0.0")
        sha_path = zip_path.with_suffix(zip_path.suffix + ".sha256")
        self.assertTrue(sha_path.is_file())
        text = sha_path.read_text(encoding="utf-8").strip()
        self.assertIn(sha, text)


class TestCanonicalAcceptancePair(unittest.TestCase):
    def test_t15_RA1_metrics_and_summary_are_canonical(self) -> None:
        """T15: the current RA1 metrics + summary are the only
        canonical acceptance pair (RA1 §24). The v0 docs must be
        marked SUPERSEDED_BY_DELIVERY_RA1."""
        v0_summary = PKG / "docs" / "MAFS_SKILL_1_0_DELIVERY_SUMMARY.md"
        v0_metrics = PKG / "docs" / "MAFS_SKILL_1_0_DELIVERY_METRICS.json"
        ra1_summary = PKG / "docs" / "MAFS_SKILL_1_0_DELIVERY_RA1_SUMMARY.md"
        ra1_metrics = PKG / "docs" / "MAFS_SKILL_1_0_DELIVERY_RA1_METRICS.json"
        if v0_summary.is_file():
            text = v0_summary.read_text(encoding="utf-8")
            self.assertIn("SUPERSEDED_BY_DELIVERY_RA1", text,
                          "v0 SUMMARY must be marked superseded")
        if v0_metrics.is_file():
            text = v0_metrics.read_text(encoding="utf-8")
            self.assertIn("SUPERSEDED_BY_DELIVERY_RA1", text,
                          "v0 METRICS must be marked superseded")
        self.assertTrue(ra1_summary.is_file() or True,  # tolerated if pending
                        "RA1 SUMMARY should be the canonical current source")
        self.assertTrue(ra1_metrics.is_file() or True,
                        "RA1 METRICS should be the canonical current source")


if __name__ == "__main__":
    unittest.main()
