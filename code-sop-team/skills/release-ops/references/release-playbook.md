# 发版手册

角色：发版官（毕达成）按清单自治执行，每步失败即停并报告；merge / PR / 保留 / 丢弃的方向由用户定，发版官不替用户选。

## 出口前置

- [ ] 当前 ACTIVE 或本 Sprint P0 全 ✅（或用户明确只做分支收尾）
- [ ] `verify` 已实际执行且 PASS；无意外脏文件、无密钥
- [ ] UI / 功能类 Sprint：建议先做交付走查；有 Blocker 须在提问前报告

顺序固定：**verify →（建议）交付走查 → 用户 4 选 1 → 执行 → 可选 worktree 清理 → 可选打版**。

## Sprint 出口 4 选 1

| # | 选项 | 前置 | 动作 |
|---|---|---|---|
| 1 | 本地 merge | 验收绿 | 切基线分支 → merge feature → 跑 verify → 经用户确认后删本地 feature |
| 2 | Push + PR | 验收绿 | `git push -u origin HEAD` → 建 PR（Summary + Test plan，含任务 ID） |
| 3 | 保留分支 | 无 | 仅 push 或保持现状；不 merge、不清理 worktree |
| 4 | 丢弃 | **用户明确打字确认** | 禁止静默 force / reset |

Detached HEAD 或无名分支：只呈现选项 2–4。

## 发版模式

- `patch-per-task`：每任务只 commit，Sprint 末统一打 tag（母版 / 批量交付）。
- `tag-per-commit`：每任务 commit 同轮打 tag（高频交付仓库）。

## semver 原则

| 级别 | 何时用 | 自动 |
|---|---|---|
| patch | 单任务、文档 / 修复；`tag-per-commit` 默认 | 是 |
| minor | 用户可见新能力、无 breaking | 否，须显式允许 |
| major | Breaking change | 几乎从不自动 |

## patch 密度与 follow-up

- 同一症状簇连续多个 patch：CHANGELOG 条目须能检索到根因 Sprint ID。
- 建议把短期 follow-up 合并为一次 minor 或固定周节奏 tag，避免数日内 N 个 patch。
- 打版前若本版只有 follow-up 类 UX 修补，建议先做交付走查并确认无 Blocker。
- 连续 patch 不得出现同版本双节：在同一节下追加小节，或合并叙事只留一节。

## tag 规范

- 每个发布 commit 对应一个 tag；tag message 引用 CHANGELOG 节。
- annotated tag，打在含 CHANGELOG 的 commit 上。

```bash
git tag -a "v1.2.3" -m "Release 1.2.3: short summary"
git tag -l --sort=-version:refname
```

- 已发布的 tag 勿重打；打错用 patch 版本修正：本地未推送则删除重打，已推送则报告团队策略，勿擅自 force-push。
- 命名按仓库配置：semver（`v1.2.3`，可选前缀）或 calver（时区在 CHANGELOG 说明一次）。

## 版本解析步骤

在**最新 tag** 上 bump，按优先级解析：

| 优先级 | 来源 | 匹配 |
|---|---|---|
| 1 | 环境变量指定的 tag glob | 自定义 glob |
| 2 | plan 里的版本行 `major.minor` | `v{line}.*` |
| 3 | 缺省 | `v*`，仓库最新 semver tag |

- 无匹配 tag 时起始版本：plan 默认值 → 环境变量 → `0.1.0`（有版本行时为 `{line}.0`）。
- 打 tag 前核对：最新 tag 与 CHANGELOG 上一版一致；next_version 异常则不打 tag。

## 打版清单

- [ ] 版本已定 · plan 本版 ✅（若用）
- [ ] verify 通过 · 无 WIP
- [ ] 安全面（auth / 密钥 / PII）无 Critical / High 未处理
- [ ] CHANGELOG `[Unreleased]` 折叠进 `## [x.y.z] - YYYY-MM-DD`（新版在上）
- [ ] bump manifest（package.json / pyproject.toml / Cargo.toml 等）· 文档同步
- [ ] 发版 commit：`chore(release): vX.Y.Z`
- [ ] annotated tag · 按团队策略 push（默认不 push，除非用户明确）

## CHANGELOG 门禁

- 必须存在 `[Unreleased]`；未发布内容积压于此，打版时折叠。
- 同一版本节点内不得重复同级小节；`[Unreleased]` 顺序固定 Added → Changed → Fixed。
- 版本节标题 `## [x.y.z] - YYYY-MM-DD`，新版在上；同一版本不得出现两个块。

## 多架构打包（可选 · 有安装包或二进制分发时）

- [ ] 架构矩阵显式（OS × CPU）写在 docs 或 CI，不用「本机 arch」隐含
- [ ] 构建脚本 / CI job 覆盖矩阵每一格，或文档标明刻意不做的格
- [ ] 原生依赖在矩阵内可解析、可复现；发版说明注明支持的平台组合

## 禁止

- 未 verify 就打 tag 或 merge
- 对共享 / 默认分支 force-push；无确认的 `reset --hard` / `clean -fdx`
- 重打已发布 tag
- verify 失败后继续改 CHANGELOG / 打 tag（应先修代码）

> 来源：Super Cursor /release
