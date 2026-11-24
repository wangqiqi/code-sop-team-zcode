# 长程调度

角色：主理人执行。模拟「总规划 → 分 Sprint → 每 Sprint 规划 + 执行 → 归档 → 下一 Sprint」。

**用这个**：跨多个 Sprint 的大目标。**不是那个**：单 Sprint 内连跑（规划 + 执行一次即可）；定时保活交给系统循环能力。

## 何时进入

- 用户下达一个 Epic 级目标
- 「自动规划并做到底」「长程开发」「跨天任务」
- resume：读长程状态文件续跑
- 已有单 Sprint ACTIVE 且用户只说执行 → **不拦截**，走单 Sprint 链

## 三层收敛（硬限制）

| 层 | 上限 | 载体 |
|---|---|---|
| Epic → Sprint | ≤5 | 长程状态文件 · plan 候选表 |
| Sprint → Task | ≤5 | plan |
| Task 深度 | 仅 L2 | 禁止 Task 子 ID |

超限 → 合并抽象或拆多个 Epic，**禁止加深层级**。

## Epic 立项

1. 读项目学习层、现有 plan 候选表、用户目标。
2. 写 / 更新长程状态文件。
3. 拆 ≤5 个 Sprint（各一句 Goal + 依赖），向用户确认（选项 ≤4 项）。
4. 置 `status: active` · `active_sprint_index: 0`。

用户首句已含「自动规划并连跑」→ 视作已批准 Sprint 列表，但仍须落盘状态文件。

## Sprint 循环

对每个 Sprint 顺序执行：

| 步 | 动作 |
|---|---|
| a | 阶段 1：Goal · Done when · Out of scope |
| b | 阶段 2：TASK 表 ≤5 + 执行顺序 |
| c | handoff：解除规划态 · 标记计划已批准 · 打开自治 |
| d | `gate-check` 通过 → 实现全部 TASK（同会话连跑，不等第二次指令） |
| e | 收尾：verify · 归档 · plan 对账 · 长程 checkpoint |
| f | `active_sprint_index++`；仍有 Sprint → 回 a；否则 Epic `completed` |

Sprint 之间可选短暂休息或结束会话；跨天用 resume 或系统循环唤醒。

## checkpoint

- 长程状态文件是唯一真源：Epic 列表、当前 Sprint 序号、状态、打断原因。
- 每个 Sprint 收尾必须落一次 checkpoint，未落盘视为该 Sprint 未闭合。
- plan 与状态文件须对账：plan 无 Active、候选表已更新；Epic 全闭合置 `completed`。

## 恢复 resume

1. 先跑一次闸门自检。
2. 读长程状态文件 + plan。
3. 状态为暂停 / 达循环上限 → 向用户说明打断原因，确认后续。
4. 当前 Sprint 未完成 → 续跑（ACTIVE）。
5. 当前 Sprint 已闭合 → 对下一 Sprint 执行循环 a–f。

## 分工

| 组件 | 职责 |
|---|---|
| 长程 | Epic 外壳 · Sprint 顺序 · checkpoint · resume |
| 规划 | 单 Sprint 的 Goal / TASK / handoff |
| 执行 | TASK 实现 · verify · commit · 单 Sprint 自治链 |
| 系统循环 | 定时 / 事件唤醒；只做配合，不改其源码 |

## 决策打断点

| 类型 | 动作 |
|---|---|
| 需决策 | 暂停 Epic 链，状态置 paused 并记原因 |
| 阻塞 | 同上；用户重新规划后 resume |
| 高风险 | 必须用户确认 |
| 目标漂移 | 停 Epic，说明偏离点 |
| 发版 | 交发版官或用户明示 |

**不算决策、不停 Epic**：Sprint 内任务切换 · commit · CHANGELOG · README 门面。

## 禁止

- 绕过 `gate-check` / `task-verify` / 计划批准
- 任务运行中静默插入新 TASK 或新 Sprint
- 改动执行器停止钩子的默认行为（须单独授权）
- 把长程做成无限任务树生成器

> 来源：Super Cursor /long
