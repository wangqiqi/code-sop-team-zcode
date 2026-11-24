# 前端与 Web 生态约定

覆盖 TypeScript、JavaScript、ESLint、React、Vue、Svelte、Next.js。每条都是实现时的硬约定，末尾是完成判据。

---

## TypeScript

- 优先 strict（`strict`、`noUncheckedIndexedAccess`，项目已开则不得关掉）
- **不用 `any`**：边界用 `unknown` + 收窄；确实不可避免的有界 `any` 必须写注释说明原因
- 公开 API 与导出函数写**显式返回类型**
- 优先**可辨识联合 + 类型守卫**，而非松散 string 联合
- API 演进用工具类型（`Pick` / `Omit` / `Partial`）；深层泛型必须起别名
- 优先 `async/await`；在边界统一处理错误；应用代码不留 floating promise
- 源码无密钥；项目若用 zod/valibot 则在启动时校验 env
- 遵循仓库 eslint/prettier；**标完成前跑 `type-check` 与 `lint`**
- 测试与源码同目录（`*.test.ts` / `__tests__`）；**在 I/O 边界 mock，不 mock 内部实现**
- 优先 type-only import；仓库若无 barrel 约定，不新增影响 tree-shaking 的桶文件

## JavaScript（非 TS）

- 模块内 strict；项目允许则统一 ESM（`import`/`export`）
- 不在 TS 迁移范围内时，公开 API 写 JSDoc 类型
- 优先 `const`/`let`；无隐式全局；**所有 promise rejection 都要处理**
- 源码无密钥；启动时校验 env
- 遵循 eslint/prettier；提交前跑 lint
- 测试与源码同目录；**一个仓库只保留一个 runner**
- Node 脚本：需要可执行才加 shebang；CLI 参数解析在仓库内保持同一套（commander 或 yargs，不混用）

## ESLint

- 跟随项目配置形态（flat `eslint.config.*` 或 legacy `.eslintrc`），**不无理由 fork 规则**
- UI/API 任务标完成前跑 lint（`npm run lint` 或项目脚本）
- 自动可修的先修；**任何 suppression 必须带注释 + 关联 issue**
- 不新增未使用变量/导入；import 顺序跟随仓库插件
- 引号/分号等风格照配置走，**不在混合 PR 里打风格战**
- TS 项目已用 `@typescript-eslint` 时，类型感知规则一并启用
- 脚手架提供 CI 时，CI 的 lint 命令必须与本地一致

---

## React

- 新代码用函数组件 + hooks；类组件仅限遗留维护
- 组件保持小；共享状态与副作用抽成自定义 hook
- Props 必须类型化；深层透传改用 context 或项目状态方案
- 状态就近放置，只有多消费者时才提升；**不保留可推导的冗余 state**
- `useEffect`：依赖正确、清理订阅与定时器；能用手写事件处理器就别用 effect 同步
- 性能：**只在测出问题或长列表时**才 memo；列表 key 稳定；大页面路由懒加载
- 路由/功能壳层加 Error Boundary，给用户安全兜底文案
- 样式走 CSS Modules / Tailwind / 项目约定，**不新增一次性全局样式**
- 测试用 React Testing Library，按角色与可访问性查询，**不测实现细节**
- 默认组合：Vitest + RTL
- 完成判据：`type-check` + `lint` + `build`（或项目 verify 脚本）

## Vue

- 新组件用 Composition API（`<script setup>`）；Options API 仅限遗留
- `defineProps` / `defineEmits` 写类型；**绝不直接改 props**
- 共享逻辑抽 composable；SFC 只负责模板与接线
- 响应式：优先 `ref`/`computed` 的可读性；`computed` 够用时不上 deep watch
- 跨路由状态用 Pinia 或项目 store；**新代码不引入全局事件总线**
- 对齐设计 token / CSS 约定；scoped 样式或项目工具类体系
- 测试用 Vitest + Vue Test Utils（若已有），测用户可见行为
- 异步：UI 处理 loading/error；用 fetch 时组件卸载要取消在途请求
- 完成判据：`type-check` + `lint` + `build`

## Svelte 5 / SvelteKit

- **优先 runes**，不与 Svelte 4 响应式语法混用
- `$props()` · `$state()` · `$derived()` · `$effect()`
- 事件用 DOM 属性（`onclick`），非 `on:click`
- 部分 slot 模式改 Snippets / `{@render}`
- SvelteKit：`+page.server.ts` / `+layout.server.ts` 做数据加载，表单用 actions
- `load` 与 `actions` 类型安全；错误用 `error()` / `fail()`
- 环境变量走 `$env/static/private` · `$env/static/public`
- 完成判据：`npm run check` / `svelte-check`（若配置）+ 测试。注意 `svelte-check` 只查类型与模板，**不能替代测试**

## Next.js（App Router）

- 新路由用 `app/`；默认 Server Components，**确实需要才 `"use client"`**
- 路由段就近放 `loading.tsx` / `error.tsx`，给 UX 边界
- env：`NEXT_PUBLIC_*` 才进浏览器；密钥仅服务端
- 数据允许时优先 static/ISR，revalidate 秒数写在代码注释里
- `fetch` 缓存选项**显式**（`force-cache` / `no-store` / `revalidate`），不靠默认值制造幽灵旧数据
- 慢段用 streaming + Suspense，不阻塞整页
- 图片用 `next/image` 并给 sizes；字体用 `next/font` 降低布局抖动
- 在预发环境看 LCP/CLS/INP；首屏以下的 client component 懒加载
- API 路由放 `app/api/`，校验输入，错误映射为稳定 JSON

### Next.js 鉴权（用 Supabase 时）

- 服务端用 `getUser()` 校验 session，**不可**仅用 `getSession()` 作授权依据（cookie 可伪造）
- RLS 默认开启；service role key **仅服务端**，绝不进 `NEXT_PUBLIC_*`
- 支付密钥仅服务端 env；webhook 必须验签
- middleware 保护的路由与 redirect 逻辑要与 RLS 一致

- 完成判据：`lint` + `type-check` + `test` + `build`（项目有 Playwright 配置时再跑 E2E）

---

## 前端通用完成判据

| 栈 | 标完成前必须跑 |
|---|---|
| TS / JS | `lint` · `type-check`（`tsc --noEmit` 或项目脚本） |
| React / Vue | 上述 + `build` + 相关测试 |
| Svelte | `svelte-check` + 测试 |
| Next.js | `lint` · `type-check` · `test` · `build` |

跑不过就不算完成——这是 `task-verify` 的前置，不是替代。
