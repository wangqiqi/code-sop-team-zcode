---
name: sop-gate
version: 1.3.0
description: Executes the four hard gates through a zero-dependency Python CLI: init, gate-check, task-verify, verify, next-task, followup, approve, release-check, friction-log/report, doctor and an optional git pre-commit hook.
name_en: SOP Gate — Hard Gates
name_zh: 硬约束闸门
description_en: Executes the four hard gates through a zero-dependency Python CLI: init, gate-check, task-verify, verify, next-task, followup, doctor and an optional git pre-commit hook.
description_zh: 四道硬闸的执行器：init、gate-check、task-verify、verify、followup、doctor 与可选 git pre-commit，跨平台零依赖。
user-invocable: true
argument-hint: Gate command, e.g. task-verify TASK-002 --evidence "..."
argument-hint-en: Gate command, e.g. task-verify TASK-002 --evidence "..."
argument-hint-zh: 闸门命令，如 `task-verify TASK-002`
---

# sop-gate · 硬约束闸门

这是本专家团的**硬约束执行层**。所有闸门判定通过 `bin/sop_gate.py` 完成，Python 标准库实现、零第三方依赖、Windows/macOS/Linux 通吃、不依赖目标项目任何既有结构。

## 状态存放（跨平台关键）

- 状态目录：`<项目根>/.zcode/sop/`，主文件 `plan.md`
- 项目根自动探测：`--root` > 环境变量 `SOP_PROJECT_ROOT` > 向上找 `.git` > 当前目录
- 与具体 IDE 无关；同一套脚本随插件走，换机器照样用

## 脚本位置

```
<插件目录>/bin/sop_gate.py
```

**绝不要写死路径**——插件可能装在任意用户名、任意插件文件夹名下。按优先级定位：

```bash
# 1) 环境变量优先（用户可预先设 SOP_GATE）
# 2) 插件根相对定位：本技能基目录为 <插件根>/skills/sop-gate，插件根 = 基目录的上两级
SOP_GATE="${SOP_GATE:-<插件根>/bin/sop_gate.py}"
[ -f "$SOP_GATE" ] || { echo "未找到 sop_gate.py，插件可能未正确安装" >&2; exit 2; }
python "$SOP_GATE" <cmd> [--root <项目根>]
```

```powershell
# PowerShell 等价写法
$sopGate = $env:SOP_GATE
if (-not $sopGate) { $sopGate = "<插件根>\bin\sop_gate.py" }
python $sopGate <cmd> --root <项目根>
```

**Python 从哪来（重要）**：闸门脚本零依赖，但必须有解释器。普通 Windows 不一定有可用 `python`（常只是 Microsoft Store 占位入口），因此会话里按 `python` → `py -3` → `python3` 的顺序探测，找到一个能跑的就用；本 skill 示例统一写 `python`。

- 完全找不到解释器时不要在闸门未跑的情况下继续编码，按「软约束降级模式」显式告知用户缺什么（见 `references/failure-playbook.md`）。
- 用户自己的终端里要跑，可用解释器绝对路径；`doctor` 会报出探测到的解释器。
- `install-hook` 会把**当前解释器绝对路径**内嵌进 git 钩子，所以即使 PATH 里没有 `python`，钩子仍能跑；重装钩子可重新定位。
- 只有「内嵌路径失效 + PATH 也没有 python」时才软降级放行，且会打印告警——这是显式降级，不是静默放行。

VERIFY 回退探测会用**当前解释器名**（避免只有 python3 的机器上写死 python 而失败）。

**新机器 / 新项目 / 闸门报错时，第一件事是跑 `doctor`**——它会明确指出断在哪一环（skill 缺失、plan 格式坏、目录不可写、VERIFY 未设、非 git 仓库等），比逐条试命令快得多。

**开工前的自检**归主理人负责（`sop-team` 第 0 步：先探测解释器与脚本，代码目录确定后跑 `doctor --root <目录>`）；本 skill 只负责闸门本身，不重复做入场问询。

## 命令速查

