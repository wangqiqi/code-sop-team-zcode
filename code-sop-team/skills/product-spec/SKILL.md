---
name: product-spec
version: 1.1.0
description: Requirement clarification in four questions, user stories, executable acceptance criteria, MVP trade-offs and scope negotiation.
name_en: Product Spec
name_zh: 需求规格
description_en: Requirement clarification in four questions, user stories, executable acceptance criteria, MVP trade-offs and scope negotiation.
description_zh: 需求澄清四问、用户故事、验收标准可执行化、MVP 取舍与范围谈判。
user-invocable: true
argument-hint: One-line requirement or competing demands
argument-hint-en: One-line requirement or competing demands
argument-hint-zh: 一句需求描述或互相冲突的诉求
---

# 需求规格

**这份清单解决一件事：把「我想要个功能」变成「可验收的目标」。** 它不拆任务——拆任务是规划师的活。

## 何时加载

| 信号 | 加载 |
|---|---|
| 需求只有一句话，说不清给谁用 | `references/clarify.md` |
| 验收标准写成"功能正常""页面不报错" | `references/acceptance.md` ← **最高价值** |
| 不确定这次该做多少、多方诉求都要做 | `references/scope.md` |
| 需求中途加东西 | `references/scope.md` 的范围谈判一节 |
| 要产出完整需求规格回传主理人 | 本页「输出格式」 |

## 五节清单

| 文件 | 查什么 | 一句话判据 |
|---|---|---|
| `references/clarify.md` | 澄清四问（谁/什么问题/什么算解决/什么时候要）+ 用户故事写法 | 四问答不全就别排期 |
| `references/acceptance.md` | 把说法翻成**可执行命令**或 `manual:` 声明：给命令、给阈值、给路径 | 一个标准只验一件事 |
| `references/scope.md` | MoSCoW 切法 + 范围谈判三选一 | 说不出"只做一条 Must 是哪条"就是没想清 |

## 三条不可让的红线

1. **四问答不全，不替用户编答案** —— 把缺口原样交回主理人去问。编出来的需求比没有需求更贵。
2. **验收标准必须能被规划师原样写进 plan 的 Acceptance 列** —— 写不进去就是没写完。验收闸只认可执行命令与 `manual:`，描述性文字会 `fail-closed` 直接 FAIL。
3. **不替用户砍需求，也不默默加班** —— 加需求时摆出「加进来 / 换掉 / 排下一个」三选一连同代价，由用户拍板。

## 输出格式（回传主理人）

```
需求：<一句话>
谁 / 问题 / 算解决的标志 / 时间压力
用户故事：作为…我要…以便…
验收标准（可执行）：
  1. <命令 或 manual: 步骤+证据>
  2. …
Must / Should / Could / Won't
Out of scope（明确不做）
待确认缺口：<需要用户回答的，没有就写"无">
```

## 与其它角色的边界

| 谁 | 管什么 | 不管什么 |
|---|---|---|
| 产品经理（本 skill） | 做什么、给谁、什么算对、先做哪个 | 怎么实现、分几步、谁写代码 |
| 规划师 | 冻结 Goal、拆 TASK、定执行顺序、写 VERIFY | 判断需求值不值得做 |
| 架构师 | 结构怎么搭、边界在哪 | 需求优先级 |
| 审查官 | 做出来的东西质量如何 | 该不该做这个需求 |

> 来源：Super Cursor 规划流程的 Goal 冻结纪律 + `delivery` 七维验收

## If Connectors Available

If **项目跟踪** is connected (Jira / Linear / Teambition):
- 需求规格与用户故事同步为 issue，验收标准写进 issue 的完成条件

If **文档协作** is connected (钉钉文档 / Notion / 飞书文档):
- 需求规格发布成 PRD 文档供干系人评审

If no connectors available:
- 规格输出为本地 Markdown，验收标准原文交规划师落表（默认行为）
