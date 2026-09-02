"""derive_evidence_id.py — stable canonical evidence identity.

Per MAINTENANCE_ADVISORY_v0.2 §2.1, the MAFS frozen pin's
`live_crossref.py:519` returns `CanonicalEvidence.evidence_id` as an empty
string, with a comment "backfilled by caller (resolve())" — but the
upstream `resolve()` itself does not backfill. This module provides a
**Skill compatibility-layer** backfill that is:

  - stable across repeated resolution of the same canonical evidence
  - **independent of resolver_invocation_id** (evidence identity != resolution
    invocation identity; see advisory §2.1 explicit prohibition of
    `hash(doi + resolver_invocation_id + title)`)
  - derived only from resolver-supported canonical identity / content

Do NOT use this in MAFS frozen pin code. It is a skill-layer helper that
drivers (e.g. `references/driver_template.py`) can import when wrapping
the MAFS `CrossrefReferenceResolver.resolve(...)` return value.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any


_DOI_NORMALIZE_RE = re.compile(r"^https?://(?:dx\.)?doi\.org/", re.IGNORECASE)


def _normalize_doi(doi: str) -> str:
    """Return the canonical lowercased DOI string, stripping URL prefix.

    Examples:
        "10.1038/nn.3741"                    -> "10.1038/nn.3741"
        "https://doi.org/10.1038/nn.3741"    -> "10.1038/nn.3741"
        "HTTPS://DX.DOI.ORG/10.1038/NN.3741" -> "10.1038/nn.3741"
    """
    if not doi:
        return ""
    s = _DOI_NORMALIZE_RE.sub("", doi.strip())
    return s.lower()


def _normalize_title(title: str) -> str:
    """Return a canonical form of the title for stable hashing.

    - Strip leading/trailing whitespace
    - Collapse internal whitespace to single space
    - Lowercase
    """
    if not title:
        return ""
    return re.sub(r"\s+", " ", title.strip()).lower()


def derive_evidence_id(*, doi: str, title: str) -> str:
    """Compute a stable evidence_id from canonical DOI + title.

    Output format: ``CE-<16 hex chars>``.

    The hash is over the **normalized** DOI + title. Two different
    resolutions of the same canonical paper (different invocations,
    different dates, different URL casings) MUST produce the same
    `evidence_id` — this is the entire point.

    This function does NOT take `resolver_invocation_id` as input, by
    design. See MAINTENANCE_ADVISORY_v0.2 §2.1 for the prohibition.
    """
    norm_doi = _normalize_doi(doi)
    norm_title = _normalize_title(title)
    if not norm_doi and not norm_title:
        # Defensive: refuse to mint a meaningless identity.
        raise ValueError("derive_evidence_id requires at least one of doi or title")
    h = hashlib.sha256(f"{norm_doi}|{norm_title}".encode("utf-8")).hexdigest()
    return f"CE-{h[:16]}"


def extract_canonical_fields(evidence: dict[str, Any] | None) -> tuple[str, str]:
    """Pull the canonical DOI + title out of a MAFS-resolved evidence dict.

    MAFS schema (from `live_crossref._build_canonical_evidence`):
        evidence["canonical"]["doi"]    -> str
        evidence["canonical"]["title"]  -> str

    Returns (doi, title) with empty strings if missing. Tolerant of
    `evidence is None` (resolution failure) and of the schema drift.
    """
    if not isinstance(evidence, dict):
        return ("", "")
    can = evidence.get("canonical") or {}
    return (
        str(can.get("doi") or ""),
        str(can.get("title") or ""),
    )
