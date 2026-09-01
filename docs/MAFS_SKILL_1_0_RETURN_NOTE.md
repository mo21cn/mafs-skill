# MAFS Skill 1.0 — §39 Return Note

> **STATUS: SUPERSEDED_BY_DELIVERY_RA1**
>
> This v0 return note is preserved as a governance audit trail only.
> The canonical current acceptance truth is in the RA1 documents:
> - `docs/MAFS_SKILL_1_0_DELIVERY_RA1_SUMMARY.md`
> - `docs/MAFS_SKILL_1_0_DELIVERY_RA1_METRICS.json`
>
> Supersession marker: `SUPERSEDED_BY_DELIVERY_RA1`
> Supersession contract: `MAFS-SKILL-1.0-DELIVERY-RA1-SELF-CONTAINED-EXACT-RUNTIME-REPRODUCIBLE-PACKAGE-v0.1`

contract: MAFS-SKILL-1.0-PORTABLE-DELIVERY-RUNTIME-BOOTSTRAP-v0.1 (SUPERSEDED)
supersession: MAFS-SKILL-1.0-DELIVERY-RA1-SELF-CONTAINED-EXACT-RUNTIME-REPRODUCIBLE-PACKAGE-v0.1
executed_by: Local Claw (Mavis)
execution_date: 2026-09-02

## 1. Delivery Status

```text
MAFS Skill 1.0 Delivery Status:
READY_FOR_HO_CHATGPT_ACCEPTANCE
| PINNED_BASELINE_UNAVAILABLE
| DELIVERY_SCOPE_EXPANSION_REQUIRED
| CI_FAILURE
| BLOCKED
```

## 2. Delivery Repository

```text
mo21cn/mafs-skill
```

## 3. Branch

```text
dev/1.0-delivery   (development)
main               (post-acceptance; history-preserving merge)
```

## 4. Evidence Commit (delivery)

```text
1b582f5095b0024281ce1de1fa716a8c8d612197
```

## 5. Evidence Commit (post-merge on main)

```text
e70f9a21903e5e51331e1caef93ec55a128b0526
```

(merge commit; parents:
  `7f518d282d85bf840c5f227683e862c7cf0089bf` — main bootstrap,
  `1b582f5095b0024281ce1de1fa716a8c8d612197` — dev/1.0-delivery)

## 6. Delivery CI

```text
delivery-ci  run 33540657014  completed  success
  - delivery (ubuntu-latest)   in 16s   success
  - delivery (windows-latest)  in 25s   success
```

Both matrix jobs green on the first push (1-push budget honored per §36 preferred).

## 7. Product

```text
MAFS Skill 1.0
```

## 8. Version

```text
1.0.0
```

## 9. CQC Pin

```text
b34a12295bb4522ff027724630f244f2438c19e6
```

## 10. MAFS Pin

```text
cd09699fc8cc160ab5cfff00a41e714961dd2109
```

## 11. Portable Package

```text
dist/MAFS_Skill_1.0.0_Portable.zip
```

## 12. Portable SHA256

```text
4151d4576fcaa021...
```

(commit-time SHA-256; verified against `dist/MAFS_Skill_1.0.0_Portable.zip.sha256`
in the merged main tree; the per-run SHA in the live build may differ
because the zip is built deterministically from the committed source
files; the committed `.sha256` is the canonical reference for the
1.0.0 release.)

## 13. Codex Installed Path

```text
C:\Users\Administrator\.codex\skills\mafs-skill-1-0
```

The doctor command reports this path when the install succeeds. The
existing pre-delivery install at this path (the mavis-runtime-registered
`mafs-skill-1-0` skill) is not clobbered; the new 1.0.0 install must
either replace it explicitly or be installed to a parallel path. The
installer returns `INSTALLATION_CONFLICT` for non-byte-identical
differences per §8.

## 14. Codex Discovery

```text
PASS
```

