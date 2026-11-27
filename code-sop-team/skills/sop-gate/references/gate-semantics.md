# 闸门判定语义（SSOT）

本文件是硬约束判定的权威说明，转译自 Super Cursor 的 `runner.sh` 与 `rules/workflow.mdc`，由 `sop_gate.py` 实现。

## gate-check（run 硬闸门）

| 条件 | 结果 |
|------|------|
| plan 不存在 / 未 init | BLOCK |
| `PLANNING` ∈ {true,1,yes} | BLOCK — 仍在规划阶段 |
| `PLAN_APPROVED` 不是 `YYYY-MM-DD` 真实日期（含空、`(none)`、`hacked`） | BLOCK — 规划未经有效确认；`set` 也不能凭空造批准值 |
| 其余 | OK — 放行 |

**设计意图**：杜绝"聊完就改代码、范围漂移"。只有用户明确确认过 Goal/Done/Out of scope 并写入批准日期，才允许写业务代码。

## approve（批准 · 带前置校验）

`approve` 不是简单盖章，写入前会做两道硬校验（`--force` 可跳过，仅供用户明确要求时使用）：

| 校验 | 不通过 |
|------|--------|
| `VERIFY` 必须非空 | BLOCK——否则收尾/打版永远 FAIL |
| `plan-check`（`for_approve` 模式，不看 PLAN_APPROVED）必须 OK | BLOCK——结构不合格不许批准 |

**设计意图**：堵住"直接 approve 绕过 plan-check"的口子，同时保证出口闸从批准那一刻起就是通的。

## plan-check（开工前完整性）

检查项（每项 WARN/FAIL 计入问题数，>0 即返回 1）：
- 是否有活跃 `⬜`/`🔧` 任务
- `ACTIVE` 是否设置
- `SPRINT` 是否设置
- 是否有 `**执行顺序**`（兼容 `**Order**`）行
- `VERIFY` 是否设置：`PLANNING=true` 时只 INFO（规划期可后补）；进入执行后缺失 = WARN 计入 FAIL
- `PLANNING=true` 时仅 INFO 不阻断编码判定；否则 `PLAN_APPROVED` 缺失 = FAIL；`for_approve=true` 时跳过该项（批准流程本身就要写它）
- 每个活跃任务：验收列是否可执行（描述性文字会 WARN）；是否有 Target 落点
- 结构 fail-closed：重复 TASK ID（后者会覆盖前者造成假完成）、状态格同时出现 `⬜ ✅`（歧义）→ 直接 FAIL

**设计意图**：fail-early，别等 `task-verify` 才发现验收列是空话。

## task-verify（单任务验收 · fail-closed）

按验收列分三类：

1. **exec（可执行命令）**：从反引号内提取命令；有多个反引号时优先取「像命令」的那段（`src/` 这类路径片段不会被误执行），在项目根执行，退出码 0 = PASS。
2. **manual（人工验收）**：验收列以 `manual:` 开头 → 必须用 `task-verify <ID> --evidence "<证据>"` 留证才算 PASS。
   - 无证据或证据只有空白 → 退出码 **3（MANUAL-PENDING）**，明确不是 PASS，主理人不得标 ✅。证据超长会截断并提示改存文件。
   - 有证据 → PASS，证据写入 `.zcode/sop/evidence.json`（含任务、证据正文、时间戳、原始验收要求），后续复核可查。
   - **证据绑定验收要求**：再次验收时会比对当前 Acceptance 与留证时记录的要求。要求变了 → 旧证据失效，返回 3 要求重新核对；老版本证据没有 `acceptance` 字段同样要求重留。这是为了防止「验收被改宽/改坏后旧证据仍放行」。
3. **prose（描述性文字）**：无法自动判定 → **直接 FAIL**，绝不静默 SKIP。

**设计意图**：杜绝"好了但测不过"和"描述性验收假完成"。人工验收不是免检通道——它只是把判定权交给人，但必须留下可追溯的证据，否则和描述性文字没有区别。

### 验收分层（TASK 定向 · 出口全量）

- TASK 验收列写**定向测试**（单文件 pytest / `vitest run <path>`），只覆盖本 TASK 改动面；全量命令属于 plan `VERIFY`，只在 Sprint 全部 ✅ 后由 `verify` 跑**一次**。
- TASK PASS 后禁止「顺便」加跑全量——出口闸一次大验证，别稀释成噪音。

### 失败计数（补丁循环闸）

- 每次 `exec` 类验收退出码非 0 → 该 TASK 的连续失败轮次 +1，写入 `.zcode/sop/followup.json`。
- 达到 **2 轮** → stderr 输出 `FOLLOWUP-GATE` 告警：禁止继续 patch，必须立 `SPIKE-*`。
- TASK 真正 PASS（exec 通过或 manual 留证）→ 该任务计数**清零**。
- `prose` 失败不计入——那是 plan 写法问题，不是实现反复失败。
- `manual:` 返回 3（待留证）**不计数**——它不是失败，只是尚未完成核对。
- 人工清零：`followup --reset [TASK_ID]`；查看：`followup`。损坏的负值计数会钳到 0（负值会静默关闭补丁闸）。
- 读-改-写全程受 `.zcode/sop/.lock` 原子锁保护；拿不到锁按 BLOCK 处理，超时/陈旧锁自动清理。