| 命令 | 用途 | 成功 |
|------|------|------|
| `init [--force]` | 生成 plan.md 工作副本，并自动把 `.zcode/sop/` 补进 `.gitignore`（幂等） | 0 |
| `status` | 打印闸门状态 | 0 |
| `doctor` | **环境与链路自检**：Python/脚本/skill/项目根/plan 解析/批准格式/证据/状态锁/gitignore/钩子及其内嵌脚本与解释器路径/测试套件一次查完 | 0 就绪，1 有阻塞 |
| `gate-check` | **run 硬闸门**：PLANNING / PLAN_APPROVED（必须是真实日期）校验 | 0 放行，1 BLOCK |
| `plan-check` | 开工前 plan 完整性（活跃任务/执行顺序/验收可执行） | 0 OK，1 FAIL |
| `task-verify [TASK_ID] [--evidence "证据"]` | **单任务验收**：执行验收列命令，fail-closed；人工验收须非空 `--evidence` 留证；失败自动累加补丁循环计数；状态写受原子锁保护 | 0 PASS，1 FAIL，**3 MANUAL-PENDING** |
| `verify [--force]` | Sprint/打版前全量验收：**默认要求任务全部 ✅**，再跑 plan `VERIFY`；VERIFY 未设时**回退探测**项目验收入口并标 `[AUTO-DETECTED]` | 0 PASS，1 FAIL |
| `next-task [--apply]` | 找下一个 ACTIVE（跳过 SPIKE/REV/DOC）；`--apply` 把结果写回 ACTIVE/NEXT | 0 |
| `followup [TASK_ID] [--reset]` | 查看「同一 TASK 连续失败轮次」；`--reset` 清零（可指定任务）。**≥2 轮即补丁循环，应转 SPIKE** | 0 |
| `approve [--force]` | 用户确认后写入 PLAN_APPROVED、置 PLANNING=false；**前置校验 VERIFY + plan-check** | 0 或 1 BLOCK |
| `set KEY VALUE` | 设元数据（PLANNING/SPRINT/ACTIVE/NEXT/VERIFY/RELEASE_BUMP…）；拒绝注释定界符，并按键校验值（批准日期/布尔/计数/任务 ID/bump 档位） | 0 或 2 |
| `release-check [--bump patch\|minor\|major]` | **发版前置预检**：最新 semver tag → next_version（`--bump` > plan `RELEASE_BUMP` > patch）、CHANGELOG `[Unreleased]`、plan 残项；不替代 `verify` 出口闸 | 0 ready，1 NOT-READY |
| `friction-log --task ID --verify pass\|fail\|manual [--rounds N] [--rework N] [--note "…"]` | 逐 TASK 记摩擦数据（轮次/返工/验收结果），追加到 `.zcode/sop/friction.jsonl` | 0 |
| `friction-report` | 汇总摩擦：verify 通过率 / 平均轮次 / 返工 TOP / followup 联动 / 高摩擦任务建议立 SPIKE | 0 |
| `install-hook` | 可选：装 git pre-commit，提交前强制 **plan-check + gate-check**；**内嵌当前解释器绝对路径**（不依赖 PATH，适配 ZCode 会话解释器） | 0 |
| `uninstall-hook` | 卸载 git pre-commit | 0 |

退出码：`0` OK/PASS；`1` BLOCK/FAIL；`2` 参数/环境错误；`3` MANUAL-PENDING（人工验收待留证）。**任何非 0 都不得继续编码、标 ✅ 或提交。**

### 验收列里的管道符

Markdown 表格里 `|` 会拆列。验收命令含管道符时，写 `\|` 转义（`echo a \| grep a`），脚本会还原成 `|` 再执行；忘记转义时脚本会把多余列并回 Acceptance，不会截断成半截命令。写完后用 `task-verify` 实跑确认命令完整。

### 验收分层：TASK 定向，出口全量

两个时机各跑各的，不要混：

| 时机 | 跑什么 | 禁止 |
|------|--------|------|
| 每个 TASK 收尾（`task-verify`） | 只跑**本 TASK 验收列**——定向测试（`pytest tests/test_x.py -q` / `vitest run path/to/x.test.ts`）或 `manual:` 留证 | 把出口全量命令写进验收列；TASK 过了「顺便」再跑一遍全量 |
| Sprint 全部 ✅ 后（`verify`） | plan `VERIFY` **一次** | 每个 TASK 结束都跑大验证 |

验收列写定向命令、`VERIFY` 写全量命令是**规划期就要分清**的事——写反了，轻则每个任务白跑几分钟全量，重则把「出口闸一次大验证」稀释成噪音。

### 回归测试套件

`python tests/test_sop_gate.py` 有 43 个用例（标准库 unittest，零依赖），覆盖四道闸门、畸形输入、超时、并发状态锁、钩子内嵌解释器及其失效检测、跨平台与所有历史 bug 的回归。改动闸门脚本后**必须跑全绿**才可打包。每个用例在独立临时 git 仓库中跑，不污染项目。

### 异常、边界与兜底（必读）

闸门失败时的退出码语义、畸形 plan / 证据 / 批准值、重复 ID、状态歧义、并发写冲突、钩子残留、工具缺失时的**降级模式**，统一见 `references/failure-playbook.md`。

**一句话原则**：判定不了 = 不通过；工具不可用 = 显式声明降级，绝不伪造闸门输出或成员结论。新机器 / 新项目 / 闸门报错，第一件事永远是 `doctor`。

## 四道闸门（铁律）