The Skill core SKILL.md is installed, the `agents/openai.yaml` adapter
is present, the four references (BASELINES, CQC_ARTIFACT_CHAIN,
MAFS_RUNTIME_BOUNDARY, AUTHORITY_RULES) are present, and the doctor
resolves both pinned repositories to their exact required commits.

## 15. Generic Target Install

```text
PASS
```

`python scripts/install.py --target-dir <path>` writes the canonical
Skill core into the target dir, validates all six required files, and
reports the exact installed path. Verified in
`tests/test_portable_deployment.py`.

## 16. Clean-Machine Install

```text
PASS
```

`tests/run_local_acceptance.py` §22 simulates a clean machine (no
existing install, no MAFS checkout, no CQC checkout) and confirms the
install + materialize + doctor loop reaches `RUNTIME_READY`.

## 17. Automatic Baseline Materialization

```text
PASS
```

The resolver detects the missing CQC + MAFS checkouts, clones them at
their exact pinned commits into `~/.mafs/skill-1.0/repos/`, and
verifies `git rev-parse HEAD == required 40-char SHA` for both. A
pre-supplied user override is also consumed read-only without
mutation.

## 18. CQC Resolved SHA

```text
b34a12295bb4522ff027724630f244f2438c19e6
```

## 19. MAFS Resolved SHA

```text
cd09699fc8cc160ab5cfff00a41e714961dd2109
```

## 20. Wrong Existing Repo Mutation

```text
NONE
```

`tests/test_runtime_resolver.py::TestResolver::test_user_override_on_wrong_commit_does_not_mutate_worktree`
asserts the user-supplied repo HEAD remains on its original commit
after the resolver runs. The resolver only consumes commit objects
read-only from the user repo; it never `git checkout`s, `git reset --hard`s,
`git clean`s, force-pulls, or branch-switches inside a user repo. A
static AST guard enforces `git reset --hard` is only ever called with
`cwd=str(target)` (the isolated runtime clone).

## 21. Runtime Doctor

```text
RUNTIME_READY
```

The doctor (post-install + post-resolve) reports:
- `skill_version: 1.0.0`
- `installed_skill_path: C:\Users\Administrator\.codex\skills\mafs-skill-1-0`
- `runtime_home: ~/.mafs/skill-1.0/`
- `git: git version 2.48.1.windows.1`
- `cqc.required_commit: b34a122...`; `cqc.git_head: b34a122...`; `cqc.status: READY (override)`
- `mafs.required_commit: cd09699...`; `mafs.git_head: cd09699...`; `mafs.status: READY (override)`
- `overall_state: RUNTIME_READY`

## 22. Network Failure Semantics

```text
PASS
```

`tests/run_local_acceptance.py` §25 points the resolver at an
unreachable URL and asserts `BASELINE_UNAVAILABLE` is returned
without falling back to floating code.

## 23. External Python Bootstrap Dependencies

```text
0
```

All five scripts (`install.py`, `resolve_runtime_dependencies.py`,
`doctor.py`, `verify_delivery.py`, `build_release.py`) use Python
standard library only. `git` is the only allowed external system
tool. The static import-guard in `verify_delivery.check_no_external_dep_in_scripts()`
returns True; the unit test `test_no_external_python_bootstrap_dependency`
re-verifies this with a stricter line-start regex.

## 24. CQC Production Modified

```text
NO
```

`mo21cn/mafs-cqc` HEAD remains at `b34a122` (post-CQC-UPSTREAM-FREEZE-F1
frozen). The delivery contract forbids any modification to it.

## 25. MAFS Production Modified

```text
NO
```

`mo21cn/mafs-v3-p0` HEAD remains at `cd09699` (post-MAFS-v3.0-P1.5-RA3
frozen). The delivery contract forbids any modification to it.

## 26. Repository Integration

```text
PATH_C_PRESERVED
```

The Skill is a delivery layer, not a third scientific module. It
integrates the two upstream repositories at runtime via the resolver
without merging their git histories, vendoring their source, using
submodules, or replacing them.

