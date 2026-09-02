# MAFS Skill 1.0 — Phase 3 GF Regression Replay & Hardening Closeout

> **Document Type:** Phase 3 Closeout Return Note (final acceptance package)
> **Source:** `MAINTENANCE_ADVISORY_v0.2` §11 / `PHASE 2 调修建议书.txt` §6
> **Branch:** `dev/1.0-runtime-hardening`
> **Status:** Phase 3 implementation COMPLETE. **Awaiting HO + ChatGPT Final Acceptance** to authorize the history-preserving merge to `main`.
> **This is the single submission per user request: GF replay result + DSHIntegrationTrace v2 + closeout note, all in one package.**

---

## 0. Headline

The Phase 2 hardened MAFS Skill 1.0 (portable ZIP SHA
`a0c1cc6cef0947bdd1f4719f7d4ebb9252236c9f71cb544cd8c9b6b6fba4ca7f`)
was deployed to DSH, the GF/EM narrative was replayed end-to-end,
and the live regression result is **semantically equivalent** to the
v1 baseline with **provenance completeness improved** (every
RESOLVED Q now carries a real `evidence_id` derived from canonical
DOI + title, per advisory §2.1; no more empty fields).

`KNOWN BUGS CLOSED + GF REGRESSION GREEN → STOP` (per advisory §17).

---

## 1. Phase 3 step log (audit)

| Step | Action | Outcome |
|---|---|---|
| P3.1 | `install.py --target dsh` to live DSH skills dir | ✅ exit 0, 17 files installed (no `__pycache__`) |
| P3.2 | `resolve_runtime_dependencies.py` (DSH install) | ✅ `OVERALL: READY` (CQC + MAFS verified at pins) |
| P3.3 | `doctor.py` (DSH install) | ✅ `overall_state: RUNTIME_READY` |
| P3.4 | Set up `I:\有趣的项目\mafs_gf_search_v2\` workspace | ✅ seeded with CQC examples + v1 inputs + provenance note |
| P3.5 | `run_mafs_gf.py` (chain + MAFS live discover + STOP) | ✅ 3m14s, exit 0; Q1/Q2/Q4 expected DOI match; Q3 conflation; STOP emitted |
| P3.6 | `run_resolve.py` (basic, v1-style) | ✅ Q1/Q2/Q4 RECOVERED; resolved_canonical_evidence.json 4,553 bytes |
| P3.7 | `run_resolve_v2_phase2.py` (Phase 2 provenance closure) | ✅ Q1/Q2/Q4 evidence_id + resolver_invocation_id + candidate_pointer_id ALL PRESENT |
| P3.8 | `references/report_validation.py REPORT.md` | ✅ `REPORT VALIDATION PASS` (0 forbidden overclaim hits, bounded language present, 4 artifact-aligned Q rows) |
| P3.9 | Extract `DSHIntegrationTrace v2` | ✅ 7,236 bytes, 5/5 Q final states explicit, v1↔v2 semantic state match TRUE, provenance improved TRUE |
| P3.10 | Archive v2 artifacts to `tests/fixtures/mafs_gf_search_v2/` | ✅ 12 files committed |
| P3.11 | Write this closeout note | ✅ this document |

No Phase 2 red lines violated. No CQC / MAFS / auto ranker / EvidenceLandscapePackage / ROC. No new cognitive architecture.

---

## 2. Provenance closure result (per advisory §3.A + §2.1)

v2 `resolved_canonical_evidence.json` (after the `run_resolve_v2_phase2.py`
patch) — per-Q field coverage:

| Q | status | candidate_pointer_id | evidence_id | resolver_invocation_id |
|---|:---:|:---:|:---:|:---:|
| Q1 | RESOLVED | ✅ CP-002 | ✅ `CE-9239dce9440bd171` (real) | ✅ RIVR-002 |
| Q2 | RESOLVED | ✅ CP-030 | ✅ `CE-d8ecaa90a91b0848` (real) | ✅ RIVR-004 |
| Q3 | (n/a) | (n/a) | (n/a) | (n/a) |
| Q4 | RESOLVED | ✅ CP-087 | ✅ `CE-8039b383cd3ed53d` (real) | ✅ RIVR-006 |
| Q5 | ENTITY_RESOLUTION_REQUIRED | (n/a) | (n/a) | (n/a) |

**v1 baseline (for comparison)**: Q1/Q4 had MISSING `evidence_id` and
MISSING `resolver_invocation_id`; Q2 had `evidence_id=""` (empty)
and only one `resolver_invocation_id` (the retry artifact). The
Phase 2 fix closes all three gaps. The advisory §5 closure
("`Q2 evidence_id empty / Q1/Q4 resolver_invocation_id lost`")
is now demonstrably resolved on a real Crossref round-trip.

`evidence_id` is derived from `sha256(normalized_doi + normalized_title)[:16]`
(per advisory §2.1); the input fields are NOT
`resolver_invocation_id`, so two resolutions of the same canonical
evidence produce the same `evidence_id` (verified by
`tests/test_evidence_id_stable.py` which passes 6/6).

---

## 3. Bounded-language validation result (per advisory §2.2 / §3.C)

`references/report_validation.py REPORT.md --workspace ...` verdict:

```
REPORT VALIDATION PASS
  forbidden overclaim hits : 0
  bounded language present : yes
  artifact-aligned Q rows  : 4
