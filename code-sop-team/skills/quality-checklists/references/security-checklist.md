# 安全清单

合并前按单核查。每条只勾有证据的项，严重度标在行尾。

输出格式：严重度 · 位置（`file:line`）· 问题 · 修复建议。

## 触发时机

diff 出现下列任一信号，本单强制全扫（并视情况叠加 API 审查）：

| 信号 | 例 |
|------|-----|
| 鉴权 / 会话变更 | login、JWT、RBAC、OAuth |
| 用户输入面扩大 | 新表单、上传、搜索、admin 工具 |
| 密钥 / 配置 | `.env`、CI secret、连接串 |
| 支付 / 结账 / 钱包 | Stripe、支付宝、订单、退款、余额 |
| Webhook / 回调 | 支付通知、第三方事件、签名校验 |
| 对外 API / 开放端点 | 新 route、GraphQL、公开 webhook URL |

无上述信号，也须过「密钥与凭证」「依赖与配置」两节。

## 密钥与凭证

- [ ] 无硬编码 API key、token、密码、私钥 — **Blocker**
- [ ] `.env` / credentials 在 `.gitignore` 且未 staged — **Blocker**
- [ ] 日志与错误信息不泄露密钥或完整 connection string — **High**
- [ ] CI / 脚本用 secret 注入，非明文 — **High**

## 鉴权与授权

- [ ] 写 / 删 / 管理路径有 auth 检查，非仅 UI 隐藏 — **Blocker**
- [ ] 资源 ID 来自 URL / body 时校验归属（防 IDOR）— **Blocker**
- [ ] 默认 deny；admin 路径单独守卫 — **High**
- [ ] Session / JWT 过期与吊销策略合理 — **High**
- [ ] 输入面扩大时复核既有守卫是否被绕过 — **Medium**

## 输入与输出

- [ ] 用户输入校验：类型、长度、enum、SQL / 命令注入面 — **High**
- [ ] 数值有上下限（百分比、偏移、速率、分页 limit、超时），越界夹紧或 4xx — **High**
- [ ] 枚举 / 模式白名单：只接受已知字面量，未知值拒绝或回退文档化默认 — **High**
- [ ] 敏感能力未显式配置则拒绝（deny-by-default）— **High**
- [ ] 配置非法时回退安全默认且可观测，无半初始化状态对外服务 — **High**
- [ ] 文件上传：类型 / 大小限制；存储路径不可遍历 — **High**
- [ ] 响应不含多余 PII；错误信息不暴露栈 / 内部路径 — **Medium**
- [ ] 破坏性导入 / 覆盖有 dry-run 或预览 + 二次确认 — **Medium**

## 支付与 webhook

diff 含支付、webhook、结账、退款、钱包、订单金额时，本节整节必扫：

- [ ] 金额 / 币种 / 数量有上下限与类型校验；服务端以权威价为准，不信客户端金额 — **Blocker**
- [ ] 支付与退款幂等（idempotency key / 去重表），防重复扣款 — **Blocker**
- [ ] Webhook 验签（HMAC / 公钥），拒绝未签名或过期时间戳 — **Blocker**
- [ ] 不记录完整卡号 / CVV；PCI 范围内数据不落日志 — **Blocker**
- [ ] 防重放：nonce / 事件 ID 去重 — **High**
- [ ] Webhook 端点默认非公开或限 IP / 密钥 — **High**
- [ ] 生产与沙箱密钥分离 — **High**
- [ ] 异步回调失败有重试与对账 / 人工兜底路径 — **High**
- [ ] 敏感交易有 audit log（谁 · 何时 · 何订单），日志不含完整 PAN / token — **Medium**

## 依赖与配置

- [ ] 无已知高危依赖：跑 `npm audit` / `pip audit` / `cargo audit` / Dependabot — **High**
- [ ] 已知 Critical / High 未缓解不得合并（或在 PR 记录已接受风险）— **High**
- [ ] 授权口径：直接依赖与 vendor 为宽松许可，传递树无未接受的 GPL / AGPL — **High**
- [ ] vendor / submodule 含 LICENSE + 溯源说明 — **Medium**
- [ ] 依赖升级 PR 注明 breaking 与回滚路径 — **Medium**
- [ ] CORS、CSP、安全 header 符合部署环境 — **High**
- [ ] 生产配置：debug / verbose 默认关闭，TLS 开启，IAM / DB 账号最小权限 — **High**
- [ ] 扩展宿主（若有）：能力白名单，默认不加载未允许项 — **High**

## 判定

| 结论 | 条件 |
|------|------|
| 不通过 | 存在任一 **Blocker** 未清 |
| 整改后合并 | 仅 High / Medium，且已列明修复项 |
| 可合并 | 全项有证据通过 |

- 每条结论带 `file:line`；无证据的项标「未核」，不得打勾。
- Blocker / High 未清 → 明确建议「不放行」，不因客气放水。
- 本清单是判断依据，不替代 `task-verify` 放行。

> 来源：Super Cursor /security
