---
name: release-ops
version: 1.0.0
description: Git discipline, four release strategies with semver, deployment playbook, project scaffolding and long-horizon three-layer planning.
name_en: Release & Ops
name_zh: 发版与运维
description_en: Git discipline, four release strategies with semver, deployment playbook, project scaffolding and long-horizon three-layer planning.
description_zh: Git 纪律、发版四选一与 semver、部署手册、脚手架与长程三层规划。
user-invocable: true
argument-hint: Release action, e.g. release, tag, scaffold
argument-hint-en: Release action, e.g. release, tag, scaffold
argument-hint-zh: 发版动作，如 发版/打 tag/脚手架
---

# release-ops · 发版与运维

代码交付的收尾面：提交怎么写、Sprint 怎么出口、版本怎么打、部署面怎么对齐、空仓库怎么起、大目标怎么跨 Sprint 收敛。

## 该用哪一份

| 参考 | 何时用 | 角色 |
|---|---|---|
| `references/git-discipline.md` | 每次 commit / push / 合并前 | 主理人驱动；事务官只读核对 |
| `references/release-playbook.md` | Sprint 全 ✅ 要出口、要打 tag、整理 CHANGELOG | 发版官（毕达成） |
| `references/ops-deploy.md` | 改 compose / `.env.example` / nginx / 部署文档 | 主理人执行，事务官核对 |
| `references/scaffold.md` | 空仓库起项目、已有项目补脚本与审计 | 主理人（须用户确认） |
| `references/long-horizon.md` | 跨多个 Sprint 的大目标、resume | 主理人 |

## 与闸门的衔接

- 打版前 `verify` 必须 PASS；非 PASS → 停，先修代码，不碰 CHANGELOG / tag。
- 每任务 `task-verify` PASS 才能标 ✅，并与标 ✅ 同轮 commit。
- `gate-check` 未放行不得写业务代码。
- 出口顺序固定：`verify` → （建议）交付走查 → 用户 4 选 1 → 执行 → 可选打版。
- 交付走查有 Blocker 时，须在向用户提问前报告，不得直接进 merge。

## 角色分工

| 角色 | 干什么 | 不干什么 |
|---|---|---|
| 主理人 | 跑闸门、决定出口方向、发起提问、执行 merge / PR | 不替用户选 4 选 1 的答案 |
| 发版官（毕达成） | 按清单自治打版；每步失败即停并报告 | 不决定「发不发」「merge 还是 PR」 |
| 工程事务官（舒井然） | 只读核对环境 / env / compose / nginx 一致性、起草 CHANGELOG | 不改配置、不 commit、不碰闸门写操作 |

## 最小命令清单

```bash
python "$SOP_GATE" verify        # 打版 / 收尾前必须 PASS
python "$SOP_GATE" task-verify   # 单任务验收
git status && git diff --stat    # 提交前范围核对
```

## 硬纪律（全篇通用）

- 共享 / 默认分支不 force-push；不 `--no-verify`；不提交密钥。
- 未 verify 不打 tag、不 merge、不折叠 CHANGELOG。
- 本地工作文件（plan、归档）不进 commit。
- 只按本包与源文件的既有规则执行；规则冲突时停下问主理人，不另立一套。

## If Connectors Available

If **代码托管** is connected (GitHub / GitLab / Gitee):
- 发版前核对目标分支合并状态、CI 结论与待合 PR，减少手工确认

If **文档协作** is connected (钉钉文档 / Notion / 飞书文档):
- CHANGELOG 与版本说明直接发布成发布页

If no connectors available:
- 发版信息落本地 CHANGELOG 与 tag message（默认行为，功能不打折）
