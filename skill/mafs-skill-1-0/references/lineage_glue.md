# Lineage Glue — model-authored Axis / SearchOrder

> **Status:** contract glue, not architecture change.
> Per `MAINTENANCE_ADVISORY_v0.2` §3.H, model-authored scientific planning
> (Axis IDs, SearchOrder IDs, the ladder of rendered queries) MUST be
> auditable from the CQC chain through to `discover()`. The deterministic
> layer MUST NOT auto-generate Axis / SearchOrder; **the model still
> owns the scientific planning meaning**. This document specifies the
> glue contract, not a code generator.

## 0. Why this exists

In the original GF/EM session, the binding-level
`integration_binding.json` had:

```json
"mafs_axis_id": null,
"mafs_search_order_ids": []
```

The model then generated the Axis / SearchOrder inside the driver
(`run_mafs_gf.py`) but did not persist them as a separate auditable
artifact, so the machine lineage CQC → MAFS had a gap:

```
CQC Binding
    ↓
[artifact lineage gap]
    ↓
model-authored Axis / SearchOrder
    ↓
MAFS discover()
```

The semantic chain was sound, but a future auditor could not machine-read
the planning from CQC to MAFS. This document specifies the contract for
closing that gap **without** auto-generating planning in deterministic
code.

## 1. The contract

### 1.1 Required artifact

Every MAFS run that follows the CQC chain MUST also write a
`mafs_planning.json` (or per-task variant) at workspace root with at
least the following fields:

```json
{
  "schema_version": "mafs-skill-planning.v1",
  "task_id": "<unique id, e.g. mafs-gf-em-2026-09-02>",
  "binding_id": "<integration_binding.artifact_id>",
  "authored_by": "model",
  "authored_at": "<iso8601>",
  "axes": [
    {
      "mafs_axis_id": "AX-Q1-vonReyn-2014",
      "requirement_id": "R01",
      "route_id": "paper_identity_crossref",
      "rationale": "<one-sentence model-authored reason>"
    }
  ],
  "search_orders": [
    {
      "mafs_search_order_id": "SO-Q1-vonReyn-2014",
      "mafs_axis_id": "AX-Q1-vonReyn-2014",
      "question_label": "Q1",
      "expected_doi": "10.1038/nn.3741",
      "expected_pmid": "24908103",
      "rendering_path": "<path string MAFS understands>",
      "ladder_rungs": [
        {
          "rendering_path": "...",
          "url_params": "..."
        }
      ]
    }
  ]
}
```

### 1.2 Backfill on the CQC binding

`integration_binding.json` MAY be augmented (by the model at planning
time, NOT by deterministic code) with a non-canonical field that points
at the planning artifact:

```json
{
  "mafs_planning_pointer": {
    "artifact": "mafs_planning.json",
    "artifact_sha256": "<hex>"
  }
}
```

This field is a **glue reference**, not a CQC binding semantic. CQC
validation MUST tolerate its presence or absence. (Per advisory: do not
reopen CQC semantics.)

### 1.3 Discovery artifact cross-reference

`discovery_candidate_pointers.json` MUST gain a sibling field per
search-order that references back to the planning artifact:

```json
{
  "Q1": {
    "mafs_search_order_id": "SO-Q1-vonReyn-2014",
    "mafs_axis_id": "AX-Q1-vonReyn-2014",
    "ladder_rungs": [...]
  }
}
```

This makes the chain **fully auditable** from CQC SRP requirement →
Axis → SearchOrder → CandidatePointer → ResolverInvocation →
CanonicalEvidence, with the planning intent captured as a machine
artifact.

## 2. What the deterministic layer MUST NOT do

Per advisory §3.H:

- MUST NOT auto-generate Axis IDs from requirements.
- MUST NOT auto-generate SearchOrder IDs from Axis.
- MUST NOT auto-render queries in the deterministic layer.
- MUST NOT auto-select a candidate.

The model owns all of the above. The deterministic layer only:

- Persists what the model wrote.
- Validates the shape (required fields present, schema_version correct).
- Lets the model edit / re-author / re-persist before any
  `discover()` call.

## 3. Validation hooks

A new `tests/test_planning_lineage.py` checks:

1. `mafs_planning.json` is present when MAFS discovery ran.
2. Every `mafs_search_order_id` in `discovery_candidate_pointers.json`
   appears in `mafs_planning.json`.
3. Every `mafs_axis_id` in `mafs_planning.json` has at least one
   `search_order_id`.
4. `integration_binding.json` (if augmented with `mafs_planning_pointer`)
   points at a file whose sha256 matches.

## 4. Schema versioning

`schema_version: "mafs-skill-planning.v1"` is pinned. Any breaking
change to the planning artifact schema requires a v2 + a Phase-3
deprecation note in the next maintenance advisory. Backwards-compatible
additive changes bump the schema in-place.
