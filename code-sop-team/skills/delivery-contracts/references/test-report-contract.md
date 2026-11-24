# 测试报告契约（Report Contract）

定位：verify 后汇总成**可单独发布**的 benchmark 报告。正文零业务词、零具体套件名、零仓库路径；项目值全部走 Contract。

**SSOT 读取顺序**：`config/test-report.yaml` → `learn/test-report.md` → 均无则 AskQuestion + 按下表起草。

## 必备字段

| 区块 | 字段 | 说明 |
|------|------|------|
| `report` | `id` / `doc_path` | 报告标识；产物路径（默认落 `docs/08_…` 号位） |
| | `version` / `title` / `audiences` | 版本头、标题、读者（engineering / qa / ops 等） |
| `run` | `log_dir` / `collect_script` | 日志目录（报告引用其时间戳）；采集脚本，可为 null |
| | `suites[]` | 每项：`id` · `tier` · `label` · `command` · `cwd` · `parse` · `optional` |
| `metadata` | `sprint_key` / `environment_hint` | 环境描述，**报告内不得出现密钥** |
| `verify` | `l1_script` / `anchors` | 锚点脚本与 grep 关键词 |
| `delivery` | `include` / `source` | 是否摘录交付走查结论及来源 |

## 报告必备结构与取证要求

| 契约要素 | 落在哪节 | 硬要求 |
|----------|----------|--------|
| 范围 | §0 定位 + §1 套件表 | 写明覆盖哪些层；未覆盖的进 §7 |
| 环境 | §0 环境（`environment_hint`） | 无密钥；本地栈与 CI 分列 |
| 用例统计 | §1 摘要表 + §2 矩阵 | 层级 · 命令 · 结果 · 墙钟；2.2 给用例数 |
| 失败项 | §1 FAIL 行 + §6 修复项 | 无缺陷时显式写「无 P0/P1」 |
| 证据 | §1 日志路径 + §8 复现命令 | 命令原样列出，先决条件一句 |
| 结论 | §1 一段话 + §10 | 是否可作发版 benchmark |
| 风险 | §0 Blocker + §7 Skip | P0 单列；跳过项写原因，不静默省略 |

## 骨架（逐块拼接）

```markdown
# {产品名} · {报告定位}
> **读者**：… ｜ **版本**：v{x.y} · {date} ｜ **Sprint**：`{id}`
> **基线 commit**：`{sha}` ｜ **环境**：{hint · 无密钥} ｜ **Blocker**：无 | P0
```

```markdown
## 1 执行摘要
| 层级 | 命令 | 结果 | 墙钟 |
|---|---|---|---|
| … | `…` | ✅ PASS / ❌ FAIL | ~Ns |
```

```markdown
## 2 测试矩阵
### 2.1 自动化分层 L0–L3 ｜ 2.2 E2E（若有） ｜ 2.3 域/模块（若有）
| 层 | 覆盖 | 状态 |
```

```markdown
## 6 本 Sprint 修复项
| 问题 | 处理 |
## 7 Skip / 环境说明
| 项 | 说明 |
## 8 复现命令（先决条件一句话）
```

```bash
bash scripts/verify.sh --l1   # Contract suites[].command 原样列出
```

```markdown
## 10 结论
Done when 是否闭合 · 后续回归对照哪几节 · 差异阈值（如 perf >20% 复评）
```

可选节：§3 业务闭环 · §4 性能 benchmark · §5 交付走查（`delivery.include`）· §9 关联文档。§1 摘要、§8 复现、§10 结论建议保留。

## 运行模式

| 模式 | 何时 | 动作 |
|------|------|------|
| `full` | 发版档 / 要最新数字 | 顺序跑套件 → 写 log → 渲染 |
| `from-logs` | 刚跑完 verify | 只解析 `log_dir` → 渲染，标注 log 时间戳 |
| `refresh` | 仅改版本/commit | 不跑套件，只更新报告头与关联链接 |

## 验收与禁止

- 文件头保留 `<!-- generated: report · regenerate: /report -->`；产物自动生成，**禁止手写**。
- L1 锚点脚本绿 + 语义完整，才可标 ✅。
- 禁止：无套件 exit 0 / 无 log 仍写「全部 PASS」；无 Contract 时编造矩阵行而不标 `inferred`。
- 禁止：用报告替代 task-verify，或替代 delivery 的 Blocker 清零。
- 禁止：正文写死项目套件名、域名、产品名、具体章节号。

> 来源：Super Cursor /test-report
