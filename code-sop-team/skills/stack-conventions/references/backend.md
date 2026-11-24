# 后端语言约定

覆盖 Python、Go、Java。每条是硬约定，末尾是完成判据。

---

## Python

- PEP 8 + 项目 formatter（`black` / `ruff format`）；提交前跑 linter（`ruff` / `flake8`）
- 公开函数写类型标注；作为库发布则带 `py.typed`
- 用 `venv` / `uv` / 项目环境管理器；依赖锁在 `pyproject.toml` 或 lockfile
- 新代码优先 `pathlib`，不用 `os.path`
- 异步：一个应用一种 event loop 策略；所有外部调用加 timeout
- 测试用 `pytest`；慢测/DB 测标 `@pytest.mark.integration`
- 密钥走 env；**绝不提交 `.env`**
- CLI 用 argparse 时遵循：参数必填项显式、`--help` 可读、失败退出码非 0

**完成判据**：`ruff check`（或项目 lint）+ `pytest`（或项目 verify 脚本）。

## Go

- 提交前 `gofmt` / `goimports`；项目有 `staticcheck` / `golangci-lint` 就跟着跑
- **错误显式处理**，不留静默 `_`（确有理由要写注释）；用 `%w` 包装以保留上下文
- I/O、HTTP、RPC 一律带 `context.Context`，尊重取消与 deadline
- 包小、命名清晰；**不建 `util` / `common` 垃圾场**
- 接口定义在使用方，保持窄
- 并发：errgroup/channel 且所有权清晰；CI 有 `-race` 就跑
- HTTP handler：校验输入、错误映射状态码、**不给客户端栈信息**
- 测试表驱动 `_test.go`；可验收时 `go test ./...`
- 模块走 `go.mod`，版本固定有意为之；密钥只用 env

**完成判据**：`gofmt -l` 无输出 + `go vet ./...` + `go test ./...`。

## Java

- 跟随项目 formatter（Google / Sun / 团队规范），提交前跑
- 优先不可变值类型；null 安全按项目方案（`Optional` 或注解）
- 分层遵循仓库结构（Spring / 多模块）；**不出上帝类、不造循环依赖**
- 异常：checked / unchecked 与代码库保持一致；**捕获后必须记日志，不许吞**
- JDK 17+ 且团队认可时 DTO 用 record；Lombok 仅限仓库已在用
- 资源用 try-with-resources；遗留代码里显式 close 流与连接
- 测试 JUnit 5；单测与集成测分包（`src/test/java/...`）
- 构建按声明走 Maven **或** Gradle，**不擅自混用**
- 密钥走 env / vault / Spring config；凭证与 keystore 绝不入库

**完成判据**：项目 lint/format + `mvn test` 或 `gradle test`（按仓库声明）。

---

## 后端通用铁律

| 项 | 约定 |
|---|---|
| 错误处理 | 不留静默失败；包装时保留原因；对外只给友好句 + error code |
| 超时 | 所有外部调用（HTTP/DB/缓存/队列）必须设 timeout |
| 配置 | 启动时校验，非法则拒绝启动或回退安全默认并记日志 |
| 日志 | 含上下文与 trace id；**不含密钥、完整凭证、PII** |
| 迁移 | schema 变更与代码同一变更集；破坏性迁移要有回滚路径 |
| 并发 | 共享状态生命周期写清；不嵌套锁 |

## 完成判据汇总

| 栈 | 必须 |
|---|---|
| Python | lint + `pytest` |
| Go | `gofmt` + `go vet` + `go test` |
| Java | formatter + `test` |

跑不过不算完成；放行判定仍归 `sop-gate`。
