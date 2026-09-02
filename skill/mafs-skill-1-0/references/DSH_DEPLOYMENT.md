# DSH Deployment Reference (Isolated Adapter)

> **Status.** This is a **DSH-specific deployment reference** and lives
> outside the core Skill per
> `MAINTENANCE_ADVISORY_v0.2` §4 ("Trusted Pin Manifest / Core Skill
> 边界"). DSH sandbox tier names, allowlist paths, and DSH_HOME
> environment variables are **NOT** canonical scientific authority —
> they are deployment adapter configuration.
>
> If you are deploying MAFS Skill 1.0 to a different harness (Codex,
> OpenCode, Claude Code, Aider, MiniMax Code, …), this file does not
> apply; use the harness's own skill deployment mechanism.

## 1. DSH install target

DSH Desktop exposes a global skills directory via
`standard agent preset` + `skill-filesystem` plugin:

| OS | DSH global skills path |
|---|---|
| Windows | `%APPDATA%\dsh-desktop\harness\skills\` |
| macOS | `~/Library/Application Support/dsh-desktop/harness/skills/` |
| Linux | `$XDG_CONFIG_HOME/dsh-desktop/harness/skills/` (default `~/.config/dsh-desktop/harness/skills/`) |

Override via `DSH_HOME` env var (e.g.
`DSH_HOME=/custom/path python deploy.py`).

`install.py --target dsh` resolves this path and installs the skill
under `<DSH-skills-root>/mafs-skill-1-0/`. `install.py --target
dsh-desktop` is an alias for the same path (matches the harness
process name `dsh-desktop`).

## 2. SKILL.md frontmatter

DSH's parser silently ignores skills whose `SKILL.md` YAML frontmatter
is missing the `description` field. The core Skill's `SKILL.md` MUST
carry both `name` and `description`; the v0.2 advisory
MAINTENANCE_HARDENING closes this gap by adding the field to the
source `skill/mafs-skill-1-0/SKILL.md` (no longer requires the
post-install manual patch documented in the GF/EM session).

## 3. Sandbox tier requests

DSH's confined-sandbox tier denies:

- subprocess with `capture_output=True` (WinError 5 in pipes under
  the confinement)
- network egress to anything outside the allowlist
- writes to paths outside the workspace

The skill's runtime scripts are designed to fit into the confined
sandbox wherever possible. Specifically:

- `doctor.py` and `resolve_runtime_dependencies.py` use
  `subprocess.DEVNULL` for the `git --version` probe (per
  advisory §2.4). All other `subprocess.run` calls in the skill
  preserve `capture_output=True` because they participate in
  truth judgment (commit identity, pin verification, remote
  availability) — the captured output is not optional.
- Network egress to `api.crossref.org` is required for live
  discovery. The DSH user must explicitly allow it.
- File writes are limited to the user workspace; the skill does
  not modify managed CQC / MAFS repos at runtime.

## 4. Pre-authorizing the skill (allowlist)

DSH supports a per-installation allowlist at
`~/.config/dsh-desktop/allowlist.json` (Linux/macOS) or
`%APPDATA%\dsh-desktop\config\allowlist.json` (Windows). To reduce
the number of per-task approval prompts, the user MAY add the
following entries (paths are illustrative; substitute the
actual install location):

```json
{
  "scripts": [
    {
      "path": "<dsh_skills_root>/mafs-skill-1-0/scripts/resolve_runtime_dependencies.py",
      "tier": "danger-full-access",
      "reason": "MAFS Skill 1.0 bootstrap resolver; needed for materialization"
    },
    {
      "path": "<dsh_skills_root>/mafs-skill-1-0/scripts/doctor.py",
      "tier": "danger-full-access",
      "reason": "MAFS Skill 1.0 doctor; managed runtime predicate"
    },
    {
      "path": "~/.mafs/skill-1.0/repos/mafs-cqc/scripts/validate_cqs.py",
      "tier": "danger-full-access",
      "reason": "Frozen CQC pin (b34a1229…); required by MAFS skill admission check"
    }
  ]
}
```

The installer does **not** write this file by default
(`LEGACY_SKILL_SHADOWING_DETECTED` is emitted as a warning, not a
silent deletion). The user copies the entries above into their
own allowlist when they want to reduce prompt noise.

## 5. Avoidable vs. deserved approvals

Per advisory §5, the goal is **avoidable approvals → 0**, with
deserved security / authority checkpoints preserved. The skill
does NOT optimize for "approval_total ≤ 3" as a hard gate. Expect:

- 0 approvals if allowlist is configured.
- 2-4 approvals per task if allowlist is not configured (bootstrap
  resolver + doctor + 1-2 for live discovery / resolve).
- N approvals if frozen-pin scripts that have been pre-authorized
  in the allowlist need to run (these are deserved; they exercise
  external / network / subprocess authority).

The hard rule: **do not blanket-replace `capture_output=True` with
`DEVNULL`** to game the approval count. Preserve all truth-bearing
subprocess observability (advisory §2.4).

## 6. SKILL frontmatter `description`

The current canonical description (added in maintenance hardening):

> MAFS Skill 1.0 runs the CQC (P0..P5) then MAFS (P0..P3)
> falsification-search workflow. Bootstrap gate first reads
> release/BASELINES.json, runs resolve_runtime_dependencies.py, and
> runs doctor.py; only then does it digest a research narrative
> through CQS, SRP, BudgetEnvelope, and IntegrationBinding, hands
> off to MAFS discover, STOP, explicit CandidatePointer selection,
> and resolve.

This is a **discovery-layer** field. It does NOT express
scientific authority; that lives in the artifact lineage
(`cqs.json` → `srp.json` → `budget_envelope.json` →
`integration_binding.json` → `discovery_candidate_pointers.json` →
`resolved_canonical_evidence.json`).

## 7. Legacy skill hygiene

`MAINTENANCE_ADVISORY_v0.2` §2.3 explicitly authorizes moving the
OMX-era legacy `multi_axis_falsification_search` skill out of
`~/.codex/skills/` and into `~/.codex/skills-archive/`. This is a
**Codex-level** hygiene step, not a DSH-level one, but is recorded
here because:

- Some users have both Codex and DSH installed; the legacy skill
  appears in Codex discovery but not DSH discovery.
- If the user is on a single-machine setup where the same global
  state feeds both harnesses, the archive move cleans up the
  Codex surface without breaking DSH.

Installer behavior on detecting the legacy skill in
`~/.codex/skills/`:

```text
LEGACY_SKILL_SHADOWING_DETECTED: multi_axis_falsification_search
  → presence in active Codex discovery may cause semantic shadowing
  → recommended: move to ~/.codex/skills-archive/multi_axis_falsification_search-v0.1/
  → installer does NOT auto-move; user must run manually
```

## 8. DSH version compatibility

This reference applies to DSH Desktop ≥ `0.1.1-rc.1`. Older
versions may have different allowlist paths or different sandbox
tier names; consult your DSH version's documentation.
