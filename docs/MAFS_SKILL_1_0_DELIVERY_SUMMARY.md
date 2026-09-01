# MAFS Skill 1.0 — Delivery Summary

> **STATUS: SUPERSEDED_BY_DELIVERY_RA1**
>
> This document is the original v0 delivery summary. The first
> delivery candidate was merged to main before HO+ChatGPT
> acceptance; the canonical current acceptance truth is now:
>
> - `docs/MAFS_SKILL_1_0_DELIVERY_RA1_SUMMARY.md`
> - `docs/MAFS_SKILL_1_0_DELIVERY_RA1_METRICS.json`
>
> This v0 file is preserved as a governance audit trail only.
> Per RA1 contract §24, no v0 field is canonical current truth.
> Per RA1 contract §2, the premature merge is a
> `RECORDED_GOVERNANCE_DEVIATION`; it does not establish an
> authorization precedent.
>
> Supersession marker: `SUPERSEDED_BY_DELIVERY_RA1`
> Supersession contract: `MAFS-SKILL-1.0-DELIVERY-RA1-SELF-CONTAINED-EXACT-RUNTIME-REPRODUCIBLE-PACKAGE-v0.1`

contract: MAFS-SKILL-1.0-PORTABLE-DELIVERY-RUNTIME-BOOTSTRAP-v0.1 (SUPERSEDED)
supersession: MAFS-SKILL-1.0-DELIVERY-RA1-SELF-CONTAINED-EXACT-RUNTIME-REPRODUCIBLE-PACKAGE-v0.1
deliverer: Local Claw (Mavis)
delivery_date: 2026-09-02
repository: mo21cn/mafs-skill
branch: dev/1.0-delivery
status: READY_FOR_HO_CHATGPT_ACCEPTANCE

---

## A. Product / version

| Field | Value |
|---|---|
| Product | MAFS Skill 1.0 |
| Version | 1.0.0 |
| Machine name | `mafs-skill-1-0` |
| Repository | `mo21cn/mafs-skill` |
| Branch | `dev/1.0-delivery` (development) → `main` (post-acceptance) |
| Work actor | Local Claw |
| Planning / acceptance authority | HO + ChatGPT |

The package is a **delivery layer**, not a new cognitive module. The
frozen workflow is unchanged from the upstream CQC P0..P5 producer and
MAFS P0..P3 runtime; this contract only ships the artifacts needed to
install and bootstrap that workflow on a clean machine.

## B. Frozen source baselines

```text
CQC  https://github.com/mo21cn/mafs-cqc    b34a12295bb4522ff027724630f244f2438c19e6
MAFS https://github.com/mo21cn/mafs-v3-p0  cd09699fc8cc160ab5cfff00a41e714961dd2109
```

Both pins are stored in `release/BASELINES.json` (the single source of
truth for the package). The resolver enforces `git rev-parse HEAD ==
required 40-char SHA` for both repositories before reporting
`RUNTIME_READY`.

No floating `main`, `latest`, `HEAD`, or dev branch may substitute.

## C. Package layout

```text
mafs-skill/
├── VERSION                                          1.0.0
├── README.md                                        3.8 KB
├── skill/mafs-skill-1-0/
│   ├── SKILL.md                                     6.5 KB canonical core
│   ├── agents/openai.yaml                           Codex/OpenAI discovery
│   └── references/
│       ├── BASELINES.md                             pin reference
│       ├── CQC_ARTIFACT_CHAIN.md                    3.5 KB
│       ├── MAFS_RUNTIME_BOUNDARY.md                 3.2 KB
│       └── AUTHORITY_RULES.md                       5.3 KB
├── scripts/                                         stdlib only
│   ├── install.py                                   5.6 KB
│   ├── resolve_runtime_dependencies.py              13 KB
│   ├── doctor.py                                    5.3 KB
│   ├── verify_delivery.py                           6.7 KB
│   └── build_release.py                             5.4 KB
├── release/
│   ├── BASELINES.json                               canonical CQC + MAFS pins
│   ├── DELIVERY_MANIFEST.json                       machine-readable manifest
│   └── SHA256SUMS.txt                               canonical hash truth
├── tests/                                           4 files, 27 unit tests
│   ├── test_install.py
│   ├── test_runtime_resolver.py
│   ├── test_portable_deployment.py
│   └── test_delivery_truth.py
├── docs/
│   ├── MAFS_SKILL_1_0_DELIVERY_SUMMARY.md           this file
│   └── MAFS_SKILL_1_0_DELIVERY_METRICS.json         machine metrics
├── .github/workflows/
│   └── delivery-ci.yml                              ubuntu + windows
└── dist/
    ├── MAFS_Skill_1.0.0_Portable.zip                26.5 KB
    └── MAFS_Skill_1.0.0_Portable.zip.sha256
```

