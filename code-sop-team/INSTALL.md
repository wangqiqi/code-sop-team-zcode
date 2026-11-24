# 安装说明（ZCode 版 code-sop-team v2.4.0）

13 人工程 SOP 专家团：12 个子智能体 + 9 个技能 + 零依赖闸门 CLI。

## 环境要求

- ZCode 桌面客户端
- Python 3.8+（闸门脚本用，纯标准库；没有也能用，但四道硬闸会显式降级为软约束）
- 可选：git（发版、pre-commit 钩子功能需要）

## 方式 A · 用户级直装（推荐，无需任何 UI 操作）

解压本包后，把对应内容复制到用户级资源目录（目录不存在就新建）：

```bash
unzip code-sop-team-zcode-v2.4.0.zip
mkdir -p ~/.zcode/skills ~/.zcode/agents ~/.zcode/bin ~/.zcode/tests

cp -r code-sop-team/skills/*               ~/.zcode/skills/
cp    code-sop-team/agents/*.md            ~/.zcode/agents/
cp    code-sop-team/bin/sop_gate.py        ~/.zcode/bin/
cp    code-sop-team/tests/test_sop_gate.py ~/.zcode/tests/
```

Windows（PowerShell）等价：

```powershell
Expand-Archive code-sop-team-zcode-v2.4.0.zip
New-Item -Force -ItemType Directory ~/.zcode/skills, ~/.zcode/agents, ~/.zcode/bin, ~/.zcode/tests | Out-Null

Copy-Item -Recurse -Force code-sop-team\skills\*               ~/.zcode\skills\
Copy-Item           code-sop-team\agents\*.md                  ~/.zcode\agents\
Copy-Item           code-sop-team\bin\sop_gate.py              ~/.zcode\bin\
Copy-Item           code-sop-team\tests\test_sop_gate.py       ~/.zcode\tests\
```

重开一个新会话即生效。自检：

```bash
bash ~/.zcode/skills/sop-team/scripts/preflight.sh   # 期望输出「结论: OK」
python3 ~/.zcode/bin/sop_gate.py doctor              # 期望 9 个 skill 全 OK
```

## 方式 B · 插件市场安装（可启停、可更新）

1. 解压本包，得到含 `marketplace.json` 的目录
2. ZCode → **插件市场 → 添加 → 添加插件市场**，选择/粘贴该目录
3. **个人 → dev-… 市场** → 找到「Code Engineering SOP Team / 代码工程 SOP 专家团」→ **安装**
4. 管理：**设置 → 插件**

## 验证安装

开个新任务，任意说一句：

- 「帮我规划一个加 `--verbose` 参数的小功能」→ 应看到逐卡问询 → 环境自检 → 规划师产出任务表
- 「用 code-reviewer review 一下」→ 应看到只读审查、按 Blocker/High 分级输出

## 快速指令

| 指令 | 用途 |
|------|------|
| `/sop-team` + 需求描述 | 主理人接管全流程 |
| `/sop-gate` | 手动跑闸门（task-verify / verify / doctor） |
| `/product-spec` `/architecture-design` `/ux-design` `/quality-checklists` `/delivery-contracts` `/release-ops` `/stack-conventions` | 单项能力直调 |

## 卸载

```bash
rm -rf ~/.zcode/skills/{sop-team,sop-gate,product-spec,architecture-design,ux-design,stack-conventions,quality-checklists,delivery-contracts,release-ops}
rm -f  ~/.zcode/agents/{sprint-planner,code-reviewer,release-engineer,product-manager,architect,qa-engineer,security-engineer,ux-designer,data-engineer,tech-spiker,morale-booster,engineering-steward}.md
rm -f  ~/.zcode/bin/sop_gate.py ~/.zcode/tests/test_sop_gate.py
```
