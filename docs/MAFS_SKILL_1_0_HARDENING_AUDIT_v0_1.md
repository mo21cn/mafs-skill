# MAFS Skill 1.0 — Delivery / Runtime Hardening Audit (Phase 1)

> **Document Type:** Diagnostic / Audit (read-only)
> **Phase:** Phase 1 of 3 (Audit → Fix → Closeout)
> **Author:** Local Claw (Mavis)
> **Review Authority:** HO + ChatGPT
> **Status:** PROPOSED · 待 HO 验收后进 Phase 2
> **Reference:** `MAFS_Skill_1_0_Local_Claw_Runtime_Delivery_Hardening_Advisory.md`（见书，下文以"见书 §N"指代）
> **Scope:** delivery / harness integration / runtime provenance / test methodology only — 不重开 CQC/MAFS architecture

---

## 0. 范围与红线

### 0.1 本审计范围

只做 6 件事，全部 read-only：

1. **P1.1**：定位 evidence provenance bug（见书 §5）
2. **P1.2**：定位 Q3 "does not exist" 措辞升级来源（见书 §6）
3. **P1.3**：Codex legacy skill 影子检查（见书 §10）
4. **P1.4**：subprocess `capture_output=True` 模式审计（见书 §4.3）
5. **P1.5**：DSHIntegrationTrace 提取（见书 §11）
6. **P1.6**：SHA baseline 锁定

### 0.2 红线（见书 §3 + §15）

- ❌ 不改 mafs-cqc frozen pin `b34a1229`
- ❌ 不改 mafs-v3-p0 frozen pin `cd09699f`
- ❌ 不改 CQC/MAFS 业务语义
- ❌ 不加 auto ranker / auto candidate selection / auto resolve
- ❌ 不加 EvidenceLandscapePackage / ROC

Phase 1 全程 read-only，**不动任何代码**。

---

## 1. Baseline SHA 锁定（P1.6）

| 项 | Target | Actual | Match |
|---|---|---|:---:|
| CQC pin | `b34a12295bb4522ff027724630f244f2438c19e6` | `b34a12295bb4522ff027724630f244f2438c19e6` | ✅ |
| MAFS pin | `cd09699fc8cc160ab5cfff00a41e714961dd2109` | `cd09699fc8cc160ab5cfff00a41e714961dd2109` | ✅ |
| I: drive portable ZIP | `e6292b251f4bb187ff40e4b36e4cbf9d49f09b3ab30c56d1972fe8199dd18b71` | `E6292B251F4BB187FF40E4B36E4CBF9D49F09B3AB30C56D1972FE8199DD18B71` | ✅ |
| main HEAD (`mo21cn/mafs-skill`) | `16ac1eb2f9d7dc7d0c86d77cb7e96f928df6dfd0` | `16ac1eb2f9d7dc7d0c86d77cb7e96f928df6dfd0` | ✅ |
| Working tree | clean (only untracked scratch + 1 intended `docs/` return note) | clean | ✅ |

**结论**：所有 baseline 完整、未漂移。Phase 2 必须在不破坏这些 SHA 的前提下做修复。

---

## 2. Evidence Provenance Bug（P1.1，见书 §5）

### 2.1 现象（与见书 §5.1 一致）

`I:\有趣的项目\mafs_gf_search\resolved_canonical_evidence.json` 字段覆盖：

| Q | `evidence_id` | `resolver_invocation_id` | `candidate_pointer_id` | 其它 7 字段 |
|---|:---:|:---:|:---:|:---:|
| Q1 | **❌ 缺字段** | **❌ 缺字段** | ✅ `CP-002` | ✅ |
| Q2 | ✅ `""`（空串） | ✅ `RIVR-002` | ✅ `CP-030` | ✅ |
| Q4 | **❌ 缺字段** | **❌ 缺字段** | ✅ `CP-089` | ✅ |

DSH session step 35（ASK #10）显示："Retrying the production resolver for the Q2 Namiki 2018 DOI with canonical casing, which was the single failed resolve."——retry 发生在 Q2 一个，其余 Q1/Q4 是初版 run_resolve.py 正常 resolve 的。

