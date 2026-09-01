# Frozen Source Baselines

The Skill integrates two upstream repositories at exact pinned commits.
These pins are the **single source of truth** for what "the correct
version" of CQC and MAFS is at any moment.

Canonical machine-readable copy: `release/BASELINES.json`.

## CQC (P0..P5 producer)

```text
repository: https://github.com/mo21cn/mafs-cqc
commit:    b34a12295bb4522ff027724630f244f2438c19e6
```

This is the post-CQC-UPSTREAM-FREEZE-F1 frozen baseline. P0 through
P5 are CLOSED / ACCEPTED; the producer surface is hash-frozen.

## MAFS (P0..P3 runtime)

```text
repository: https://github.com/mo21cn/mafs-v3-p0
commit:    cd09699fc8cc160ab5cfff00a41e714961dd2109
```

This is the post-MAFS-v3.0-P1.5-RA3 frozen baseline. P0 through P3
are CLOSED / ACCEPTED; the runtime surface is hash-frozen.

## Why exact pinning

- Floating `main`, `latest`, `HEAD`, or dev branches may not substitute.
- Web search, unverified source archive, or latest code may not
  substitute.
- The resolver must reach `git rev-parse HEAD == required 40-char SHA`
  for both repositories before reporting `READY` / `RUNTIME_READY`.

## What changes the pins

Pins are upgraded only by a measured failure that motivates a new
contract, never by routine. The upgrade path is:

```text
1. measured failure (real HO use, captured in writing)
2. new contract (e.g. CQC-UPSTREAM-FREEZE-F2 or MAFS-P2-RA1)
3. fresh HO+ChatGPT authorization
4. pin update in release/BASELINES.json
5. SHA-256 rebinding of release/SHA256SUMS.txt
6. portable zip rebuilt (dist/MAFS_Skill_1.0.0_Portable.zip)
```

No shortcut. No silent pin drift.