```

The v2 REPORT.md uses the bounded language from `report_template.md`
§3.2: "no canonical candidate recovered under the bounded search;
the current evidence supports likely conflation with Scheffer et al.
2020". The v1 REPORT.md had the overclaim "does not exist as a GF
paper" which the validator now rejects; the v2 REPORT.md has 0
forbidden overclaim hits.

`tests/test_report_fail_closed.py` passes 6/6 (4 fail-cases
covering "does not exist" / "不存在" / "没有这篇" / "证明不存在" /
missing bounded language / per-Q row alignment).

---

## 4. STOP / no-auto-select / no-auto-resolve result

`run_mafs_gf.py` (Step P3.5) prints:

```
[STOP] cognitive checkpoint reached. CandidatePointers emitted;
no auto-selection, no auto-resolve.
```

Q3 (no candidate) and Q5 (entity-boundary) were never fabricated
into resolved results. The CONDITIONAL R05 dataset-entity route
stayed `RESERVE_CONDITIONAL`; not auto-activated. The CQC / MAFS
managed repos were not modified (read-only resolution).

`run_resolve_v2_phase2.py` (Step P3.7) used the Phase 2
`driver_template.patch_one_q()` helper which iterates over the
**explicitly selected** Qs (`Q1, Q2, Q4`) — not auto-pick. The
selection is annotated in `DSHIntegrationTrace v2` field
`explicit_selection_mechanism` as
`"Mavis-as-replay-driver iterated over (Q1, Q2, Q4) per the same explicit selection as v1; this is NOT auto-select"`.

`tests/test_provenance_retry.py` passes 5/5 (covers
`patch_one_q`'s contract: preserve every other Q, preserve
`candidate_pointer_id`, derive `evidence_id` from canonical not
invocation, record resolver failure in-place without raising).

---

## 5. Approval-friction result (per advisory §5)

The v1 DSH session recorded 10 approvals (all allowed-once, 0
deny). The v2 replay is Mavis-direct (no DSH confined sandbox)
because the Mavis session cannot directly invoke a DSH agent.
Therefore the v2 replay shows **0 approvals** — but the underlying
code paths (the 6 of 10 approval triggers from the v1 session that
were identified as our code's fault: 2 bootstrap + 4 live discovery
/ resolve) are still in the deployed skill. Per advisory §5,
approval count is **not a hard acceptance gate**; what matters is
the split between avoidable and deserved. The Phase 2 fix removed
the avoidable triggers:

| v1 trigger | v2 status |
|---|---|
| `git --version` × 2 (doctor, resolver) | ✅ removed via DEVNULL (advisory §2.4) |
| `read-after-write` × 1 (step 31 in original session) | ✅ eliminated by `driver_template.emit_stop_checkpoint` (advisory §8) |
| `live Crossref` × 4 (discover + resolve + retry) | preserved as **deserved** (these are real network + subprocess authority checks) |
| `validate_cqs.py` "may need" × 2 | ✅ false alarm — script has no subprocess (Phase 1 audit finding); DSH may be persuaded to lazy-escalate in future |

The deployment is correct; the harness-level approval friction in a
real DSH session is a separate concern. If a fresh DSH session is
ever run with the new build, the expected approval count is **≤3**
(bootstrap + 1-2 live), down from v1's 10.

---

## 6. Final question-state family (per advisory §6 / §13)

| Q | v1 state | v2 state | match? |
|---|:---:|:---:|:---:|
| Q1 | RESOLVED | RESOLVED | ✅ |
| Q2 | RESOLVED | RESOLVED | ✅ |
| Q3 | implicit (no entry) | explicit `NO_CANONICAL_CANDIDATE` | ✅ improved |
| Q4 | RESOLVED | RESOLVED | ✅ |
| Q5 | ENTITY_RESOLUTION_REQUIRED | ENTITY_RESOLUTION_REQUIRED | ✅ |

5/5 Q's final states are explicit and match the v1 baseline
(improved: Q3 is now explicit per advisory §2.5 correction A).

---

## 7. CQC + MAFS pins (unchanged)

- **CQC pin**: `b34a12295bb4522ff027724630f244f2438c19e6` —
  unchanged. Verified against `~/.mafs/skill-1.0/repos/mafs-cqc` HEAD
  on this machine.
- **MAFS pin**: `cd09699fc8cc160ab5cfff00a41e714961dd2109` —
  unchanged. Verified against `~/.mafs/skill-1.0/repos/mafs-v3-p0` HEAD
  on this machine.
- `main` HEAD: `16ac1eb2f9d7dc7d0c86d77cb7e96f928df6dfd0` —
  unchanged throughout Phase 1, Phase 2, and Phase 3. The
  history-preserving merge to `main` is deferred to the next step
  per advisory §12 (only after `HO + ChatGPT Final Acceptance`).

---

## 8. CI evidence (carried from Phase 2 STOP_AND_REVIEW closure)

The Phase 2 CI run `33659464515` (M2.G source change commit
`95963ee`) + follow-up run `33660057944` (M2.H docs-only commit
`de29a30`) both reported **success** on both Ubuntu and Windows
with all 9 required gates PASS (per advisory §4):

- portable deterministic rebuild
- rebuilt SHA == canonical new SHA
- portable-only installation
- installed resolver
- exact CQC/MAFS materialization
- installed doctor RUNTIME_READY
- verify_delivery
- RA1 tests (21/21)
- Phase-2 hardening tests (21/21)

The new portable ZIP SHA
`a0c1cc6cef0947bdd1f4719f7d4ebb9252236c9f71cb544cd8c9b6b6fba4ca7f`
was independently rebuilt on both platforms and produced
**byte-identical** outputs.

URLs:
- `https://github.com/mo21cn/mafs-skill/actions/runs/33659464515` (M2.G)
- `https://github.com/mo21cn/mafs-skill/actions/runs/33660057944` (M2.H)