### 2.2 根因（**双层**）

**层 1：driver（`run_resolve.py`）的 retry / 合并逻辑手工重建 JSON**

`run_resolve.py:60-71`（RESOLVED 分支）的赋值语句确实会写 10 个字段（包含 `evidence_id` + `resolver_invocation_id`）。但 **实际 JSON 缺失这两个字段**——证明 retry 路径**手工构造了一份新的 JSON**，把 Q1/Q4 的 `evidence_id` / `resolver_invocation_id` 字段漏了。

证据：
- Q1/Q4 完全没有 `evidence_id` / `resolver_invocation_id` 字段（不是 `""`）
- Q2 是 retry 后手工写的（保留 `resolver_invocation_id="RIVR-002"`，但 `evidence_id=""` 因为 retry 路径没拿到 MAFS 的 evidence_id）
- 这与见书 §5.1 "Q2 evidence_id empty / Q1/Q4 resolver_invocation_id lost" 完全一致

**层 2：MAFS frozen pin 的 `evidence_id` 设计缺陷（不可改）**

`C:\Users\Administrator\.mafs\skill-1.0\repos\mafs-v3-p0\src\mafs_p0\live_crossref.py:519`：

```python
"evidence_id": "",  # backfilled by caller (resolve())
```

`resolve()` 方法本身**没有 backfill**（line 80+ 看完没看到 backfill 逻辑）。所以 MAFS 返回的 `evidence` 对象中 `evidence_id` 永远是空串。

对比同方法 `live_crossref.py:434`：
```python
evidence["provenance"]["resolver_invocation_id"] = rivr_id
```
`resolver_invocation_id` 是有设的（写在 provenance 子字典里），所以 Q2 能拿到 RIVR-002。

### 2.3 Phase 2 修法（**不破 §15 红线**）

| 层 | 修法 | 在哪改 |
|---|---|---|
| 层 1（driver retry） | `run_resolve.py` 加一个 retry helper：读原 JSON → 仅 patch 单个 Q 的字段 → 写回。禁止 overwrite 整个文件 | 新增 `references/driver_template.py` + `run_resolve.py` 用模板 |
| 层 2（MAFS evidence_id 空） | **不直接改 MAFS pin**（红线）。在 skill 层 wrap：driver 拿到 MAFS 返回的空 `evidence_id` 后，**自己生成** stable UUID（基于 `doi + resolver_invocation_id + sha256(canonical_title)`） | `run_resolve.py` 或 driver template |

具体代码模板（Phase 2 实施）：

```python
import hashlib
def derive_evidence_id(doi: str, rivr_id: str, title: str) -> str:
    """Stable evidence_id derived from the resolver's return (no fabrication risk
    because the inputs are the resolver's own outputs)."""
    h = hashlib.sha256(f"{doi}|{rivr_id}|{title}".encode("utf-8")).hexdigest()
    return f"CE-{h[:16]}"
```

加 **regression test**（见书 §5.2 末段要求）：构造 1 个 retry scenario，验证 retry 后 Q1/Q4 的 `evidence_id` 和 `resolver_invocation_id` 仍存在且与 retry 前 byte-identical。

### 2.4 是否触及红线？

- ❌ 不改 MAFS pin
- ✅ 改 driver（skill 层，user-authored）
- ✅ 加 test（skill 仓内）
- ✅ "no auto-select / no auto-resolve" 不变（retry 是同一选择的再次执行，不是新选择）

**通过红线审查**。

---

## 3. Q3 Wording 升级来源（P1.2，见书 §6）

### 3.1 现象

`I:\有趣的项目\mafs_gf_search\REPORT.md:41`：

```
- **«von Reyn 2020» does not exist** as a GF paper. It is a conflation with **Scheffer et al. 2020** (hemibrain connectome, `10.7554/eLife.57443`).
```

### 3.2 根因定位

