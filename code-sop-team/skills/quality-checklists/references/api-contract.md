# API 契约清单

审查 REST / GraphQL / RPC 接口设计，以及**契约变更是否同步到位**。每条只勾有证据的项。

输出格式：严重度 · 位置（`file:line`）· 问题 · 修复建议。

## 触发时机

diff 触及下列任一信号，本单强制全扫：

| 信号 | 例 |
|------|-----|
| 新增 / 修改路由 | `routes/`、`handlers/`、`controllers/`、`app/api/` |
| schema / DTO 变更 | `schemas/`、`types/`、`*.proto`、`openapi*`、`swagger*` |
| 前端消费的字段变了 | API client、`useQuery` 参数、表格列 |
| 分页 / 排序 / 筛选参数变更 | `limit`、`cursor`、`offset`、`order_by` |
| 错误码 / 响应信封变更 | 全局 error handler、`detail`、`error_code` |

## 一、URL 与资源

- [ ] 资源名词复数、小写、kebab-case（`/users`，非 `/getUsers`）— **High**
- [ ] 嵌套 ≤2 层；更深改 query 或独立资源 — **Medium**
- [ ] 版本策略全项目统一（`/v1/` 或 header，不混用）— **High**
- [ ] 幂等写操作语义正确：PUT/DELETE 幂等，POST 非幂等 — **High**
- [ ] 动作型端点确有理由（非 CRUD 能表达）时才用动词路径 — **Medium**

## 二、请求与响应

- [ ] 稳定 error code / error type，非仅自由文本 message — **High**
- [ ] HTTP 状态码语义正确：401 未认证 vs 403 无权限；404 vs 410 — **High**
- [ ] 分页风格唯一（cursor **或** offset，不混用），列表信封结构一致 — **High**
- [ ] 分页 `limit` 有上限，禁止无界拉取 — **Blocker**
- [ ] 日期时间 ISO-8601 带时区；枚举取值与 OpenAPI schema 一致 — **High**
- [ ] 响应字段命名风格全项目统一（camelCase / snake_case 二选一）— **Medium**
- [ ] 敏感字段不在 list 接口过度暴露（手机号、身份证、内部 ID）— **High**
- [ ] 空值语义明确：missing vs null vs 空数组，前端能区分 — **Medium**

## 三、鉴权与校验

- [ ] 每个写路径都有 auth，非仅前端隐藏按钮 — **Blocker**
- [ ] 资源 ID 来自 URL / body 时校验归属（防 IDOR）— **Blocker**
- [ ] 输入校验：类型、长度、枚举、注入面 — **High**
- [ ] 默认 deny：未显式授权的端点/能力关闭 — **High**
- [ ] 公开端点考虑 rate limit 与体量限制 — **High**
- [ ] 调试 / 内部端点不在生产路由中暴露 — **High**

## 四、输入边界与安全默认

数值与枚举是最高频事故源，逐项核：

- [ ] 数值参数有文档化上下限（百分比、偏移、速率、`limit`、超时），越界 **clamp 或 4xx**，禁止静默用脏值 — **High**
- [ ] 枚举 / 模式字段走白名单，未知值**拒绝**或回退到文档化默认 — **High**
- [ ] 配置类输入非法时回退安全默认**且可观测**（日志/指标），禁止半初始化状态对外服务 — **High**
- [ ] 敏感能力（插件加载、远程代码、宽 CORS、自动发现入网）默认关，官方/签名白名单才启用 — **High**
- [ ] 破坏性导入 / 覆盖有 dry-run 或预览 + 二次确认 — **Medium**

## 五、契约同步（最容易漏）

一次逻辑变更必须**同一个 PR / 同一轮改动**内完成：

| 面 | 要改什么 |
|---|---|
| Server | route/handler + schema/DTO + 必要时 migration |
| Client | types、API client/wrapper、消费该字段的 UI |
| Mocks / fixtures | 默认值与 enum 与生产 schema 一致 |
| OpenAPI / spec | 与实现同 PR 更新 |
| CHANGELOG | 用户可见的契约变更必须记录 |

- [ ] 上述五面已同步，无「后端改了前端没改」的半截状态 — **Blocker**
- [ ] 删字段/改语义属 breaking，已说明迁移路径或版本隔离 — **Blocker**
- [ ] mock / fixture 与真实 schema 一致（否则测试假绿）— **High**

## 判定

| 结论 | 条件 |
|------|------|
| 不通过 | 任一 **Blocker** 未清 |
| 整改后合并 | 仅 High / Medium，且已列明修复项 |
| 可合并 | 全项有证据通过 |

- 每条结论带 `file:line`；无证据标「未核」，不得打勾。
- 契约同步项若只改了一半，一律计 **Blocker**——这是线上事故的第一来源。
- 本清单是判断依据，不替代 `task-verify` 放行。

> 来源：Super Cursor /api · `rules/execution/api.mdc` · `rules/execution/input-bounds.mdc`