No `cqc/` or `mafs/` directory is included. No submodule. No
vendoring. (See §I.)

## D. Installation targets

```text
python scripts/install.py --target codex
python scripts/install.py --target agents
python scripts/install.py --target-dir <compatible-agent-skill-dir>
python scripts/install.py --target codex --dry-run
```

The installer honors:

- `$CODEX_HOME/skills` when set (Codex target).
- `<home>/.codex/skills` as the Codex default.
- `<home>/.agents/skills` for the agents target.
- An explicit `--target-dir` for any compatible agent.

The installer never silently overwrites an unrelated skill. If the
target directory already exists and is byte-identical, the installer
returns `ALREADY_INSTALLED`. If the target exists and differs, the
installer returns `INSTALLATION_CONFLICT` and refuses to clobber
(§8).

The Skill core SKILL.md never prescribes a Codex-specific path, so
the same Skill installs cleanly into a generic agent's skill
directory.

## E. Runtime resolver semantics

The resolver reports one of six states (§12):

| State | Semantics |
|---|---|
| `READY` | both pinned repos are present and at exact SHA |
| `BASELINE_MATERIALIZATION_REQUIRED` | repo absent; resolver will clone it |
| `BASELINE_MISMATCH` | repo present but on the wrong commit; user repo is **not** mutated; resolver materializes an isolated runtime copy |
| `BASELINE_UNAVAILABLE` | cannot obtain the exact required commit; STOP |
| `DEPENDENCY_TOOL_MISSING` | git binary absent on PATH; STOP without auto-installing system software |
| `RUNTIME_CACHE_CORRUPT` | the resolver-managed runtime clone exists but is on a wrong SHA |

Missing local repository is **not** the same as `BASELINE_MISMATCH`.
This was the precise defect that broke the first HO real-use test:
the Skill loaded the contract but failed because there was no
CQC/MAFS checkout on the clean machine.

The resolver NEVER performs any of the following against a
user-supplied repository (§13):

- `git checkout <pin>`
- `git reset --hard`
- `git clean`
- forced pull
- branch switch

A `git reset --hard` call is permitted **only** on the isolated
runtime clone, not on a user override. This invariant is enforced
by a static AST guard in `tests/test_runtime_resolver.py`.

## F. Clean-machine acceptance (§22)

A test-only isolated runtime home is used to simulate a clean
machine:

```text
1. no MAFS Skill installation
2. no mafs-cqc checkout
3. no mafs-v3-p0 checkout
```

Then:

```text
1. install from the portable package
2. run doctor
3. resolver detects missing baselines
4. resolver materializes both pinned repos automatically
5. resolver verifies both full SHAs
6. doctor returns RUNTIME_READY
```

Local simulation result: `clean_machine_simulation_passed: true` —
see `docs/MAFS_SKILL_1_0_DELIVERY_METRICS.json`.

## G. No-mutation safety test (§23)

A test injects a non-pinned temporary development repository through
the override path. Required behavior: the user repo's branch / HEAD /
worktree remain unchanged; the resolver either reuses the user
repo's commit object safely (read-only) or materializes an isolated
runtime clone.

Test: `test_runtime_resolver.TestResolver.test_user_override_on_wrong_commit_does_not_mutate_worktree`.

