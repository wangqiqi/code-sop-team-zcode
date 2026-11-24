---
name: quality-checklists
version: 1.0.0
description: Review checklists for security, API contracts, test layers, debugging loops, the patch-loop stop rule, performance and refactoring protocols.
name_en: Quality Checklists
name_zh: 质量清单
description_en: Review checklists for security, API contracts, test layers, debugging loops, the patch-loop stop rule, performance and refactoring protocols.
description_zh: 安全清单、API 契约、测试分层、调试循环、补丁循环拦截、性能手册与重构协议。
user-invocable: true
argument-hint: Risk area to check: security, API, tests, performance
argument-hint-en: Risk area to check: security, API, tests, performance
argument-hint-zh: 要检查的风险面，如 安全/API/测试/性能
---

# 质量检查清单

本目录是**判断依据**，不是执行器。每份清单只回答「这一项过没过」，跑不跑绿由 `sop-gate` 说了算。

## 何时加载

| 信号 | 加载 |
|------|------|
| diff 触及 auth / 密钥 / 支付 / webhook / 上传 / 对外 API | 安全清单 |
| 改路由 / schema / DTO / 分页 / 错误码 / 前端消费字段 | API 契约清单 |
| 写测试、TDD、设计验收命令、测挂了要分层 | 测试分层 |
| 修 bug、异常行为、要找根因再改 | 调试循环 |
| **同一问题修了 ≥2 轮还没好**、想再加个判断绕过 | 补丁循环拦截 |
| 慢、卡、内存涨、首屏差 | 性能手册 |
| 重构、删死代码、拆模块 | 重构协议 |

合并前审查默认叠加安全 + 测试两份；改到接口面再叠加 API 契约。信号不清时先扫一遍，扫完再决定深查到哪一层。

**补丁循环拦截是唯一一份「叫停」清单**——其余六份判断代码对不对，它判断**现在该不该继续改**。

## 7 份清单

| 文件 | 查什么 | 主用角色 |
|------|--------|----------|
| `references/security-checklist.md` | 密钥凭证、鉴权授权、输入输出边界、支付与 webhook、依赖配置 | code-reviewer |
| `references/api-contract.md` | URL 与资源、请求响应、鉴权校验、输入边界、**契约五面同步** | code-reviewer |
| `references/test-layers.md` | 红绿重构短环、单测/集成/E2E 分层、verify 分层、长测有界、mock 原则 | code-reviewer |
| `references/patch-loop.md` | **连续失败判据**、五个高频反复区（异步进度/长任务 UI/弹窗分层/错误上下文/单一检测器）、范围纪律 | code-reviewer · tech-spiker · sprint-planner |
| `references/debug-loop.md` | 复现→假设→隔离→验证→记录、模式聚类、停止与升级判据 | tech-spiker |
| `references/perf-playbook.md` | 测量优先、常见瓶颈、输出格式 | tech-spiker |
| `references/refactor-protocol.md` | 小步可验证、最小 diff、死代码删除协议、禁止项 | code-reviewer |

## 与四道闸门的关系

清单**在闸门内**，不**代替**闸门：

| 闸门 | 命令 | 清单扮演什么 |
|------|------|-------------|
| 规划闸 | `gate-check` | 无角色。清单不参与放行判定 |
| 验收闸 | `task-verify` | 解释失败原因、指出补什么；本身不构成 PASS |
| 出口闸 | `verify` | 同上；全量绿由命令 exit code 决定 |
| 补丁循环闸 | `task-verify` 内建计数 | 提供「该不该继续修」的判据；计数与告警由脚本执行，清单只给结论标准 |

铁律：

- 清单全勾 ≠ 验收通过。判定只认 `task-verify` / `verify` 的 exit code。
- 清单出 Blocker ≠ 闸门自动 BLOCK。由审查官给「不放行」建议，主理人决定是否回流规划（Phase 1）。
- 任何清单都不得被引用为「跳过 task-verify 的理由」。

## 使用纪律

- 只勾有证据的项：每条结论带 `file:line` 或命令输出；无证据写「未核」，不打勾。
- 源里没写的不要补。清单缺项 → 标 `Decision needed` 交主理人。
- 严重度只用 Blocker / High / Medium，与审查官输出格式对齐。
- 调研员用调试 / 性能两份做只读根因定位，结论回主理人，不直接改代码。
