# 测试分层清单

验收命令优先取 plan 验收列；无列则用项目 `./scripts/test.sh` 或栈默认。

## TDD 短环

| 步 | 动作 | 完成标准 |
|----|------|----------|
| 1 红 | 写失败测试（或复现用例）并实际运行 | 确认失败，失败原因对得上假设 |
| 2 绿 | 最小实现使测试通过 | 只满足该断言，不扩 scope |
| 3 重构 | 在绿测保护下整理 | 测仍绿，行为不变 |

- [ ] 先跑红测，再写实现 — **High**
- [ ] 绿阶段只做最小实现，不顺手加功能 — **Medium**
- [ ] 重构阶段不引入断言之外的行为 — **Medium**
- [ ] 红测未转绿不得标 ✅ task — **Blocker**

## 分层

| 类型 | 何时写 | 边界 |
|------|--------|------|
| 单元 | 纯逻辑、utils、hooks | 不真连 DB / HTTP |
| 集成 | API、DB、模块边界 | 可连真依赖，范围限单模块 |
| E2E | 关键用户路径 | 测行为与可见结果，非 DOM 实现细节 |

- [ ] 新功能域优先补 L1 进 `task-verify`；全量 E2E 归 Sprint Done / nightly — **High**
- [ ] 客户端小改只跑定向单文件测，不为小改跑全量 L2 / L3 — **Medium**
- [ ] 服务端 P0 用 L2-core 子集或单文件集成测 — **High**
- [ ] 同层不混两套 runner（如 Vitest + Jest 并存）— **Medium**

## verify 分层

| 层 | 归属 | 何时跑 |
|----|------|--------|
| L1 | `task-verify` | 每任务收尾 |
| L2 | 子集 / 集成 | 服务端 P0 |
| L3 | Sprint Done / nightly | 收尾与打版 |

- [ ] 红测停在 L1 即可标 🔧，不为 ✅ 跳过 L1 直跑 L3 — **High**
- [ ] 未触达慢层时不得用全量集成「消 flake」— **High**
- [ ] 新 slice 脚本须入注册表；CI 设 `VERIFY_REGISTRY_STRICT=1` — **Medium**

## 长测有界运行

- [ ] 有界超时：wall timeout + per-case timeout — **Blocker**
- [ ] 取消长命令用 `kill -<pgid>`，不只 `kill <pid>` — **High**
- [ ] 入口有孤儿回收，清理陈旧测试进程 — **High**
- [ ] 用户喊停后不再开第二轮同全量门禁 — **High**
- [ ] 并行 verify / 装依赖 / slice 注册共用锁，陈旧 lock 有清理 — **Medium**

## mock 原则

| 手法 | 何时用 | 要点 |
|------|--------|------|
| Factory | 实体 / DTO 构造重复、字段组合多 | 默认值 + 每测只覆盖差异字段 |
| Test double | 外部 I/O、时钟、随机、网络 | 优先接口边界注入 |
| Mock | 断言「被调用方式」或隔离慢依赖 | mock 行为，不 mock 实现细节 |
| Stub | 只需固定返回值、不关心调用次数 | 比 mock 简单就用 stub / fixture |

- [ ] 一个测试一个主要 mock 面 — **Medium**
- [ ] 不过度 mock 被测对象自身（测实现而非契约时换集成测）— **High**
- [ ] 异步断言 await；假定时器用栈等价物 — **Medium**
- [ ] 单测不真连 DB / HTTP（集成层除外）— **High**

## 测试纪律

- [ ] Arrange 用 factory · Act 一行 · Assert 聚焦一个行为 — **Medium**
- [ ] 测行为与契约，非私有函数名 / DOM 选择器 — **High**
- [ ] 一断言一意图；表驱动优于复制粘贴 case — **Medium**
- [ ] 新 bug 先补回归测，再修实现 — **High**
- [ ] E2E 用稳定 `data-testid` 或 role 选择器 — **Medium**
- [ ] 动态 SPA 先 `networkidle` 再断言；不测 flaky 时序 — **Medium**
- [ ] 测例自建临时目录在 `afterAll` / `try/finally` 删除 — **Medium**

> 来源：Super Cursor /test
