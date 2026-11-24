---
name: stack-conventions
version: 1.0.0
description: Coding conventions per language and framework: TS/JS/ESLint, React/Vue/Svelte/Next, Python/Go/Java, Rust/C/C++, with completion criteria for each stack.
name_en: Stack Conventions
name_zh: 技术栈约定
description_en: Coding conventions per language and framework: TS/JS/ESLint, React/Vue/Svelte/Next, Python/Go/Java, Rust/C/C++, with completion criteria for each stack.
description_zh: 按语言与框架给出编码约定：TS/JS/ESLint、React/Vue/Svelte/Next、Python/Go/Java、Rust/C/C++，含各栈完成判据。
user-invocable: true
argument-hint: Language, framework or the files to check
argument-hint-en: Language, framework or the files to check
argument-hint-zh: 语言/框架或待检查的文件
---

# 技术栈约定

**这份 skill 只回答「这门语言的代码该长什么样」**，不判断验收是否通过——放行永远由 `sop-gate` 决定。

## 怎么用

1. 先看 diff 或待改文件涉及哪些后缀 / 框架，按下面路由表定位。
2. 只加载命中的那份 reference，不要一次全读。
3. 「完成判据」是**最低线**：不属于它的检查可以不做，属于它的不许跳过。

| 命中的文件 | 加载 |
|---|---|
| `.ts` `.tsx` `.js` `.jsx` `.mjs` `.cjs` · `.eslintrc*` `eslint.config.*` · `components/` `hooks/` `pages/` · `.vue` · `.svelte` · `next.config.*` `app/` `middleware.ts` | `references/web-frontend.md` |
| `.py` `pyproject.toml` `requirements*.txt` · `.go` `go.mod` · `.java` `pom.xml` `build.gradle*` | `references/backend.md` |
| `.rs` `Cargo.toml` · `.c` `.cc` `.cpp` `.cxx` `.h` `.hpp` · `CMakeLists.txt` | `references/systems.md` |

混栈项目（如 TS 前端 + Go 后端）**两份都加载**，各查各的。

## 通用铁律（不分语言）

- **跟随仓库既有约定优先于本文档**。本文给的是默认值；仓库里已有 formatter / linter / 目录约定时，一律以仓库为准，不得反向改造。
- **提交前必须跑该栈的检查**（lint / type-check / format）。跑不过不算任务完成。
- **不新增第二套工具链**。已有 runner、formatter、build 系统时不引入同类竞品。
- **不做顺手格式化**。全库格式化属于独立 TASK，混在功能 PR 里会淹没真实 diff。
- **密钥一律走环境变量**，任何语言的源码里都不许出现凭证。

## 与其它清单的关系

| 场景 | 谁说了算 |
|---|---|
| 代码风格、类型、并发、错误处理约定 | 本 skill |
| 安全 / 支付 / 鉴权审查 | `quality-checklists` → `security-checklist.md` |
| API 契约与输入边界 | `quality-checklists` → `api-contract.md` |
| 反复修不好、该不该继续打补丁 | `quality-checklists` → `patch-loop.md` |
| 测试怎么分层 | `quality-checklists` → `test-layers.md` |
| 验收是否通过 | `sop-gate`（exit code 唯一判据） |

> 来源：Super Cursor `rules/tech/*.mdc`（13 份语言规范）
