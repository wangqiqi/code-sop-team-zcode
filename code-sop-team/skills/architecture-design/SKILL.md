---
name: architecture-design
version: 1.1.0
description: Module boundaries, dependency direction, ADRs, technical-debt accounting and the data layer (schema, migration, index, backup, consistency).
name_en: Architecture Design
name_zh: 架构设计
description_en: Module boundaries, dependency direction, ADRs, technical-debt accounting and the data layer (schema, migration, index, backup, consistency).
description_zh: 边界划分、依赖方向、ADR、技术债记账与数据层（schema/迁移/索引/备份/一致性）。
user-invocable: true
argument-hint: Structure, boundary or refactoring question
argument-hint-en: Structure, boundary or refactoring question
argument-hint-zh: 结构、边界或重构问题
---

# 架构与数据设计

**判断标准只有一条：三个月后还改得动吗。** 能跑不等于结构对；跑得快也不等于能演进。

## 何时加载

| 信号 | 加载 |
|---|---|
| 新项目起步 / 空仓库 | `references/module-boundaries.md` 定骨架 |
| 跨模块改动、一次改到 3 个以上目录 | `references/module-boundaries.md` 查依赖方向是否被破坏 |
| 要新增服务 / 队列 / 缓存 / 中间件 | `references/adr-and-debt.md` 先写 ADR |
| 想说"以后再重构" | `references/adr-and-debt.md` 记账，不口头欠 |
| 加表、改字段、写迁移 | `references/data-layer.md` 全节 |
| 查询变慢、数据对不上、要不要回滚 | `references/data-layer.md` 执行计划与一致性 |

## 四份清单

| 文件 | 查什么 | 一句话判据 |
|---|---|---|
| `references/module-boundaries.md` | 边界划分四看（变化频率/数据所有权/依赖方向/可替换性）+ 依赖图 + 接口契约 + 五个反模式 | 改一处不牵连别处 |
| `references/adr-and-debt.md` | ADR 模板（**代价必写**）+ 技术债记账 + 大改造是否可分布 | 没有"代价"一节的 ADR 是宣传稿 |
| `references/data-layer.md` | schema 变更三步法、索引看执行计划、备份必验可恢复、写路径幂等 | 不可逆操作先给回滚路径 |

接口的深度审查用 `quality-checklists/references/api-contract.md`——**契约五面同步**那节是最高频事故源。

## 输出格式（回传主理人）

```
结构判断：<当前结构哪里对 / 哪里会成为瓶颈>
建议边界：<模块与依赖方向，一句话一条>
需要 ADR 的决定：<列表；每条给出代价>
数据影响：<schema/迁移/索引/备份，逐条>
技术债记账：<位置 · 欠什么 · 何时必须还>
不建议现在做的：<明确列出，防过度设计>
```

## 与其它角色的边界

| 谁 | 管什么 | 不管什么 |
|---|---|---|
| 架构师 | 结构、边界、依赖方向、ADR、演进 | 选型对比（调研员的活）、写业务代码 |
| 数据工程师 | schema、迁移、索引、备份、一致性 | 业务规则、接口形状 |
| 调研员 | 多个方案横向比，给推荐 | 定最终结构 |
| 规划师 | 把结构建议拆成 TASK | 判断结构对不对 |

**铁律**：架构建议必须带代价。只说"建议这样更好"而不说"代价是什么、什么时候会疼"的建议，一律不算结论。

> 来源：Super Cursor `scope.mdc` 的最小 diff 原则 + `single-detector` 的单一真相源 + 本专家团技术债纪律
