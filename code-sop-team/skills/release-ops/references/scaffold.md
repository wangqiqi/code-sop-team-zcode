# 脚手架

角色：主理人主导，**须用户确认后再创建**；事务官可先做只读环境核对。任意模式都先沟通再动手。

## 闸门

- 空仓库（检测为 empty）：可在无 plan 时直接走脚手架流程。
- 已有代码：必须先审计 + 提问确认，默认 `--dry-run`，**禁止静默覆盖**。

## 流程 · 空项目

**1 检测** —— 确认仓库状态与可用模板列表。

```bash
./.cursor/bin/scaffold.sh detect
./.cursor/bin/scaffold.sh list
```

**2 选型确认**（可多轮，至少确认技术栈）：

| 项 | 选项 |
|---|---|
| 项目类型 | frontend · backend · systems |
| 技术栈 | react-vite-ts · vue-vite-ts · nextjs-ts · go-api · rust-axum · python-fastapi · cpp-cmake |
| Go 模块路径 | 默认 `example.com/app`，问用户是否替换 |
| 包管理器 | npm / pnpm（前端）；venv（Python） |
| 可选附加包 | 用户手册骨架 / 测试报告骨架，默认不加 |

**3 预览** —— 用户确认前必须做，并用表格列出将 CREATE / SKIP 的文件，说明 post_apply 与 verify：

```bash
./.cursor/bin/scaffold.sh info <id>
./.cursor/bin/scaffold.sh apply <id> --dry-run
```

**4 创建** —— 用户明确说「确认 / 创建 / apply」后才 apply；附加包单独 apply-bundle，不改默认文件集。

**5 收尾**（建议，不自动 commit）：

- 执行 manifest 中的 post_apply（依赖安装、mod tidy 等）
- 跑 `./scripts/verify.sh` 或登记为项目默认验收命令；复制 plan 模板拆首个 Sprint（plan 不提交）
- 需要时补 `docs/specs/` 规格骨架，并把栈与目录约定写进项目学习层

## 目录骨架（standard+）

| 内容 | 说明 |
|---|---|
| lint / test / verify 脚本 + CI + README | `test.sh` 开发中快速回归；`verify.sh` 任务 / Sprint 全量验收；CI 第一天接上 |
| `tests/README.md` | 测试目录说明 |
| `.env.example` | 对齐部署 env 契约 |

共享层先铺公共骨架，再由栈内同名文件覆盖，新仓从第一天就是分层结构。

## 流程 · 已有项目

1. `detect` + `audit`，不直接 apply。
2. 审计三维度输出表格：

| 维度 | 看什么 |
|---|---|
| 结构 | 目录 / module 边界、入口、配置散落 |
| 依赖 | lockfile、audit 结果、过时 major |
| 质量 | lint / test / verify 脚本、CI、README、plan |

3. 提问三选一：全量脚手架 / 只补 verify 脚本 / 只给建议。
4. 若补文件：`--dry-run` → 确认 → apply；无 `--force` 除非用户明确要求覆盖，收尾对齐技术栈规则与项目学习层。

## 与规划 / 执行

- 空仓库先搭架：确认 → apply → 再进规划；规划阶段纳入则在 Sprint 加一条初始化任务，验收为 apply + verify。
- 仅建议：先做选型调研，结论归档后再立任务。
- 执行阶段跑脚手架任务时，仍须 `gate-check` 通过。

## 禁止

- 未确认就 apply（尤其已有代码的仓库）
- 默认 `--force` 覆盖用户文件
- 把项目特化路径写进通用模板（应写进项目学习层或本地规则）

> 来源：Super Cursor /scaffold
