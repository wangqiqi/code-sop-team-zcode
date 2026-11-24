# Connectors

本插件用**品类占位符**引用外部工具：某个品类连上任意一个工具即可升级体验，没连也不影响任何技能使用。

| 品类 | 连上后能做什么 | 支持的工具 | 配置方式 |
|------|---------------|-----------|----------|
| 代码托管 | 审查阶段直接读 PR diff / 评论，把 Blocker 与 High 发回 PR；发版前核对合并状态 | GitHub、GitLab、Gitee | 在本应用「设置 → MCP」启用对应 server，或在 `~/.zcode/cli/config.json`（用户级）/ `<repo>/.zcode/config.json`（工作区级）的 `mcp.servers` 配置 |
| 项目跟踪 | 规划完成后把 TASK 同步为 issue，执行中回写状态与验收结果 | Jira、Linear、Teambition | 同上；各平台在自身开放平台生成 MCP 配置 |
| 文档协作 | 把 plan、验收报告、CHANGELOG 发布成团队可见文档 | 钉钉文档、Notion、飞书文档 | 钉钉/飞书：在 AI 能力中心生成个人 MCP 配置后粘贴；Notion：设置页一键开启 |
| 通讯协作 | 闸门 BLOCK、Sprint 收口、发版完成时推送到群 | 钉钉、飞书、Slack | 同「文档协作」对应平台的 MCP 配置页 |

## 说明

- 插件**不内置**任何 MCP 配置（没有 `.mcp.json`），装完即用；外部工具是可选增强。
- 所有技能都在技能末尾写了「If Connectors Available」分支：没有连接器时产出落本地文件与 `plan.md`，功能不打折。
- 闸门与验收证据始终以本地 `bin/sop_gate.py` 的退出码为唯一判据，**不因接了外部工具而放宽**。
