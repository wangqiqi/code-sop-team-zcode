# 调试循环清单

铁律：**无根因调查，不提修复。** 无复现、无假设的盲改视为失败；symptomatic patch 计为失败。

结论须含 `file:line` 与可复现步骤。

## 五步循环

| 步 | 动作 | 完成标准 |
|----|------|----------|
| 1 复现 | 固定步骤 / 最小用例；读完整报错与栈 | 稳定触发，或明确「不可复现 → 先采证」 |
| 2 假设 | 1～3 条可证伪原因（含近期变更 / 环境） | 写下假设再动手，不边猜边改 |
| 3 隔离 | 缩小到单层 / 单文件 | 证据指向失败边界 |
| 4 验证 | 最小 diff + `task-verify` / 项目 test | 绿且回归不过度 |
| 5 记录 | 用户可见 → CHANGELOG `### Fixed`；流程缺口 → learn | 可审计 |

- [ ] 复现步骤编号，他人可跟做 — **High**
- [ ] 一条假设一次证伪，不同时押多个 — **High**
- [ ] 跨组件（API↔DB、CI↔脚本）先在边界打诊断日志，定位断裂层再深入 — **High**
- [ ] 不在多处同时猜改 — **High**
- [ ] 修复后跑回归，不只跑新用例 — **High**
- [ ] 区分 bug 与预期变更；后者走规划而非 hotfix — **High**

## 隔离法

- [ ] 最小复现或补失败测试 — **High**
- [ ] 注释 / 禁用可疑块（先备份或 stash）— **Medium**
- [ ] 跑 `task-verify` / 项目 test 对比前后 — **High**
- [ ] 二分缩小范围，不靠直觉定位 — **Medium**

## 模式聚类

- [ ] 同类报错一批修，同根因不打多个补丁 — **High**
- [ ] 先区分环境 vs 代码（config、版本、路径）— **High**

### 路径型资源 · 健康三角

适用：Unix socket、PID 文件、锁文件、命名管道路径。

| 视角 | 检查什么 |
|------|----------|
| 客户端路径 | `test -S path` / `stat` — 文件系统上是否存在 |
| 系统层 | `ss -xl` / `lsof` — 内核是否仍有 listener |
| 进程内 | 应用 `/health` 或内存 handle — 是否自认 healthy |

- [ ] 三个视角都查，不只信单一绿灯 — **High**
- [ ] 三者不一致时按「路径可达 + 失效 stale 缓存」两条同时修 — **High**
- [ ] 不以纯 HTTP `/health` 返回 200 收工 — **High**

### Stale 单例 / 连接缓存

- [ ] 连接类全局缓存硬失败（`ENOENT` / `ECONNREFUSED`）后 invalidate 并重试 — **High**
- [ ] 禁止无限复用 stale 句柄 — **High**
- [ ] 优先读指针文件 / 权威配置，而非进程启动时注入的旧 env — **Medium**

### Dev 反代 · 多传输路径

- [ ] 枚举所有出站路径：主线程 fetch shim、XHR、Web Worker、WebSocket — **High**
- [ ] Worker 内请求不经过 HTML 注入的 fetch 补丁，须单独验证 — **High**
- [ ] 专用 rewrite（如 `/api/uploads`、`/api/ws`）排在泛 `/api` 之前 — **Medium**
- [ ] iframe / 子应用路径与主站 API 分流分别验证 — **Medium**

## 停止与升级

| 症状 | 判据 |
|------|------|
| 绿测后又挂 / 补丁叠补丁 | 停止扩 diff，回第 1 步复现，列出已改文件与仍失败断言 |
| 同命令第 3 次仍失败 | 打印 cwd、实际命令、exit code，对照 Escalation |
| 自修 2 轮仍失败 | plan 标 `⚠️`，回流规划（Phase 1） |
| 同症状 ≥2 已发布 patch | 禁止第三个 symptomatic hotfix，走 Follow-up / SPIKE |

- [ ] 任一症状出现即停手，不自造第三轮「碰运气」修复 — **Blocker**
- [ ] 升级时附：已改文件清单、仍失败断言、已证伪的假设 — **High**
- [ ] 同时改多模块碰运气属禁止动作 — **Blocker**

## 记录

- [ ] 用户可见修复进 CHANGELOG `### Fixed` — **Medium**
- [ ] 流程 / 约定缺口提议 learn，不自动改母版规则 — **Medium**
- [ ] 信息不足时标 `Decision needed`，并列出缺什么 — **Medium**

> 来源：Super Cursor /debug