| 来源 | 措辞 | 评估 |
|---|---|---|
| `run_mafs_gf.py` driver | 没说任何 "does not exist" / "不存在"。Q5 只 emit `ENTITY_RESOLUTION_REQUIRED`，Q3 没有 candidate → 列表里就没 Q3 | ✅ 谨慎 |
| `run_resolve.py` driver | Q3 没出现（没 candidate → `NO_CANDIDATE` 但不写进 evidence_out） | ✅ 谨慎 |
| `discovery_candidate_pointers.json` (artifact) | Q3 的 ladder_rungs 全空，`status` 字段缺，无 "does not exist" | ✅ 谨慎 |
| `REPORT.md`（**手写**） | L41 写 "does not exist" | ❌ **升级** |

REPORT.md 不是 driver 自动生成的——是 DSH agent **在跑完所有 pipeline 后手工综合**写的（per session 末段 todo write + write calls）。

### 3.3 Phase 2 修法

1. **新增 `references/report_template.md`**：给 agent 一个 REPORT.md 模板，**Q3 negative branch 段** 强制使用见书 §6.2 推荐的措辞：
   > "No canonical von Reyn 2020 GF paper was recovered under the bounded search; the current evidence supports likely conflation with Scheffer et al. 2020."
2. **REPORT renderer 模板里加 invariant check**：
   ```python
   def check_no_nonexistence_claim(text: str) -> list[str]:
       """Return list of phrases that overclaim bounded negative evidence."""
       forbidden = ["does not exist", "doesn't exist", "不存在", "没有这篇"]
       return [p for p in forbidden if p.lower() in text.lower()]
   ```
   模板调用此函数，命中则在 REPORT 顶部加 ⚠️ warning。
3. **`DSH_DEPLOYMENT.md` 加 prompt hint**：告诉 agent 写 REPORT 时用模板、不要升级 negative 措辞。

### 3.4 是否触及红线？

- ❌ 不改 CQC/MAFS
- ✅ 加 template + renderer hint
- ✅ 仍然 "no auto-select / no auto-resolve" 不变

**通过红线审查**。

---

## 4. Codex Legacy Skill 影子（P1.3，见书 §10）

### 4.1 现象