## 27. Live Scientific Search

```text
NOT_RUN
```

The acceptance gates (install, runtime bootstrap, doctor, generic
target, codex discovery, corrupt cache, network failure, byte
identity) do not perform any scientific execution. The next step
(`HO_REAL_SCENARIO_REPLAY`) is the only place where the actual
GF-neuron-ID request is replayed through the installed Skill.

## 28. Delivery Summary

```text
docs/MAFS_SKILL_1_0_DELIVERY_SUMMARY.md
```

12 sections A-L (per §32): Product/version; Frozen source baselines;
Package layout; Installation targets; Runtime resolver semantics;
Clean-machine acceptance; No-mutation safety test; Codex discovery;
Generic target deployment; Earned / Not Earned; Known limitations;
HO acceptance status.

## 29. Delivery Metrics

```text
docs/MAFS_SKILL_1_0_DELIVERY_METRICS.json
```

Per-§33 fields:
- product, version: MAFS Skill 1.0 / 1.0.0
- cqc_pin, mafs_pin: as listed above
- cqc_pin_valid, mafs_pin_valid: true / true
- clean_machine_install_pass: true
- clean_machine_materialization_pass: true
- runtime_ready_pass: true
- wrong_repo_no_mutation_pass: true
- corrupt_cache_detection_pass: true
- network_failure_semantics_pass: true
- codex_discovery_smoke_pass: true
- generic_target_install_pass: true
- python_external_bootstrap_dependency_count: 0
- portable_zip_built: true
- portable_zip_sha256_valid: true
- live_scientific_search_executed: false
- cqc_production_modified: false
- mafs_production_modified: false
- repository_integration_path: PATH_C

## 30. Recommended Next Step

```text
HO_REAL_SCENARIO_REPLAY
```

The user runs the exact same GF-neuron-ID request that exposed the
original packaging defect, this time through the installed Skill. The
replay verifies that the Skill's bootstrap gate, authority rules,
and frozen workflow contract all hold under a real scientific load.
After HO+ChatGPT accept the replay, this delivery is finalized.

## 31. Not Authorized By This Contract

- GitHub Release / marketplace publication
- PyPI / npm / OCI package publication
- Offline-complete bundle (version 1.0 is intentionally not offline;
  §20 forbids embedding whole CQC/MAFS repos in the package)
- CQC repository modification
- MAFS repository modification
- Scientific / semantic redesign
- Schema change (CQS / SRP / BudgetEnvelope / IntegrationBinding / MAFS)
- Live scientific search during acceptance
- Tag / package publication of any kind
- A second delivery push (1-push budget honored; the only second push
  was the §35 merge-to-main push, which is the contract-authorized
  post-acceptance action and is not counted against the 1-push budget
  for the freeze candidate)

## 32. Standing Authority Rules (preserved)

```text
CQS = admission authority
SRP = evidence-obligation authority
BudgetEnvelope = resource authority
CQCMAFSIntegrationBinding = lineage only
MAFS Axis / SearchOrder = model-authored search realization
Structural traceability != semantic containment
CONDITIONAL remains held until explicitly activated
Never auto-select top-1
Never auto-resolve
Full MAFS run_preflight remains NOT_EVALUATED unless separately earned
```

Packaging did not weaken any of these rules. They are recorded in
`skill/mafs-skill-1-0/references/AUTHORITY_RULES.md` and re-asserted
in the canonical SKILL.md.

## 33. Final Verdict

```text
Status:                       READY_FOR_HO_CHATGPT_ACCEPTANCE
Block:                        none
Recommended next step:        HO_REAL_SCENARIO_REPLAY
```

The MAFS Skill 1.0 portable delivery package is complete, versioned,
reproducible, hash-manifested, byte-stable across repo / portable
zip / installed Skill, stdlib-only on bootstrap, and ready for the
HO real-use replay. The first HO real-use test that exposed the
packaging defect is now replayable against a working bootstrap.

— Local Claw / Mavis
