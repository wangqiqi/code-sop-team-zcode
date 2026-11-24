# Git 提交纪律

适用：任何 commit / push / 合并之前。主理人驱动日常提交；事务官只读核对仓库整洁度并输出差异表。

## 分支命名

| 前缀 | 用途 |
|---|---|
| `feat/*` | 新功能 |
| `fix/*` | 缺陷修复 |
| `chore/*` | 杂务与构建 |
| `docs/*` | 文档 |

- 短生命周期 feature 分支，合并后即删（删本地分支须用户确认）。
- 受保护分支（main / master）须走 PR + review。

## 提交信息

格式 `type(scope): summary`，scope 可选。

```text
<type>[optional scope]: <description>
[optional body]
[optional footer]
```

| type | 用途 | SemVer |
|---|---|---|
| `feat` | 新功能 | MINOR |
| `fix` | 缺陷修复 | PATCH |
| `docs` `style` `refactor` `perf` `test` `build` `ci` `chore` | 非功能面变更 | 通常无版本跃迁 |
| `BREAKING CHANGE:` 页脚或 `type!:` | 破坏性 API / 行为变更 | MAJOR |

- 一提交一逻辑变更。
- 正文解释 **why**，不只 what。
- scope 填受影响模块名，如 `feat(api): …`。

## 提交前检查

- [ ] `git status` —— 无 `.env`、密钥、意外大文件
- [ ] 不 stage 本地工作文件（plan 已在 `.gitignore`）
- [ ] `git diff --stat` —— 范围符合当前任务
- [ ] 任务验收已跑（启用 plan/run 时 `task-verify`）
- [ ] CHANGELOG `[Unreleased]` 已记用户可见变更（若有）
- [ ] message 引用任务 ID，如 `docs(readme): sync summary (DOC-001)`

## 自动提交时机

| 时机 | 动作 |
|---|---|
| 每任务 ✅ | 与标 ✅ 同轮 commit |
| Sprint 收尾 | 同轮 commit |
| `tag-per-commit` 模式 | 同轮再打 tag |

- commit 只含已跟踪的代码 / CHANGELOG / README 等；本地工作文件不进 commit。
- 不 amend 已 push 的 commit（除非用户明确要求）。

## 合并前

- [ ] 本地验收绿
- [ ] 无 WIP commit
- [ ] UI / 功能类 PR 建议先做交付走查；有 Blocker 须写进 PR 描述

## worktree 隔离（可选）

并行任务或功能分支时可用，主 worktree 保持可发布基线。

```bash
git worktree add ../repo-feature-<name> -b feat/<name>
git worktree list
git worktree remove <path>
```

- 清理前验收须绿；`remove` 要求无未提交改动并经用户确认。
- 清理时机与 Sprint 出口 4 选 1 的选择保持一致。

## 禁止

- 对共享 / 默认分支 `git push --force`
- `git reset --hard` · `git clean -fdx`
- `--no-verify` · `--no-gpg-sign`
- 提交密钥或密钥文件

> 来源：Super Cursor /git