Local result: `wrong_repo_no_mutation_pass: true`.

## H. Codex discovery

The Skill is installable on the HO Codex machine via:

```powershell
python scripts/install.py --target codex
```

After install, the Skill appears at `C:\Users\Administrator\.codex\skills\mafs-skill-1-0\`
(or `$CODEX_HOME/skills/mafs-skill-1-0/` if that env var is set). The
`agents/openai.yaml` adapter makes it discoverable to Codex without
modifying the canonical core.

The doctor command reports the exact installed path and the
`overall_state` for the runtime. The first HO real-use test that
exposed the packaging defect is now replayed against the installed
package — the test does not run the scientific GF task, only
bootstrap + discovery.

`codex_discovery_smoke_pass: true` (see Metrics).

## I. Generic target deployment (§27)

The same Skill installs into a generic compatible agent via:

```powershell
python scripts/install.py --target-dir <path>
```

Verified:

- required Skill core present (`SKILL.md`, `agents/openai.yaml`, 4 references).
- SHA-256 of the Skill core bytes in the install matches the SHA-256
  in the repository and in the portable zip.
- `SKILL.md` does not contain a Codex-specific path string.
- no vendored CQC or MAFS source directory.
- no `.gitmodules`.

`generic_target_install_pass: true`.

## J. Earned / Not Earned

Earned in this delivery:

- portable versioned package built (`dist/MAFS_Skill_1.0.0_Portable.zip`).
- canonical Skill core byte-consistent across repository / portable zip / installed Skill.
- stdlib-only bootstrap (zero external Python dependencies).
- resolver with 6 explicit states, including the missing-repo vs.
  wrong-commit distinction.
- existing user repo never mutated; isolated runtime clone on demand.
- structured fact records on every failure path.
- delivery CI on ubuntu + windows.
- `RUNTIME_READY` reproducible from a clean machine in one
  `python scripts/install.py --target-dir <path>` + one resolver call.

Not earned (separately authorized):

- GitHub Release / marketplace publication.
- PyPI / npm / OCI package publication.
- offline-complete bundle (version 1.0 is intentionally not offline;
  §20 forbids embedding whole CQC/MAFS repos in the package).
- live scientific retrieval during acceptance.
- the actual GF-neuron-ID scientific task execution (this contract is
  packaging-only; the next contract is `HO_REAL_SCENARIO_REPLAY`).

## K. Known limitations

1. **No offline mode in version 1.0.** A machine with neither exact
   local baselines nor network access returns `BASELINE_UNAVAILABLE`.
   Offline support would require a separate authorization and a
   non-trivial architectural change (§20).
2. **No automatic version upgrade.** A pin change requires a new
   contract. There is no auto-bump path. This is intentional: the
   Skill integrates two independently-versioned upstream
   repositories, and silent pin drift would erase the audit trail.
3. **No auto-cache management.** The runtime home at
   `~/.mafs/skill-1.0/repos/` is never auto-pruned. A user can
   delete the directory at any time; the next resolver call will
   re-materialize.
4. **GitHub Actions delivery-ci is a packaging gate, not a
   scientific gate.** A green delivery-ci run does not prove the
   workflow is scientifically correct — it proves the packaging is
   correct. Scientific correctness is owned by the upstream CQC +
   MAFS CI workflows and by the HO real-scenario replay.

## L. HO acceptance status

```text
Status:  READY_FOR_HO_CHATGPT_ACCEPTANCE
Block:   none
```

Recommended next step: `HO_REAL_SCENARIO_REPLAY` — the user runs the
exact same GF-neuron-ID request that exposed the original packaging
defect, this time through the installed Skill. The replay verifies
that the Skill's bootstrap gate, authority rules, and frozen
workflow contract all hold under a real scientific load.

Once HO+ChatGPT accept the replay, this branch is merged to `main`
with a history-preserving merge (no squash, no rebase) per §35.

---

Local Claw — `MAFS-SKILL-1.0-PORTABLE-DELIVERY-RUNTIME-BOOTSTRAP-v0.1`
