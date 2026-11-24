# 安全重构协议

## 原则

- [ ] 行为不变的重构与功能变更分 commit — **High**
- [ ] 每步后 `task-verify` / test 绿 — **Blocker**
- [ ] 范围匹配 plan 中 `REV-*` 或用户明确指定 — **High**
- [ ] 小步可验证：一步一个可回滚的变换 — **High**
- [ ] 最小 diff：只动目标范围 — **High**

## 常见动作

| 动作 | 要点 |
|------|------|
| 提取函数 / 模块 | 抽出后调用点行为不变 |
| 重命名 | 用 IDE / 工具链，不手改 |
| 去重复 | 合并后保留单一实现 |
| 缩小 public API | 未被引用的导出先按删除协议处理 |

## 死代码删除协议

删组件、Hook、API、路由前必须走完四步：

| 步 | 动作 | 判据 |
|----|------|------|
| 1 证据 | grep 生产路径：路由表、页面 import、OpenAPI / 客户端 SDK、后端 router 注册 | 生产路径无引用 |
| 2 隔离 | 区分仅测试引用 vs 生产引用 | 仅测试 → 可删，但须同删对应测试 / mock |
| 3 分轮 | 前端 UI 一轮、后端 / API 一轮 | 避免 half-clean；第二轮前出 SPIKE 清单交产品确认 |
| 4 验证 | 删后跑 verify / 全量 test | 绿 + CHANGELOG `### Removed` 一行摘要 |

- [ ] 未 grep 生产路径不得删「看起来没用」的 export — **Blocker**
- [ ] 仅测试引用者删除时同删测试 / mock，不留悬空引用 — **High**
- [ ] 前后端删除分轮进行，不一轮清完 — **High**
- [ ] 删除后 CHANGELOG 记 `### Removed` — **Medium**

## 禁止项

- [ ] 顺手改无关文件（drive-by）— **Blocker**
- [ ] 无测试的大范围重写（先回流规划 Phase 1）— **Blocker**
- [ ] 边重构边改行为 — **Blocker**
- [ ] 重构中途不跑验证就继续下一步 — **High**
- [ ] 以「清理」为名扩大 scope — **High**

> 来源：Super Cursor /refactor