1. **规划闸门**：无 `PLAN_APPROVED` 或 `PLANNING=true` → `gate-check` 返回 BLOCK → 禁止写业务代码。
2. **验收闸门**：每任务 `task-verify` 必须 PASS 才能标 ✅ / commit。验收列必须可执行命令或 `manual:` 声明；描述性文字会 **fail-closed 直接 FAIL**。`manual:` 不加 `--evidence` 返回 3，**不算 PASS**。证据与当时的验收要求绑定：**Acceptance 一改，旧证据立即失效**，必须重新留证。
3. **出口闸门**：Sprint 收尾 / 打版前 `verify` 必须全绿。它有两道检查：① **所有 TASK 已 ✅**（残项需 `--force` 且用户明确接受）② plan `VERIFY` 命令退出码 0。`VERIFY` 由**规划师**写 plan 时设定，主理人 `approve` 前会硬校验——留空则批准直接被 BLOCK。plan **解析不到任何 TASK 行时直接 FAIL**（防「plan 被改坏=假收口」）。所有验收命令有 10 分钟超时保护，`SOP_VERIFY_TIMEOUT=<秒>` 可覆盖，`0` 表示不限。
4. **补丁循环闸门**：`task-verify` 每次失败会把该 TASK 的连续失败轮次写进 `followup.json`，**第 2 次失败**起输出 `FOLLOWUP-GATE` 告警：禁止继续 patch，必须立 `SPIKE-*`。任务真正 PASS 后计数自动清零；也可 `followup --reset` 手动清。判据与五个高频反复区见 `../quality-checklists/references/patch-loop.md`。

### 状态文件不入库

`.zcode/sop/` 是本地执行面板（plan / 验收证据 / 补丁计数），`init` 会自动写进 `.gitignore`。它一旦被提交，多会话与多团员就会互相覆盖 plan，证据里的复核人与截图路径也会进仓库。`doctor` 会检查是否已跟踪；若历史上已跟踪，按提示执行 `git rm --cached -r .zcode/sop/`。

### verify 的回退探测（不是放水）

`VERIFY` 留空时 `verify` 会按跨平台可靠度依次探测：`scripts/verify.py|test.py` → `package.json` 的 `verify`/`test` → pytest 配置或 `tests/` → `scripts/*.sh`（Windows 用 `sh` 前缀执行）。命中后仍打印 `[AUTO-DETECTED]` 并要求固化写回 plan——**探测只避免「无命令可跑」，不放宽任何 PASS 标准**。

## 两个层次：软约束 + 硬约束

- **软约束（必做）**：主理人在 MD 铁律中强制"关键节点必须跑对应闸门命令"，并把输出贴出。
- **硬约束（可选加固）**：`install-hook` 装 git pre-commit，提交前依次跑 `plan-check`（结构）与 `gate-check`（规划是否已批准），任一不过就拒绝提交；钩子内嵌当前解释器绝对路径，不依赖 PATH。只有内嵌路径与 PATH 都找不到 Python 时才告警软降级（不阻断用户）。重复执行 `install-hook` 会把旧版钩子原地升级。

## 验收列写法（决定 task-verify 能否判）

| 写法 | 判定 |
|------|------|
| `` `npm run test` `` · `` `pytest` `` · `` `python -m pytest -q` `` | ✅ 可执行，直接跑 |
| `` `manual: 截图路径 + 复核人 + 步骤` `` | ⚠️ 须 `task-verify <ID> --evidence "…"` 留证才 PASS；否则 rc=3 |
| 「功能正常」「UI 没问题」 | ❌ 描述性 → FAIL |

证据存放在 `<项目根>/.zcode/sop/evidence.json`，记录任务、证据正文、时间戳与原始验收要求，可随时复核。

### 验收命令的跨平台写法（易踩坑）

脚本用 `shell=True` 执行，Windows 走 `cmd.exe`、macOS/Linux 走 `/bin/sh`。差集在于**单引号**：

| 写法 | Windows | POSIX | 建议 |
|---|---|---|---|
| `python -c "print('ok')"` | ✅ | ✅ | 外层双引号、内层单引号，两边都行 |
| `python -c 'print("ok")'` | ❌ cmd.exe 不认单引号 | ✅ | **Windows 上会失败** |
| `npm test` / `pytest -q` | ✅ | ✅ | 最稳，优先选 |
| 复杂管道 `a \| grep b \| xargs c` | ⚠️ 语义不同 | ✅ | 改用脚本文件或 `python -c` |

**规则**：验收列优先写「单一命令 + 参数」，需要引号时一律外层双引号；复杂逻辑写成 `scripts/verify_xxx.py` 再调用。

## 与团队协作的衔接

- 主理人负责：`init` / `approve` / `gate-check` / `set` / `install-hook`
- 规划师负责：**写 plan.md** + 设 `SPRINT` / `ACTIVE` / `VERIFY` + `plan-check` 自检
- 执行阶段（主理人驱动）：`task-verify`（每任务）/ `next-task --apply` / `verify`（收尾）
- 审查官与调研员只读，不碰闸门写操作

详细判定语义见 `references/gate-semantics.md`。
人格话术与映射见 `references/personas.md`。
**三公理、编辑主权、反幻觉纪律见 `references/constitution.md`** — 闸门管「能不能过」，它管「话能不能这么说、文件能不能这么改」。多 agent 并行写同一仓库时，全员必须先读这一份。