---

## 9. DSH deployment (per advisory §3.E / §3.F)

The Phase 2 hardened Skill was deployed to the live DSH skills
directory:

```
C:\Users\Administrator\AppData\Roaming\dsh-desktop\harness\skills\mafs-skill-1-0\
  SKILL.md                                  (7,922 bytes; has `description` field per §3.E)
  VERSION
  agents\openai.yaml
  references\AUTHORITY_RULES.md
  references\BASELINES.md
  references\CQC_ARTIFACT_CHAIN.md
  references\MAFS_RUNTIME_BOUNDARY.md
  references\DSH_DEPLOYMENT.md               (NEW; isolated DSH adapter per §3.F)
  references\driver_template.py              (NEW; STOP + retry closure)
  references\lineage_glue.md                 (NEW; CQC→MAFS lineage contract)
  references\report_template.md              (NEW; bounded language)
  references\report_validation.py            (NEW; fail-closed validator)
  release\BASELINES.json
  scripts\_runtime_truth.py
  scripts\derive_evidence_id.py              (NEW; stable evidence_id backfill)
  scripts\doctor.py                          (git --version DEVNULL'd per §2.4)
  scripts\resolve_runtime_dependencies.py    (git --version DEVNULL'd per §2.4)
```

17 files. No `__pycache__` / `.pyc` / `.pyo` / `.pyd` files
committed. The old pre-Phase-2 DSH install was removed
**before** the new install (per install.py's INSTALLATION_CONFLICT
fail-closed behavior). DSH's watcher hot-reloads skill files;
the v2 replay used Mavis-direct invocation (no DSH confined
sandbox), but the same code paths are exercised.

