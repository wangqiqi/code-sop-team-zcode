# 使用说明书契约（Manual Contract）

定位：生成**可单独发布**的操作手册——故事线 + 实机截图 + 可选 Mermaid 示意图。正文零业务词、零演示账号、零仓库路径。

**SSOT 读取顺序**：`config/manual.yaml` → `learn/user-manual.md` → 均无则 AskQuestion + 按下表起草。禁止在 contract 写真实人名。

## 必备字段

| 区块 | 字段 | 说明 |
|------|------|------|
| `manual` | `id` / `doc_path` | 手册标识与产物路径（默认 `docs/07_…`） |
| | `assets_dir` / `version` | 配图发布目录；版本与文档顶栏同步 |
| | `audiences` | 读者角色槽位 id |
| `capture` | `profile` | `web-fullstack` · `web-spa-only` · `electron` · `flutter` · `native-window` |
| | `stack_command` / `walkthrough_command` | 起环境；产出 intermediate PNG |
| | `sync_command` / `intermediate_dir` | 中间图 → `assets_dir` |
| | `env` | 只存变量键名，值从 env 读，不写 secret |
| `roles[]` | `id` / `auth` / `default_route` | `auth` 取 `env` 或 `fixture`；`default_route` 定 shot 顺序 |
| `storylines[]` | `id` / `title` / `audience` | 故事线标识、标题、目标角色 |
| | `duration_min` / `inferred` / `shots[]` | `inferred: true` 表示从代码推断，须 Reader Test |
| `verify` | `l1_script` / `reader_test` / `anchors` | 机械验收 + 语义验收 + grep 锚点 |

`shots[]` 仅列 **walkthrough 实机截图**：`file` · `step` · `highlights` · `manual`（`true` = 禁止自动 regen，人工补图并登记）。

## 故事线结构（六段）

| 段落 | 落点 | 写法 |
|------|------|------|
| 读者 | `manual.audiences` + 「先选对故事线」表 | 按角色槽位与时长引导，不写真人 |
| 前置条件 | 故事线 ⓪ · 开始前 | 检查清单每项给可观察的通过标志 |
| 快速开始 | ⓪ 登录 + 角色默认首页 | 凭据由管理员分配，仓库不写密码 |
| 核心场景 | 故事线 ①～N | 前提 · 步骤表 · 嵌入图 · 期望结果 |
| FAQ | 附录 · 常见错误 | 只收真实高频错误，附下一步动作 |
| 限制 | 附录 + 正文边界 | 未覆盖角色、`manual: true` 待补图项、`inferred` 待 Reader Test 项、仅窗口像素无法元素级标注的场景 |

写作原则：按**任务**写，不按菜单树堆砌；每步可观察；图与步骤 1:1，红框区域在步骤文字中点明；关键操作不依赖外链设计 doc。

## 配图要求

| 项 | 要求 |
|----|------|
| 来源 | 仅 `storylines[].shots` 列出的实机截图，路径落 `assets_dir` |
| 时机 | 每 shot 前等业务就绪（非固定 sleep）；不起环境不截图 |
| 禁止 | 骨架屏配图；`fullPage` 整页截；概念图混入 `shots` |
| 裁切 | 按 shell（顶栏 / 侧栏 / 主区）+ highlight 并集裁切 |
| 红框 | 由 `highlights` 选器 / 坐标注入 overlay；`native-window` 无元素级红框 → 坐标表或后处理 |
| 兜底 | `manual: true` 人工补图并登记，不假装已自动更新 |
| 概念图 | 正文内嵌 Mermaid，不进 walkthrough；中文须显式配 CJK 字体，否则方框乱码 |

## 骨架（逐块拼接）

```markdown
# {产品名} · 软件使用说明书
> **版本**：v{x.y} · {date} ｜ **读者**：{角色槽位} ｜ **定位**：可单独发布的操作手册
> **配图**：`{assets_dir}/` 实机截图；概念图用正文 Mermaid
## 一、这本手册怎么用（你是谁 ｜ 从哪条线开始 ｜ 大约多久）
| {角色 A} | **故事线 ① {标题}** | {N} 分钟 |
```

```markdown
## 二、故事线 ⓪ · 开始前（人人必读）
| # | 检查项 | 通过标志 |
| ☐ 1 | {项} | {可观察标志} |
```

```markdown
## 三、故事线 ① · {标题}
**前提**：{检查清单引用} ｜ **做完应看到**：{期望结果}
| 步骤 | 操作 | 图 |
| 1 | {操作} | 图 1 → `{assets_dir}/{file}.png`
## 附录 · 术语 / 常见错误 / 联系支持（可选）
```

## 双层验收

| 层 | 手段 | 通过标准 |
|----|------|----------|
| L1 机械 | `verify.l1_script`：文件存在、链接可达、锚点 grep | 脚本绿 |
| L2 语义 | Reader Test：只给手册，逐题提问 | 十问全通过才可标 ✅ |

Reader Test 必做场景：新手册首版、大改版（故事线重组或图 >30% 更换）、含 `inferred: true` 故事线。答不出、歧义、与图不符 → 回改对应节，必要时只 regen 单张图。用户明确说「不用测读者」→ 记录跳过，仍建议维护者通读一遍。

## 禁止

- 无 verify 绿仍声称「配图已更新」，或跳过 verify 门禁。
- 无 Contract 时编造故事线而不标 `inferred`。
- 把概念示意图登记进 `storylines[].shots`，或指望 walkthrough 产出；无 CJK 字体链时静默导出中文 PNG。
- 用 manual regen 替代交付走查或 task-verify。

> 来源：Super Cursor /user-manual
