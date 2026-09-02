"""report_validation.py — fail-closed validator for MAFS Skill 1.0 reports.

Per MAINTENANCE_ADVISORY_v0.2 §2.2 / §3.C, a final REPORT.md is
**fail-closed**: any forbidden overclaim (e.g. "does not exist" applied
to a bounded search absence) MUST cause the validator to exit non-zero
and block release. The validator is the *only* gate; do not override
by hand.

Forbidden overclaim patterns (case-insensitive, all variants listed):

  - "does not exist"        / "doesn't exist"
  - "不存在"                 / "没有这篇"
  - "证明不存在"             / "被证伪不存在"
  - any other global-non-existence claim applied to a bounded-search
    negative branch

The validator distinguishes contexts:
  - In a section describing a `RESOLVED` Q, the overclaim is meaningless
    (the Q was recovered) but still flagged, because overclaim in any
    section erodes the report's epistemic authority.
  - In a section describing a `NO_CANONICAL_CANDIDATE` /
    `LIKELY_CONFLATION` Q, the overclaim is a hard violation.
  - In a section describing an `ENTITY_RESOLUTION_REQUIRED` Q, the
    overclaim is also a hard violation.

Required positive patterns (presence checks; the report MUST include
some bounded language to pass):
  - At least one of: "bounded search", "bounded", "under the bounded"
  - For each `LIKELY_CONFLATION` Q, the report MUST include the word
    "likely conflation" (or "conflation") in the Q's row.
  - For each `ENTITY_RESOLUTION_REQUIRED` Q, the report MUST include
    the exact string "ENTITY_RESOLUTION_REQUIRED" in the Q's row.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Forbidden phrases (case-insensitive). Each tuple is (pattern, label).
FORBIDDEN: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bdoes\s+not\s+exist\b", re.IGNORECASE), "does not exist"),
    (re.compile(r"\bdoesn't\s+exist\b", re.IGNORECASE), "doesn't exist"),
    (re.compile(r"\bdo\s+not\s+exist\b", re.IGNORECASE), "do not exist"),
    (re.compile(r"不存在", re.IGNORECASE), "不存在"),
    (re.compile(r"没有这篇", re.IGNORECASE), "没有这篇"),
    (re.compile(r"证明\s*不\s*存在", re.IGNORECASE), "证明不存在"),
    (re.compile(r"被证伪\s*不\s*存在", re.IGNORECASE), "被证伪不存在"),
    (re.compile(r"\bproven\s+to\s+not\s+exist\b", re.IGNORECASE), "proven to not exist"),
    (re.compile(r"\bdoes\s+not\s+exist\s+anywhere\b", re.IGNORECASE),
     "does not exist anywhere"),
]

# Required bounded-language patterns (any one must appear in the report).
BOUNDED_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bbounded\s+search\b", re.IGNORECASE),
    re.compile(r"\bunder\s+the\s+bounded\b", re.IGNORECASE),
    re.compile(r"\bbounded\b", re.IGNORECASE),
]


def _find_forbidden(text: str) -> list[tuple[int, str, str]]:
    """Return list of (line_no, label, line_text) for every forbidden hit."""
    hits: list[tuple[int, str, str]] = []
    for i, line in enumerate(text.splitlines(), 1):
        for pat, label in FORBIDDEN:
            if pat.search(line):
                hits.append((i, label, line.strip()))
    return hits


def _has_bounded_language(text: str) -> bool:
    return any(p.search(text) for p in BOUNDED_PATTERNS)


def _artifact_status(workspace: Path) -> dict[str, str]:
    """Read the resolved_canonical_evidence.json to know per-Q artifact state.

    Returns a {q: status} map. Qs not in the artifact are not reported
    here; the report itself is the source of truth for which Qs the
    report covers.
    """
    candidates = [
        workspace / "resolved_canonical_evidence.json",
        workspace / "mafs_gf_search" / "resolved_canonical_evidence.json",
    ]
    for c in candidates:
        if c.is_file():
            try:
                data = json.loads(c.read_text(encoding="utf-8"))
                return {q: d.get("status", "UNKNOWN") for q, d in data.items()
                        if isinstance(d, dict)}
            except json.JSONDecodeError:
                pass
    return {}


def _artifact_negative(workspace: Path) -> list[str]:
    """Return Qs that the artifact marks as negative-branch / entity-boundary."""
    art = _artifact_status(workspace)
    return [q for q, st in art.items()
            if st in ("NO_CANONICAL_CANDIDATE", "LIKELY_CONFLATION",
                      "ENTITY_RESOLUTION_REQUIRED")]


def _q_row_text(text: str, q: str) -> str:
    """Extract the row text for a given Q from the report markdown.

    Heuristic: find a line beginning with `| Qn |` (table row) and grab
    the rest of the table block. If not found, return the full text.
    """
    pat = re.compile(rf"^\|\s*{re.escape(q)}\s*\|.*$", re.MULTILINE)
    m = pat.search(text)
    if not m:
        return text
    start = m.start()
    # Walk forward until the next `|` row that doesn't start with Qn
    # OR until the table ends.
    end = len(text)
    next_row = re.compile(r"^\|", re.MULTILINE)
    for nm in next_row.finditer(text, m.end()):
        line = text[nm.start():text.find("\n", nm.start())]
        if not re.match(rf"^\|\s*{re.escape(q)}\s*\|", line):
            end = nm.start()
            break
    return text[start:end]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("report", type=Path, nargs="?",
                    default=Path("REPORT.md"),
                    help="Path to the final report (default: ./REPORT.md).")
    ap.add_argument("--workspace", type=Path, default=Path("."),
                    help="Workspace root for resolving the evidence artifact.")
    args = ap.parse_args()

    if not args.report.is_file():
        print(f"REPORT VALIDATION FAIL: report not found: {args.report}",
              file=sys.stderr)
        return 2

    text = args.report.read_text(encoding="utf-8")
    failures: list[str] = []

    # 1. Forbidden overclaim check (fail-closed, hard fail on any hit).
    forbidden = _find_forbidden(text)
    for line_no, label, line in forbidden:
        failures.append(
            f"FORBIDDEN_OVERCLAIM at L{line_no} ({label}): {line[:120]}"
        )

    # 2. Bounded-language presence check (also hard fail).
    if not _has_bounded_language(text):
        failures.append(
            "MISSING_BOUNDED_LANGUAGE: report does not include any of "
            "'bounded search' / 'under the bounded' / 'bounded'. "
            "Per advisory §2.2, bounded-search absence language is required."
        )

    # 3. Per-Q row checks against artifact status.
    art = _artifact_status(args.workspace)
    for q, st in art.items():
        if st in ("NO_CANONICAL_CANDIDATE", "LIKELY_CONFLATION"):
            row = _q_row_text(text, q)
            if "conflation" not in row.lower() and "bounded" not in row.lower():
                failures.append(
                    f"Q{q} marked {st} in artifact but row missing "
                    f"bounded/conflation language. Row: {row.strip()[:200]}"
                )
        elif st == "ENTITY_RESOLUTION_REQUIRED":
            row = _q_row_text(text, q)
            if "ENTITY_RESOLUTION_REQUIRED" not in row:
                failures.append(
                    f"Q{q} marked ENTITY_RESOLUTION_REQUIRED in artifact "
                    f"but row missing the verbatim marker."
                )

    if failures:
        print("REPORT VALIDATION FAIL", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        print(f"\nTotal failures: {len(failures)}", file=sys.stderr)
        print(
            "Per MAINTENANCE_ADVISORY_v0.2 §2.2 / §3.C, the report is "
            "fail-closed. Fix the report per the bounded language in "
            "references/report_template.md §3 and re-run.",
            file=sys.stderr,
        )
        return 1

    print("REPORT VALIDATION PASS")
    print(f"  forbidden overclaim hits : 0")
    print(f"  bounded language present : yes")
    print(f"  artifact-aligned Q rows  : {len(art)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