`C:\Users\Administrator\.codex\skills\` 目录**同时**存在：

| 目录 | 大小 | SKILL.md frontmatter 关键字段 |
|---|---|---|
| `mafs-skill-1-0` | (skill 1.0) | `name: mafs-skill-1-0`（新，RA1 closed） |
| `multi_axis_falsification_search` | 18233 bytes | `name: multi-axis-falsification-search` / `Short Name: MAFS` / `Version: 0.1`（旧 OMX era） |

**潜在风险**：
- Codex agent 看到 `MAFS` short name → 调旧 skill → 完全无 CQS/SRP/BudgetEnvelope/runtime bootstrap 链
- 新旧 skill 名字不同（`mafs-skill-1-0` vs `multi-axis-falsification-search`），但都标 "MAFS"

### 4.2 评估

- 不是直接 name collision（不同 name）
- 是 **semantic shadowing**：旧 skill 用了 "MAFS" 这个 short name 误导
- 见书 §10 判定为 "deployment hygiene" 问题，不属 CQC/MAFS architecture

### 4.3 Phase 2 修法

1. **不动旧 skill 文件**（HO/ChatGPT 未授权删 skill）
2. **DEPLOYMENT.md 加 §5.6 "Legacy Skill Hygiene"**：
   - 给出 `Get-ChildItem ~/.codex/skills | Sort-Object` 的输出预期
   - 明确：**只调 `mafs-skill-1-0`**，**不调 `multi-axis-falsification-search`**
   - 给出 deprecation 指引（user 自行决定是否删）
3. **DSH 端不直接暴露 legacy skill**：DSH 自带 skill 列表里**只**列 `mafs-skill-1-0`

### 4.4 是否触及红线？

- ❌ 不删旧 skill（HO 决策）
- ✅ 文档指引
- ✅ 不改 CQC/MAFS

**通过红线审查**。

---

## 5. subprocess Capture 模式审计（P1.4，见书 §4.3）

### 5.1 完整清单（deployed skill `scripts/`）

| # | 文件:L | 调用 | output 用途 | 分类 | Phase 2 改不改 |
|---:|---|---|---|:---:|:---:|
| 1 | `doctor.py:59` | `git --version` | version probe（不参与 truth judgment） | **可改 DEVNULL** | ✅ |
| 2 | `resolve_runtime_dependencies.py:56` | `git --version` | version probe | **可改 DEVNULL** | ✅ |
| 3 | `resolve_runtime_dependencies.py:83` | `git ls-remote <url>` | 检查 remote 是否可达 | 参与 truth | ❌ 保留 |
| 4 | `resolve_runtime_dependencies.py:92` | `git ls-remote --heads <repo>` | pin commit SHA 列表 | 参与 truth（pin verify） | ❌ 保留 |
| 5 | `resolve_runtime_dependencies.py:116` | `git ls-remote <override>` | override 仓库可达性 | 参与 truth | ❌ 保留 |
| 6 | `resolve_runtime_dependencies.py:176` | `git status --porcelain` | committed state check | 参与 truth | ❌ 保留 |
| 7 | `resolve_runtime_dependencies.py:181` | `git ls-files` | tracked files 列表 | 参与 truth（hygiene） | ❌ 保留 |
| 8 | `resolve_runtime_dependencies.py:186` | `git log` | commit log | 参与 truth（diagnosis） | ❌ 保留 |
| 9 | `resolve_runtime_dependencies.py:191` | `git rev-parse HEAD` | 当前 commit SHA | 参与 truth（pin verify） | ❌ 保留 |
| 10 | `_runtime_truth.py:43` | `git ls-remote` | remote 验证 | 参与 truth | ❌ 保留 |
| 11 | `_runtime_truth.py:59` | `git log` | commit log | 参与 truth | ❌ 保留 |
| 12 | `_runtime_truth.py:65` | `git status` | 状态检查 | 参与 truth | ❌ 保留 |

### 5.2 CQC `validate_cqs.py` 检查

```
$ grep 'subprocess\.(run|Popen|check_output|check_call)' C:\Users\Administrator\.mafs\skill-1.0\repos\mafs-cqc\scripts\validate_cqs.py
(无匹配)
```

**`validate_cqs.py` 本身无 subprocess 调用**。DSH session ASK #3 #4 标的 "validate_cqs.py validates the CQS against its schema... may need non-confined mode for subprocess check" 是 **§9 "may need" 过度保守**——脚本本身不需要 subprocess，可能是它 import 的某个模块或只是 DSH 启发式误报。

### 5.3 Phase 2 修法

1. **改 #1 #2 → DEVNULL 模式**：
   ```python
   # BEFORE
   r = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=10)
   v = (r.stdout or "").strip()
   # AFTER
   r = subprocess.run(["git", "--version"], stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL, timeout=10)
   present = (r.returncode == 0)
   ```
2. **不 blanket 改**：其余 10 个调用**保留** `capture_output=True`，因为参与 commit identity / pin verification / runtime diagnosis
3. **加注释**说明每个 capture_output 的判断依据（commit identity? pin verify? diagnosis?）

### 5.4 预期效果

| 阶段 | approvals 来自 capture_output 的数量 |
|---|---:|
| 当前 DSH session | 5-6 of 10 |
| Phase 2 改后 | 4-5 of 10（#1 #2 消除） |

> 注：见书 §12 明确：approval 数不是验收门。**避免的 approvals 降到 0，deserved security/authority checkpoints 保留** 才是标准。我们只消除明显可消除的 2 个，**不为了数字**。

### 5.5 是否触及红线？

- ❌ 不改 CQC/MAFS
- ✅ 改 skill 自己的 scripts
- ✅ 保留所有 truth-judgment 相关的 output

**通过红线审查**。

---

## 6. DSHIntegrationTrace 提取（P1.5，见书 §11）

### 6.1 提取结果

`I:\有趣的项目\mafs_gf_search\dsh_integration_trace.json`（4,758 bytes）：

```json
{
  "schema_version": "dsh-integration-trace.v1",
  "task_id": "mafs-gf-em-2026-09-02",
  "step_count": 40,
  "approval_total": 10,
  "approval_allow_once": 10,
  "approval_deny": 0,
  "approval_category_counts": {
    "bootstrap_resolver": 1,   // ASK #1
    "doctor": 1,              // ASK #2
    "cqc_validate": 1,        // ASK #3
    "stop_readback": 2,       // ASK #4 #8
    "network_probe": 1,       // ASK #5
    "live_discovery": 3,      // ASK #6 #7
    "live_resolve": 1,        // ASK #9
    "retry": 1                // ASK #10
  },
  "stop_checkpoint_observed": true,
  "final_question_states": {
    "Q1": "RESOLVED",
    "Q2": "RESOLVED",
    "Q4": "RESOLVED",
    "Q5": "ENTITY_RESOLUTION_REQUIRED"
  },
  "artifact_hashes": {
    "cqs.json": {...},
    "srp.json": {...},
    ...
  }
}
```

### 6.2 关键设计

- **不存 2.3 MB 完整 session**（见书 §11 要求）
- 用 `task_id` 锚定 + `artifact_hashes` 锁定 7 个产物 SHA
- `approval_category_counts` 用语义分类而非逐条 ID
- `stop_checkpoint_observed: true` 是 boolean，不存原始 ask_user_question call 内容

### 6.3 Phase 2 用途

1. **Regression fixture**：`tests/test_gf_replay.py` 读 DSHIntegrationTrace，验证：
   - `approval_category_counts["cqc_validate"]` 持续为 1（DSH §9 lazy escalate 后应降为 0）
   - `final_question_states` 5 个 Q 与 baseline 语义一致
   - `artifact_hashes` 集合不变（产物的 identity 不漂移）
2. **不**作为单元测试主 truth source（per 见书 §11 末段）

### 6.4 是否触及红线？

- ❌ 不改 CQC/MAFS
- ✅ 加 fixture file
- ✅ 加 regression test

**通过红线审查**。

---

## 7. Phase 2 任务清单（基于 P1.1-P1.6 审计发现）

> 见书 §15 自主修复范围 + §16 完成标准 → Phase 2 实施。

### 7.1 必须改（blocker for hardening goal）

| 来源 | 任务 | 关联见书 |
|---|---|---|
| P1.1 层 1 | `run_resolve.py` + `references/driver_template.py` 加 retry helper，禁止手工重建 JSON | §5.2 |
| P1.1 层 2 | driver template 加 `derive_evidence_id()` 函数（基于 MAFS 返回生成 stable UUID） | §5.2 |
| P1.2 | `references/report_template.md` 含 bounded negative-evidence 措辞 + `check_no_nonexistence_claim()` invariant | §6.2 |
| P1.3 | DEPLOYMENT.md §5.6 加 legacy skill hygiene 指引 | §10 |
| P1.4 | `doctor.py:59` + `resolve_runtime_dependencies.py:56` 改 DEVNULL 模式（**仅这 2 个**） | §4.3 |
| P1.5 | `tests/fixtures/mafs_gf_search/dsh_integration_trace.json` 归档 + `tests/test_gf_replay.py` | §11 / §13 |
| 见书 §4.1 | `SKILL.md` frontmatter 加 `description` 字段 | §4.1 |
| 见书 §4.2 | `install.py` 加 `dsh` / `dsh-desktop` target | §4.2 |
| 见书 §8 | driver template 自 print STOP checkpoint（write + print 同进程） | §8 |
| 见书 §9 | `references/DSH_DEPLOYMENT.md` 隔离 DSH allowlist，**不**进 core SKILL.md | §9 |
| 见书 §7 | `references/lineage_glue.md` 描述 model-authored Axis/SearchOrder 落 artifact 的契约（**只文档，不自动生成**） | §7 |

### 7.2 顺手做（low cost, prevents regression）

| 任务 | 关联见书 |
|---|---|
| DEPLOYMENT.md / README.md / deploy.py 全部更新（DSH target + 真路径） | (housekeeping) |
| `I:/MAFS Skill 1.0/` 部署包同步更新 SHA | (housekeeping) |
| doctor.py 健壮性（subprocess 失败不假阴性） | §4.3 |
| Trusted Pin Manifest 章节加进 SKILL.md `## 0.5` | §4 / §11 |