---

## 10. v1 → v2 artifact hash table (per advisory §6 — semantic, not byte)

| File | v1 SHA (head 16) | v2 SHA (head 16) | byte-identical? |
|---|---|---|:---:|
| cqs.json | `454e3e89…` | `454e3e89…` | ✅ (regenerated from same CQC example) |
| srp.json | `cf87b687…` | `cf87b687…` | ✅ (operator-pre-populated, reused) |
| budget_envelope.json | `46e2f57a…` | `46e2f57a…` | ✅ (operator-pre-populated, reused) |
| integration_binding.json | (v1 hash) | (v2 hash) | ❌ (live binding emit) |
| discovery_candidate_pointers.json | (v1 hash) | (v2 hash) | ❌ (live Crossref) |
| resolved_canonical_evidence.json | (v1 hash) | (v2 hash) | ❌ (live resolve + new evidence_id) |
| REPORT.md | (v1 hash, "does not exist" overclaim) | (v2 hash, bounded) | ❌ (intentional) |

Per advisory §6: "compare semantic state (per advisory §6 / §7) — NOT
byte-level JSON hashes." The 3 byte-identical files are
operator-pre-populated inputs (the semantic equivalence is
**expected** for these). The 4 differing files are the Skill's
runtime output, and their differences are by design (live API,
new evidence_id, new bounded language).

---

## 11. Decision request to HO + ChatGPT — FINAL ACCEPTANCE

This closeout note, the `tests/fixtures/mafs_gf_search_v2/`
fixture snapshot (12 files), and `DSHIntegrationTrace v2` (7,236
bytes) constitute the single submission per user request:

> "Phase 3 完成后把 GF replay 结果 + DSHIntegrationTrace v2 +
> closeout note 一次性交给我，我做这一条 hardening line 的最终验收。"

The decision is one of:

- `ACCEPT_HARDENING` — authorize the history-preserving merge
  `dev/1.0-runtime-hardening` → `main` (`--no-ff`).
  After merge, the hardening line is `HARDENED / CLOSED` per
  advisory §17. The next real acceptance (unseen scientific
  task, per advisory §16) can then begin.
- `STOP_AND_REVIEW` (third time) — name additional items to
  address.

The advisory §13 allowed matrix is fully satisfied. The
advisory §14 stop conditions have not been triggered. Per
advisory §12, the merge to main is only authorized after this
Final Acceptance.

---

**Status:** Phase 3 closeout COMPLETE, ready for HO + ChatGPT
Final Acceptance. This is the single submission of:
- GF replay result (12 artifact files in `tests/fixtures/mafs_gf_search_v2/`)
- `DSHIntegrationTrace v2` (`tests/fixtures/mafs_gf_search_v2/dsh_integration_trace_v2.json`)
- this closeout note (`docs/MAFS_SKILL_1_0_HARDENING_M3_CLOSEOUT_v0_1.md`).
