# 部署与运维约定

角色：主理人执行；事务官（舒井然）只读核对 env / compose / nginx 一致性，输出差异表，不擅自改。

## 何时进入

- 新增或改 `docker-compose*.yml` · `Dockerfile` · `.env.example` · nginx 配置
- 用户要求「对齐 env」「compose 归位」「nginx 反代」「补部署文档」
- 脚手架建完需要补部署面
- Sprint 候选里出现部署 / 运维类任务

## 布局与单一真源

| 面 | 真源 | 纪律 |
|---|---|---|
| compose | 仓库根 `docker-compose.yml` | 不搞 `compose/` 与根双份不同步 |
| env 模板 | 根 `.env.example` | 唯一非密钥模板；`.env` / `.env.local` 进 `.gitignore` |
| nginx | `deploy/nginx*.conf.example` 或 `docs/deploy/` | 带索引，勿散落多份无索引 copy |
| 密钥 | env / 密钥管理 | compose 内只用变量占位，禁明文 |

## env 契约

- 分段注释组织：`# --- App ---` · `# --- Database ---` · `# --- Ports ---`。
- 模板内注明 copy → `.env` / `.env.local` 的做法。
- 新增变量同步三处：`.env.example` + README 安装节 + 项目部署约定文档。

## 三联对齐

改端口 / URL / 服务名 → 同步 **compose · `.env.example` · README**；若有 OpenAPI server 一并同步。

## nginx 反代

- `upstream` 名与 compose service 名一致。
- 静态 / media 路径与仓库 `deploy/` 或文档索引一致。
- TLS、`client_max_body_size`、WebSocket 头：改一处须 grep 全仓引用。

## 部署前检查

- [ ] `verify` PASS，无 WIP
- [ ] compose / env / nginx 三联对齐
- [ ] `.env` 未进版本库，仓库内无明文密钥
- [ ] 新增部署断言已注册进 verify（见下节）
- [ ] README 部署节与实际端口 / URL 一致

## verify 注册

- 先 grep 现有 `scripts/verify*.sh` 与 `scripts/lib/`，优先扩已有脚本或抽公共库。
- 部署域 L0 断言：example 文件存在 + 关键键 grep 命中。
- 聚合脚本只加挂载行，禁止复制整段 orchestrator。
- 母版 hybrid 仓不在根 `scripts/` 新建业务 verify；目标项目按本节执行。

## 回滚

源文件未给出独立的部署回滚流程，只规定下列处置：

- verify 失败：不继续发版动作，先修代码。
- tag 打错：本地未推 → 本地删除重打；已推送 → 报告团队策略，勿擅自 force-push。
- 禁止拿无确认的 `reset --hard` / `clean -fdx` 当回滚手段。
- 部署面变更回退后须重跑 verify 再交付。

## 与脚手架 / 学习层

- 脚手架 standard+ 栈自带 `.env.example`，须对齐 env 契约；不全栈重写时至少改 exemplar 或文档指针。
- 项目特化路径（compose 文件名、nginx 实际路径、端口表）写进项目自己的部署约定文档，不写进通用母版正文。

## 禁止

- compose 里写明文密钥
- 第三次「对齐 env / compose」热修仍不立项收敛
- 母版仓根目录新建 `scripts/verify_deploy.sh`

> 来源：Super Cursor /ops-deploy