### 7.3 严守不做（红线）

- ❌ 不改 CQC pin
- ❌ 不改 MAFS pin
- ❌ 不改 CQS/SRP/BudgetEnvelope/MAFS 业务语义
- ❌ 不加 auto ranker / auto candidate selection / auto resolve
- ❌ 不为压低 approval 数删 authority gate
- ❌ 不为压低 approval 数 blanket 改 `capture_output=True → DEVNULL`
- ❌ 不把 DSH allowlist / sandbox tier 写进 core SKILL.md（写到 `references/DSH_DEPLOYMENT.md`）

---

## 8. 风险与 stop rule

| 风险 | 概率 | 缓解 |
|---|:---:|---|
| Phase 2 改某源码后跨平台 ZIP SHA 不一致 | 中 | 见 RA1 模式：4 平台独立 build，任一不一致立即 stop |
| `derive_evidence_id` 函数生成 UUID 不稳定 | 低 | 锁输入字段 + test |
| REPORT.md template 改后 agent 仍手写升级 | 中 | invariant check + DSH_DEPLOYMENT.md prompt hint 双层 |
| 旧 `multi-axis-falsification-search` skill 仍被调 | 中 | DEPLOYMENT.md + DSH 端不暴露 |
| DSHIntegrationTrace fixture 漏检某个 Q | 低 | regression test 覆盖 5 个 Q 全部状态 |

