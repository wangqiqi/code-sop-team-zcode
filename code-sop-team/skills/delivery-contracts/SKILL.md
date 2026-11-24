---
name: delivery-contracts
version: 1.0.0
description: Seven-dimension delivery acceptance, test-report contract and user-manual contract for closing a sprint or a release.
name_en: Delivery Contracts
name_zh: 交付契约
description_en: Seven-dimension delivery acceptance, test-report contract and user-manual contract for closing a sprint or a release.
description_zh: 交付七维验收、测试报告契约与使用说明书契约，用于 Sprint 收口与发版前交接。
user-invocable: true
argument-hint: Sprint or version to deliver
argument-hint-en: Sprint or version to deliver
argument-hint-zh: 要交付的 Sprint 或版本
---

# 交付契约

**用这个**：功能已绿、上线前的七维走查，以及测试报告、使用说明书这两份可单独发布文档的契约化产出。
**不是那个**：自动化脚本红/绿 → verify 类 skill；导航与结构规划 → ia/ux；跑全量套件 → test / run。

## 何时进入

| 触发 | 动作 |
|------|------|
| task-verify / verify 已绿 | 进入七维走查，不重复跑套件 |
| Sprint Done when 含「delivery 无 Blocker」 | 收尾前完整走一遍 |
| `/release`（merge / PR）前 | UI/功能 Sprint 建议先走查 |
| 用户说「上线前检查」「生产就绪」「交付验收」 | 立即进入 |

进入前先读项目特化路径（design token、i18n 库、OpenAPI 位置），并扫 Sprint Goal / Done when。

## 由谁执行

| 角色 | 职责 |
|------|------|
| release-engineer | 主责：定七维结论与严重度，守 Blocker 门禁，出 release 前判定 |
| engineering-steward | 出草稿：按清单逐项取证，起草报告与手册骨架 |
| review agent | `REV-*` 含交付范围时只读复核，复用同一份清单 |

## 七维与两份契约

七维清单是**验收**，两份契约是**可发布产物**；先清单清 Blocker，再按契约成稿。

| 维度 | 判据落点 |
|------|----------|
| 1 视觉一致性 | token、字号、间距、响应式/暗色 |
| 2 i18n 与文案 | locale 真源、术语统一、锚点同步 |
| 3 文档 ↔ 实现 | 双向一致，冲突上报 |
| 4 API 与数据 | 字段、错误码、鉴权、Mock 一致 |
| 5 组件与交互 | 状态完整，无「待办」类注释上生产 |
| 6 可维护性 | 分层正确，最小 diff |
| 7 生产就绪 | 无 debug/mock 残留，日志无 PII |

| 契约 | 前置 | 产物 |
|------|------|------|
| Report Contract | verify 已跑或即将跑 | 测试报告，落 contract `doc_path` |
| Manual Contract | verify 全绿 | 使用说明书 + 实机配图 |

细目：`references/delivery-checklist.md` · `test-report-contract.md` · `user-manual-contract.md`。

## 不通过怎么处理

| 严重度 | 处理 |
|--------|------|
| Blocker | 不可 merge/上线；修复或用户书面接受风险 |
| High | 本 Sprint 内修 |
| Medium | 可开 issue，不挡 release |
| Low | 风格 / nit |

- 每条一行：`严重度 · file:line · 发现 · 建议`。
- 文档与实现冲突：标 `Decision needed`（文档说法 · 实现现状 · 建议 · 等你决策），不擅自改 spec。
- 某维跳过（如单语产品）须在报告中写明理由。
- 契约类产物为自动生成，禁止手写，保留文件头生成标记。

## If Connectors Available

If **文档协作** is connected (钉钉文档 / Notion / 飞书文档):
- 验收清单、测试报告与使用说明书直接发布成团队可见文档，不必手工导出

If **项目跟踪** is connected (Jira / Linear / Teambition):
- 把交付项与遗留问题同步为 issue 并回写验收结论

If no connectors available:
- 产出落本地 Markdown 文件并在会话里汇报（默认行为，功能不打折）
