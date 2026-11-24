---
name: ux-design
version: 1.1.0
description: Information architecture, interaction flows, six-state design, visual tokens and usability audits.
name_en: UX Design
name_zh: UX 设计
description_en: Information architecture, interaction flows, six-state design, visual tokens and usability audits.
description_zh: 信息架构、交互流程、六态设计、视觉 token 与可用性走查。
user-invocable: true
argument-hint: Page, navigation or usability problem
argument-hint-en: Page, navigation or usability problem
argument-hint-zh: 页面、导航或体验问题
---

# 交互与视觉设计

**核心判断：用户第一次用，能不能不用问人就把事办完。** 好看是副产品，不是目标。

## 何时加载

| 信号 | 加载 |
|---|---|
| 新页面 / 新流程 | `references/ia-and-flow.md`（先定层，再定结构，再定流程） |
| 用户说"不好用""找不到""乱" | 分流：导航问题走 IA，流程问题走交互，视觉问题走视觉规范 |
| Dashboard / 列表页 / 表单 | `references/six-states.md` ← **漏态=看起来完成了其实没做** |
| UI Sprint 收尾、多角色权限可见性 | `references/usability-audit.md` |
| 设计规范缺失、各页面各写一套 | `references/visual-tokens.md` |

## 四份清单

| 文件 | 查什么 | 一句话判据 |
|---|---|---|
| `references/ia-and-flow.md` | Garrett 五层定位、IA 三规则、角色入口表、交互四要素、分支点 | 一个功能一个主入口，深度 ≤3 |
| `references/six-states.md` | 首次空 / 筛选空 / 加载 / 错误 / 成功 / 无权限 + 长任务 | 六个态缺一个就是 bug |
| `references/visual-tokens.md` | 间距字号色板层级圆角、三条硬规矩 | 组件里不出现 magic number |
| `references/usability-audit.md` | 11 项走查清单，带 Blocker/High 分级 | 只隐藏按钮计 Blocker |

## 输出格式（回传主理人）

```
定位层：<IA / 交互 / 视觉 / 多层>
结构问题：<入口、分组、角色可见性，逐条>
流程缺口：<缺失的分支，逐条>
缺态：<哪几个界面缺哪几个态>
视觉问题：<token 缺失 / 一致性 / 对比度>
建议改动（按影响排序）：1… 2…
本次不做：<明确排除，防视觉层无限打磨>
```

## 与其它角色的边界

| 谁 | 管什么 | 不管什么 |
|---|---|---|
| 设计师 | 结构、流程、状态、视觉规范 | 写业务实现、定需求优先级 |
| 产品经理 | 做什么、给谁 | 界面怎么组织 |
| 审查官 | 代码是否符合设计规范 | 设计本身好不好 |
| 安全工程师 | 权限是否真的挡住 | 界面怎么提示 |

**铁律**：设计结论要能落到「具体界面 + 具体状态 + 具体值」。说"整体感觉不够清爽"不算结论，说"列表页间距从 12 统一到 16，卡片圆角从 8 收到 6"才算。

> 来源：Super Cursor `ux` / `ia` skill + `rules/execution/ux.mdc`（Garrett 分层）+ `delivery` §视觉走查
