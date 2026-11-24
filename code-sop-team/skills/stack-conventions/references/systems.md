# 系统级语言约定

覆盖 Rust、C、C++。这三门语言的共同点是**错误代价高**：未定义行为、生命周期、资源泄漏不会在测试里温和地报错，而是静默破坏。所以约定偏保守。

---

## Rust

- 项目在用就跑 `cargo fmt` 与 `cargo clippy`（deny warnings）；提交前必须过
- 库内优先 `Result` + `?`；有意的 `expect`/`unwrap` 必须注释说明不变量
- 所有权：能借用就借用；`Arc`/`Mutex` 必须有清晰生命周期说明；**不嵌套锁**
- 异步：Tokio 只在二进制边界；`spawn` 配合结构化关闭；外部调用加 timeout
- 错误：按仓库选 `thiserror` / `anyhow`；API 边界映射为用户安全文案
- 公开 API 最小化；模块默认私有；破坏性变更在 CHANGELOG 标明 semver 影响
- 测试：模块内单测；`tests/` 集成测只测公开 API
- 安全：**`unsafe` 必须带注释 + 经审查**；外部输入长度必须校验
- 完成判据：`cargo fmt --check` + `cargo clippy` + `cargo test`（或项目 `scripts/`）

## C

- 目标标准按项目（C11 或既定）；构建支持时开 warnings 并视作错误
- **每次分配都检查返回值**；每个 acquire 配一个 release（内存、fd、锁）
- 错误路径显式；多步 init/teardown 且仓库已用 `goto cleanup` 时保持一致
- **不碰未定义行为**：API 边界校验长度、越界、空指针；禁止隐式截断
- 头文件：include guard 或 `#pragma once`；`.h` 只放必要声明；`.c` 里 include 自己用的
- 命名跟随项目（通常 snake_case）；文件内符号用 `static`，除非要导出
- 并发：写明线程假设；统一使用项目锁原语
- 测试：项目 runner（`make test` / `ctest` / 自有 harness）；可用时跑 valgrind / ASan
- 构建跟随 Makefile / CMake；**不手改生成产物**
- 安全：禁用无界 `strcpy` / `sprintf`；用有界拷贝；外部输入长度必须 sanitize

## C++

- 项目允许时用现代 C++（17/20）；所有权用 RAII；**新代码不用裸 `new`/`delete`**
- const 正确性；所有权显式（`unique_ptr` / `shared_ptr`）；能前向声明就前向声明
- 模板 / `constexpr` / enum 能替代宏时不用宏；头文件尽量少 include
- 跟随构建系统（CMake / Bazel / Makefile）；不手改生成的构建文件
- 异常或错误码跟随项目风格，**不静默混用**
- 重类型用移动语义；持有资源的类遵循 rule of zero/five
- 并发：优先标准库原语；写明共享状态生命周期
- 测试：`ctest` / `ninja test` / `make test`；仓库支持时开 ASan / UBSan
- 不用未定义行为走捷径；API 边界校验边界与生命周期

---

## 系统级通用铁律

| 项 | 约定 |
|---|---|
| 资源 | acquire/release 成对；用 RAII 或统一的 cleanup 路径 |
| 边界 | 所有外部输入（长度、索引、指针、枚举）在入口校验一次 |
| 并发 | 共享状态所有权与生命周期必须写在注释里 |
| 未定义行为 | 不为性能赌 UB；确有需要必须隔离 + 注释 + 审查 |
| 构建 | 跟随既有构建系统，不手改生成文件 |
| 安全 | 内存安全告警（ASan / valgrind / miri）在支持时纳入验收 |

## 完成判据汇总

| 栈 | 必须 |
|---|---|
| Rust | `cargo fmt --check` + `clippy` + `test` |
| C | warnings 清洁 + 项目 test（+ ASan/valgrind 若可用） |
| C++ | warnings 清洁 + `ctest`/`make test` |

这些是**最低线**。跑了不等于验收通过——放行仍由 `sop-gate` 的 exit code 决定。