**stop rule**：
- 任一 baseline SHA 在 Phase 2 末尾被漂移 → 立即 stop 并回滚
- 21/21 单测失败 → stop
- verify_delivery.py 非 PASS → stop
- 跨 4 平台 ZIP SHA 任一不一致 → stop
- CQC/MAFS pin 任一漂移 → stop（per 见书 §15）

---

## 9. Phase 1 完成度

| 子项 | 状态 | 交付物 |
|---|:---:|---|
| P1.1 evidence provenance 定位 | ✅ | §2 + 待 Phase 2 修 |
| P1.2 Q3 wording 来源 | ✅ | §3 + 待 Phase 2 修 |
| P1.3 Codex legacy skill 检查 | ✅ | §4 + 待 Phase 2 文档 |
| P1.4 subprocess 审计 | ✅ | §5 + 待 Phase 2 改 2 个 |
| P1.5 DSHIntegrationTrace | ✅ | §6 + `dsh_integration_trace.json` 已生成 |
| P1.6 SHA baseline 锁定 | ✅ | §1 全部 ✓ match |
| 审计报告本身 | ✅ | 本文 |

**Phase 1 完毕，待 HO 验收 → 开 Phase 2**。

---

## 10. 给 HO 的验收点

1. **P1.1 双层根因**是否站得住？尤其是"层 1 driver retry"vs"层 2 MAFS evidence_id 空"的区分
2. **P1.2 REPORT.md 是手写**这个判断对吗？（REPORT.md 不在 driver 写文件列表里）
3. **P1.3 Codex 旧 skill**的处理方案（只文档不删）HO 接受吗？
4. **P1.4 只改 2 个 DEVNULL**是否够？是否要扩到 git status / git log 那些？
5. **P1.5 DSHIntegrationTrace 4.7 KB**字段覆盖度够吗？
6. **Phase 2 任务清单**（§7）按"必须改 + 顺手做 + 严守不做"三档分类，HO 是否同意优先级？

确认后即开 Phase 2（修源码 + 文档 + 部署包 → 4 平台 CI → main push → I: 盘同步 → GF replay → 收尾）。