**设计意图**：把"改了三四轮还在改"从主观感受变成可观测指标。计数由脚本执行，不靠人自觉。

## verify（出口全量验收）

两道检查，全过才 PASS：

1. **前置：任务全部完成** —— plan 中所有 `TASK-*` 必须为 ✅（`SPIKE-`/`REV-`/`DOC-` 不计入）。有残项 → FAIL 并列出 ID。用户明确接受残项时才可 `--force`（会打印 WARN）。
2. **执行**：读取 plan 头部 `<!-- VERIFY: <命令> -->` 执行，退出码 0 = PASS。

### VERIFY 未设置时的回退探测

`VERIFY` 为空时不立刻 FAIL，而是按**跨平台可靠度**依次探测，命中即用并标 `[AUTO-DETECTED]`：

| 顺序 | 探测目标 | 采用命令 |
|---|---|---|
| 1 | `scripts/verify.py` · `scripts/test.py` · `verify.py` · `test.py` | `python <path>` |
| 2 | `package.json` 的 `scripts.verify` / `scripts.test` | `npm run verify` / `npm test` |
| 3 | `pyproject.toml` · `pytest.ini` · `tox.ini` · `setup.cfg` · `tests/test_*.py` | `pytest -q` |
| 4 | `scripts/verify.sh` · `scripts/test.sh` · `verify.sh` | POSIX `./x.sh`；**Windows 用 `sh x.sh`** |

探测不到 → FAIL 并给出 `set VERIFY` 的具体命令。

**为什么顺序是这样**：`.py` 与 npm 在 Windows/macOS/Linux 都能直接跑；`.sh` 在 Windows cmd.exe 下 `./x.sh` 必然失败（`'.' 不是内部或外部命令`），所以放最后并做平台适配。

**探测不是放水**：它只避免"plan 忘写 VERIFY 就永远无法收尾"，标准仍是退出码 0。命中后必须 `set VERIFY` 固化写回 plan——每次都靠猜等于没有出口闸。

**设计意图**：防止"任务还欠着但 VERIFY 命令恰好通过"就收尾/发版——那是假收口。

**责任主体**：`VERIFY` 由**规划师**在写 plan.md 时设定，主理人 `approve` 时硬校验。这是唯一保证出口闸可达的设计——没有它，verify 永远报"未设置"。

**边界**：`verify` 先做结构检查（重复 ID / 状态歧义）再判完成；`--force` 且零任务时放行但显式 WARN「零任务」，必须在汇报中说明。

## next-task（推进）

按 `**执行顺序**` 找第一个状态为 `⬜`/`🔧` 的任务；跳过 `SPIKE-`/`REV-`/`DOC-` 前缀（调研/审查类不进入执行主路径，但仍受 gate-check 约束）。

- 默认**只报告**，不改 plan。
- 加 `--apply` 才把结果写回 `ACTIVE` / `NEXT`——主理人在 Phase 2 推进时必须用 `--apply`，否则下一轮仍停在旧 ACTIVE。

## 递归分解与防漂移（源自 workflow.mdc）

- 规划先冻结 L0 Goal / Done when / Out of scope，再划 L1 Theme，同层 MECE 拆 TASK。
- 执行阶段只做当前 ACTIVE 分支；发现新 Theme 或横向扩张 → 标 `⚠️` 回规划（Phase 1），不得追加到当前 TASK。
- 实现步骤留在 TASK 内部，不为单文件/字段/命令单独建任务。
- 需方案决策的内容走 `SPIKE-*`，不与实现 TASK 混合。
- 同层节点 >5 先重查分区轴，必要时拆 Sprint。

## 规模门禁（任务数 > 5）

预估或已列任务数 > 5 → 禁止直接编码，先走规划（Phase 1）写入 plan.md 并获用户确认。≤5 的清晰小改可直述执行，仍建议 gate-check。

## 及时 commit（源自 run skill）

- 每个 TASK ✅ 后同轮必须 `git commit`（不含 plan.md，plan 属本地状态）。
- 仅改 plan.md 不提交。
- 默认不 push，用户明确要求或发版时再推。
- commit message 含任务 ID：`type(scope): summary (TASK-003)`。

## 任务 ID 前缀

| 前缀 | 含义 | next-task |
|------|------|-----------|
| `TASK-` | 常规实现 | 进入主路径 |
| `SPIKE-` | 方案调研 | 跳过 |
| `REV-` | 代码审查 | 跳过 |
| `DOC-` | 文档 | 跳过 |

## 异常、并发与降级

闸门判定之外的失效模式（脚本缺失、批准值伪造、证据损坏、状态锁竞争、钩子残留、工具不可用时的降级模式）**统一以 `failure-playbook.md` 为准**。核心三条：

- 判定不了 = 不通过（fail-closed）；
- 读-改-写状态受 `.lock` 原子锁保护，`--force` 之外没有任何静默放行；
- 工具不可用时只能声明降级，不得伪造闸门输出或成员结论。
