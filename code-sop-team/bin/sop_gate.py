#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sop_gate.py — 代码工程 SOP 专家团的跨平台硬约束闸门。

设计目标：
  1. 零第三方依赖（仅 Python 标准库），Python 3.8+，Windows / macOS / Linux 通吃。
  2. 不依赖目标项目已有任何目录结构。状态统一落在 <项目根>/.zcode/sop/。
  3. 自动探测项目根：优先环境变量 SOP_PROJECT_ROOT，否则从 cwd 向上找 .git，
     找不到就用 cwd（也可用 --root 显式指定）。
  4. fail-closed：任何判定不了的情况一律返回非 0，绝不静默放行。

用法：
  python sop_gate.py init      [--root PATH] [--force]      初始化 plan.md 工作副本
  python sop_gate.py status    [--root PATH]                打印闸门状态
  python sop_gate.py gate-check [--root PATH]               run 硬闸门（规划未批准则 BLOCK）
  python sop_gate.py plan-check [--root PATH]               plan 完整性检查（开工前）
  python sop_gate.py task-verify [TASK_ID] [--evidence "证据"] [--root PATH]
                                                            单任务验收（fail-closed；人工验收须留证）
  python sop_gate.py verify    [--force] [--root PATH]      Sprint / 打版前全量验收（默认要求任务全部 ✅）
  python sop_gate.py next-task [--apply] [--root PATH]     找出下一个 ACTIVE 任务（--apply 写回 ACTIVE/NEXT）
  python sop_gate.py followup  [TASK_ID] [--reset] [--root PATH]
                                                            查看/清零补丁循环计数（同一 TASK 连续失败轮次，≥2 应转 SPIKE）
  python sop_gate.py approve   [--force] [--root PATH]     写入 PLAN_APPROVED（前置校验 VERIFY + plan-check）
  python sop_gate.py set       <KEY> <VALUE> [--root PATH]  设置元数据（PLANNING/SPRINT/ACTIVE/...）
  python sop_gate.py release-check [--bump patch|minor|major] [--root PATH]
                                                            发版前置预检（next_version / CHANGELOG / plan 残项）
  python sop_gate.py friction-log --task ID --verify pass|fail|manual [--rounds N] [--rework N] [--note "..."]
                                                            记一条任务摩擦数据（Sprint 收尾看通过率与返工）
  python sop_gate.py friction-report [--root PATH]         汇总摩擦数据（通过率/轮次/返工 TOP/SPIKE 建议）
  python sop_gate.py install-hook [--root PATH]            安装可选 git pre-commit 硬闸门
  python sop_gate.py uninstall-hook [--root PATH]          卸载 git pre-commit 硬闸门

退出码：0 = OK / PASS；1 = BLOCK / FAIL；2 = 参数或环境错误；3 = MANUAL-PENDING（人工验收待留证）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

SOP_REL = Path(".zcode") / "sop"          # 状态目录（相对项目根）
PLAN_NAME = "plan.md"
HOOK_REL = Path(".git") / "hooks" / "pre-commit"
HOOK_MARK_BEGIN = "# >>> code-sop-gate >>>"
HOOK_MARK_END = "# <<< code-sop-gate <<<"

META_KEYS = [
    "PLANNING", "SPRINT", "PLAN_APPROVED", "AUTONOMOUS", "SPRINT_STATUS",
    "ACTIVE", "NEXT", "LAST_DONE", "VERIFY", "MAX_LOOPS", "RELEASE_BUMP",
]

STATUS_ACTIVE = ("⬜", "🔧")     # 未完成
STATUS_DONE = "✅"
STATUS_WARN = "⚠️"
STATUS_MARKERS = (STATUS_DONE, STATUS_WARN, "⬜", "🔧")

# 环境异常保护的上限：一是超时钳制，二是并发写状态时的等待/陈旧判定。
MAX_VERIFY_TIMEOUT = 86400       # 24h，超过视为配置错误
LOCK_NAME = ".lock"
LOCK_STALE_SEC = 120             # 超过 2 分钟未见更新的锁视为进程崩溃残留
LOCK_DEFAULT_WAIT = 5.0

# 只有形如 2026-11-18 的真实日期才算批准；hacked / todo / true 都不算。
APPROVAL_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

PLAN_TEMPLATE = """<!-- 代码工程 SOP 工作副本 · 由 sop_gate.py init 生成 · 本文件通常 gitignore -->
<!-- 纪律：禁止删除 ⬜/🔧/⚠️ 任务行，除非用户明确取消 -->
<!-- PLANNING: true -->
<!-- SPRINT: (none) -->
<!-- PLAN_APPROVED: (none) -->
<!-- AUTONOMOUS: true -->
<!-- SPRINT_STATUS: closed -->
<!-- ACTIVE: (none) -->
<!-- NEXT: (none) -->
<!-- LAST_DONE: (none) -->
<!-- VERIFY: (none) -->
<!-- MAX_LOOPS: 15 -->

# Plan

无 Active Sprint。用 /plan 冻结 Goal · Done when · Out of scope，拆出 TASK 后等待用户确认，再由主理人执行 `approve` 解锁闸门。

---

## Active sprint · SPRINT-01 Example

（有进行中 Sprint 时保留本区块；全部 ✅ 后整段删除。）

**Goal**: （能力/模块交付，不要写「打 tag / merge」这类出口动作）

**Done when**:

- [ ] P0 tasks ✅ · `python <专家bin>/sop_gate.py verify`
- [ ] （可选）交付走查无 Blocker

**Out of scope**: （明确边界，防漂移）

| ID | Task | Priority | Status | Acceptance | Target |
|----|------|----------|--------|------------|--------|
| TASK-001 | 示例任务 | P0 | ⬜ | `python -c "print('ok')"` | `src/` |

**执行顺序**: `TASK-001`

---

## 下一 Sprint · 候选

| 候选 | Goal | 依赖 |
|------|------|------|
| SPRINT-02 | （待规划） | — |
"""

HOOK_BODY = """{HOOK_MARK_BEGIN}
# 由代码工程 SOP 专家团安装：提交前强制校验闸门（plan-check + gate-check）。
# 如本仓库未启用 SOP（无 .zcode/sop/plan.md），直接放行。
_SOP_PY=__SOP_PY_PATH__
# 安装时就把「当前解释器」的绝对路径写进钩子：会话里的解释器常常
# 不在系统 PATH 上；普通 Windows 机器更是默认没有 Python。
# 只找 PATH 会让钩子在这些机器上软降级放行，硬闸形同虚设。
_SOP_PY_BIN=__SOP_PY_BIN__
if [ -f .zcode/sop/plan.md ]; then
  if [ ! -f "$_SOP_PY" ]; then
    echo "[sop-gate] 闸门脚本不存在: $_SOP_PY" >&2
    echo "            插件可能已移动/卸载，请重装或运行 install-hook 更新路径。" >&2
    exit 1
  fi
  if [ -n "$_SOP_PY_BIN" ] && [ -x "$_SOP_PY_BIN" ]; then
    _PY="$_SOP_PY_BIN"
  elif command -v python3 >/dev/null 2>&1; then
    _PY=python3
  elif command -v python >/dev/null 2>&1; then
    _PY=python
  else
    echo "[sop-gate] 未找到 python（含 ZCode 会话解释器），硬闸门软降级放行" >&2
    echo "            重装钩子可重新定位解释器；或显式设 SOP_GATE_PY 后修改本钩子。" >&2
    exit 0
  fi
  if ! "$_PY" "$_SOP_PY" plan-check >/dev/null 2>&1; then
    echo "[sop-gate] plan-check 未通过：plan 结构有问题，禁止 commit。" >&2
    echo "            查看详情: \\"$_PY\\" \\"$_SOP_PY\\" plan-check" >&2
    exit 1
  fi
  if ! "$_PY" "$_SOP_PY" gate-check >/dev/null 2>&1; then
    echo "[sop-gate] gate-check 未通过：规划未获批准（或仍在规划期），禁止 commit。" >&2
    echo "            查看详情: \\"$_PY\\" \\"$_SOP_PY\\" gate-check" >&2
    exit 1
  fi
fi
{HOOK_MARK_END}""".replace("{HOOK_MARK_BEGIN}", HOOK_MARK_BEGIN).replace("{HOOK_MARK_END}", HOOK_MARK_END)


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------

def _detect_root(explicit: Optional[str]) -> Path:
    """探测项目根：显式 --root > 环境变量 > 向上找 .git > cwd。"""
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if not p.is_dir():
            die(f"--root 指向的目录不存在: {p}")
        return p
    env = os.environ.get("SOP_PROJECT_ROOT", "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if not p.is_dir():
            # 静默退回 cwd 会让用户以为在 A 项目跑，实际改的是 B 项目——
            # 这是比「报错」严重得多的 fail-open，必须显式拒绝。
            die(f"SOP_PROJECT_ROOT 指向的目录不存在: {p}（取消该环境变量或改正路径）")
        return p
    cur = Path.cwd().resolve()
    for candidate in (cur,) + tuple(cur.parents):
        if (candidate / ".git").exists():
            return candidate
    return cur


def sop_dir(root: Path) -> Path:
    return root / SOP_REL


def plan_path(root: Path) -> Path:
    return sop_dir(root) / PLAN_NAME


def die(msg: str, code: int = 2) -> "NoReturn":  # type: ignore[valid-type]
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def read_text(p: Path) -> str:
    """读文本。任何 I/O 异常都退化为空串（后续闸门因为解析不到内容而 fail-closed）。

    Windows 上把目录当文件读会得到 PermissionError，不是 FileNotFoundError；
    只捕获后两者会让 status / verify 直接抛 Traceback。
    """
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
    except OSError as e:
        if not isinstance(e, FileNotFoundError):
            print(f"WARN: 读取失败，按空内容处理（闸门会 fail-closed）: {p} ({e})", file=sys.stderr)
        return ""


def atomic_write(p: Path, text: str) -> None:
    """原子落盘：先写同目录临时文件再 os.replace。

    状态文件（plan/evidence/followup）会被主理人与多个团员并发读写；
    直接 write_text 一旦在写入中途被打断，会留下半截文件，
    而 load_* 的 except 会把它当成「空」——证据静默丢失，属于 fail-open。
    Windows 上文件被编辑器/杀软短暂占用时 os.replace 会抛 PermissionError，
    做几次短重试；仍失败就明确报错，绝不假装写入成功。
    """
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + f".tmp{os.getpid()}")
    try:
        for attempt in range(4):
            try:
                tmp.write_text(text, encoding="utf-8")
                os.replace(tmp, p)
                return
            except PermissionError:
                if attempt == 3:
                    raise
                time.sleep(0.05 * (attempt + 1))
    except OSError as e:
        die(f"写入状态文件失败: {p} ({e})", 1)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


@contextmanager
def state_lock(root: Path) -> Iterator[None]:
    """跨进程状态锁（mkdir 原子性，Windows/POSIX 通用）。

    只包住「读-改-写」的那一小段，不包住验收命令（可能跑 10 分钟）。
    锁目录里写 owner.json 供陈旧判定：进程崩溃时不会把后来者永久锁死。
    """
    lock = sop_dir(root) / LOCK_NAME
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        wait = max(0.0, float(os.environ.get("SOP_STATE_LOCK_WAIT", str(LOCK_DEFAULT_WAIT))))
    except ValueError:
        wait = LOCK_DEFAULT_WAIT
    deadline = time.monotonic() + wait
    while True:
        try:
            lock.mkdir()
            (lock / "owner.json").write_text(
                json.dumps({"pid": os.getpid(), "ts": time.time()}), encoding="utf-8")
            break
        except FileExistsError:
            _clear_stale_lock(lock)
            if time.monotonic() >= deadline:
                die(f"状态文件正被另一进程占用（{lock}），请稍后重试或删除过期锁", 1)
            time.sleep(0.02)
        except OSError as e:
            die(f"无法获取状态锁 {lock}: {e}", 1)
    try:
        yield
    finally:
        try:
            (lock / "owner.json").unlink()
        except OSError:
            pass
        try:
            lock.rmdir()
        except OSError:
            pass


def _clear_stale_lock(lock: Path) -> None:
    owner = lock / "owner.json"
    try:
        info = json.loads(read_text(owner))
        ts = float(info.get("ts", 0))
    except Exception:
        ts = 0.0
    if ts and time.time() - ts < LOCK_STALE_SEC:
        return
    # 无 owner / 时间戳过旧 = 崩溃残留，可安全清理
    try:
        owner.unlink()
    except OSError:
        pass
    try:
        lock.rmdir()
    except OSError:
        pass


def approval_valid(value: str) -> bool:
    """批准值必须是真实日期；空值/占位符/任意字符串都无效。"""
    v = (value or "").strip()
    if not APPROVAL_RE.match(v):
        return False
    try:
        date.fromisoformat(v)
        return True
    except ValueError:
        return False


def status_markers(status: str) -> List[str]:
    """返回一个状态单元格里的所有合法状态标记。多个 = 状态歧义。"""
    return [m for m in STATUS_MARKERS if m in (status or "")]


def task_structure_issues(text: str) -> List[str]:
    """plan 结构层面的 fail-closed 检查：重复 ID / 状态歧义。

    重复 ID 会让 dict 后者覆盖前者（一个 ✅ 覆盖一个 ⬜ = 假完成）；
    状态歧义（⬜ ✅ 同格）会让 plan-check 与 verify 各取所需的半边。
    """
    tasks = parse_tasks(text)
    issues: List[str] = []
    seen: Dict[str, int] = {}
    for t in tasks:
        seen[t["id"]] = seen.get(t["id"], 0) + 1
    for tid, n in sorted(seen.items()):
        if n > 1:
            issues.append(f"任务 ID 重复: {tid}（{n} 行）")
    for t in tasks:
        marks = status_markers(t["status"])
        if len(marks) > 1:
            issues.append(f"{t['id']} 状态歧义: {t['status']}（同时出现 {'/'.join(marks)}）")
    return issues


def parse_meta(text: str) -> Dict[str, str]:
    """解析 <!-- KEY: value --> 形式的元数据。"""
    meta: Dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"\s*<!--\s*([A-Z_]+)\s*:\s*(.*?)\s*-->\s*$", line)
        if m:
            meta[m.group(1)] = m.group(2).strip()
    return meta


def set_meta(text: str, key: str, value: str) -> str:
    """更新或新增一个元数据注释行，保持其余内容不变。"""
    pattern = re.compile(rf"(^<!--\s*{re.escape(key)}\s*:\s*).*?(\s*-->\s*$)", re.MULTILINE)
    new_line = f"<!-- {key}: {value} -->"
    if pattern.search(text):
        return pattern.sub(lambda m: m.group(1) + value + m.group(2), text, count=1)
    # 未在头部找到 → 插到第一行之后
    lines = text.splitlines(keepends=True)
    insert_at = 1 if lines and lines[0].startswith("<!--") else 0
    lines.insert(insert_at, new_line + "\n")
    return "".join(lines)


def _split_md_row(line: str) -> List[str]:
    """按 Markdown 表格语法拆一行，但把转义的 \\| 保护起来。

    Markdown 表格里管道符必须写成 \\|；验收命令里管道符很常见
    （如 `npm test | tee log`）。若直接 split("|")，命令会被截断成
    半截 → 执行失败或（更糟）变成另一条能跑通的命令 → fail-open。
    """
    SENTINEL = "\x00SOP_PIPE\x00"
    protected = line.strip().strip("|").replace("\\|", SENTINEL)
    cells = [c.strip() for c in protected.split("|")]
    return [c.replace(SENTINEL, "|") for c in cells]


def parse_tasks(text: str) -> List[Dict[str, str]]:
    """解析 Markdown 任务表：| ID | Task | Priority | Status | Acceptance | Target |

    ID 必须完整匹配 `TYPE-<数字>`（不允许 TASK-001abc 这类脏 ID 混进主路径）。
    """
    tasks: List[Dict[str, str]] = []
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = _split_md_row(line)
        if len(cells) < 6:
            continue
        tid = cells[0].strip("* ")
        if not re.match(r"^(TASK|SPIKE|REV|DOC)-\d+$", tid):
            continue
        if len(cells) > 6:
            #  Acceptance 里有未转义的 |：Markdown 表格会把它拆成额外列。
            # 不能静默取前 6 列——那会把验收命令截断成半截，
            # 轻则执行失败，重则变成另一条能跑通的命令（fail-open）。
            # 把多余列并回 Acceptance，并插入显式警告让 plan-check / doctor 报出。
            merged = " | ".join(cells[4:-1])
            cells = cells[:4] + [merged, cells[-1]]
        tasks.append({
            "id": tid,
            "task": cells[1],
            "priority": cells[2],
            "status": cells[3],
            "acceptance": cells[4],
            "target": cells[5],
        })
    return tasks


def execution_order(text: str) -> List[str]:
    """解析 **执行顺序**: `TASK-001` → `TASK-002` 行。"""
    for line in text.splitlines():
        if re.search(r"\*\*(执行顺序|Order)\*\*", line):
            return re.findall(r"`([A-Z]+-\d+)`", line)
    return []


def classify_acceptance(acc: str) -> str:
    """判定验收列类型：exec / manual / prose。"""
    a = (acc or "").strip().strip("`").strip()
    if not a or a in ("(none)", "…", "—", "-"):
        return "prose"
    if a.startswith("manual:"):
        return "manual"
    # 明显的自然语言而非命令
    if re.match(r"^(功能|UI|界面|页面|确保|完成|实现|检查是否|正常|没问题)", a) and " " not in a[:12]:
        return "prose"
    # 含可执行命令特征
    if re.search(r"(python|pytest|npm|pnpm|yarn|node|bash|sh |grep|curl|make|docker|dotnet|go test|cargo|mvn|gradle|echo|test)", a):
        return "exec"
    if a.startswith("./") or a.startswith("/") or "\\" in a:
        return "exec"
    return "prose"


def _cmd_timeout() -> int:
    """验收超时（秒）。默认 10 分钟；可用 SOP_VERIFY_TIMEOUT 覆盖，0 = 不限制。

    超大整数会传进 subprocess.communicate 的 time.monotonic 计算，
    Windows 上直接 OverflowError + Traceback。这里钳到 24h；越界值给警告。
    """
    raw = os.environ.get("SOP_VERIFY_TIMEOUT", "600").strip()
    try:
        n = int(raw)
    except ValueError:
        print(f"WARN: SOP_VERIFY_TIMEOUT={raw!r} 不是整数，使用默认 600s", file=sys.stderr)
        return 600
    if n < 0:
        print("WARN: SOP_VERIFY_TIMEOUT 为负数，按 0（不限制）处理", file=sys.stderr)
        return 0
    if n > MAX_VERIFY_TIMEOUT:
        print(f"WARN: SOP_VERIFY_TIMEOUT={n} 超过上限 {MAX_VERIFY_TIMEOUT}s，已钳制", file=sys.stderr)
        return MAX_VERIFY_TIMEOUT
    return n


def _kill_process_tree(proc: "subprocess.Popen") -> None:
    """超时后杀掉整棵进程树（shell 及其子进程），避免孤儿进程占着管道。"""
    if os.name == "nt":
        try:
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except Exception:
            pass
    # POSIX：杀进程组（负 pid）
    try:
        os.killpg(os.getpgid(proc.pid), 9)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def run_cmd(cmd: str, cwd: Path) -> int:
    """跨平台执行命令。带真正的超时保护，避免 watch 模式等永不退出的命令挂死闸门。"""
    print(f"==> 执行验收命令: {cmd}")
    timeout = _cmd_timeout()
    kwargs = {
        "cwd": str(cwd),
        "shell": True,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    proc = None
    try:
        proc = subprocess.Popen(cmd, **kwargs)
        out, _ = proc.communicate(timeout=timeout or None)
        if out:
            print(out.decode("utf-8", errors="replace"), end="")
        return proc.returncode
    except subprocess.TimeoutExpired:
        _kill_process_tree(proc)
        if proc is not None:
            try:
                rest, _ = proc.communicate(timeout=3)
                if rest:
                    print(rest.decode("utf-8", errors="replace"), end="")
            except Exception:
                pass
        print(f"FAIL: 验收命令超过 {timeout}s 未退出 — 判定失败（疑似 watch/交互/死循环）", file=sys.stderr)
        print("      修法: 用非交互的 CI 模式（如 pytest -q / npm test -- --run）；", file=sys.stderr)
        print("      确需更长时限: 设环境变量 SOP_VERIFY_TIMEOUT=<秒>，0 表示不限。", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        # Ctrl+C 只打到父进程时，子进程会变成孤儿继续占着管道；主动收树。
        _kill_process_tree(proc)
        print("FAIL: 用户中断验收命令 — 判定失败，不得标 PASS", file=sys.stderr)
        return 130
    except OSError as e:
        print(f"WARN: shell 执行失败({e})，尝试 shlex 拆分", file=sys.stderr)
        try:
            args = shlex.split(cmd)
            p2 = subprocess.Popen(args, cwd=str(cwd), stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT)
            out, _ = p2.communicate(timeout=timeout or None)
            if out:
                print(out.decode("utf-8", errors="replace"), end="")
            return p2.returncode
        except subprocess.TimeoutExpired:
            _kill_process_tree(p2)
            print(f"FAIL: 命令超过 {timeout}s 未退出 — 判定失败", file=sys.stderr)
            return 1
        except Exception as e2:
            print(f"FAIL: 命令无法执行: {e2}", file=sys.stderr)
            return 1

# ---------------------------------------------------------------------------
# 命令实现
# ---------------------------------------------------------------------------

GITIGNORE_ENTRY = ".zcode/sop/"


def _gitignore_covers(line: str) -> bool:
    """识别用户已有的等效忽略规则，避免 init 反复追加（幂等）。

    覆盖 `.zcode` / `.zcode/` / `.zcode/sop` / `.zcode/sop/`
    / `.zcode/sop/*` / `**/.zcode/sop/` 等常见写法。
    """
    s = line.strip().strip("/")
    if s in (".zcode", ".zcode/sop", ".zcode/sop/*"):
        return True
    return s.endswith("/.zcode/sop") or s.endswith("/.zcode/sop/*")


def ensure_gitignore(root: Path) -> Tuple[bool, bool]:
    """把状态目录写进 .gitignore（幂等）。返回 (是否写入, 是否已被 git 跟踪)。

    状态文件是本地执行面板（含人工验收证据），一旦被提交：
      - 多会话 / 多团员会互相覆盖 plan，违反编辑主权
      - 证据里的复核人、截图路径进仓库
      - 每次状态变更都产生 commit 噪声
    所以不再只「口头建议」，init 时直接补一行；追加不覆盖用户原有内容。
    """
    gi = root / ".gitignore"
    lines = read_text(gi).splitlines() if gi.is_file() else []
    covered = any(
        _gitignore_covers(ln.strip())
        for ln in lines if ln.strip() and not ln.strip().startswith("#")
    )
    wrote = False
    if not covered:
        block = ["", "# 代码工程 SOP 本地状态（plan / 验收证据 / 补丁计数）", GITIGNORE_ENTRY]
        atomic_write(gi, "\n".join(lines + block).lstrip("\n") + "\n")
        wrote = True

    tracked = False
    try:
        cp = subprocess.run(
            ["git", "ls-files", "--error-unmatch", GITIGNORE_ENTRY],
            cwd=str(root), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        tracked = cp.returncode == 0
    except Exception:
        pass
    return wrote, tracked


def cmd_init(root: Path, force: bool) -> int:
    d = sop_dir(root)
    p = plan_path(root)
    if p.exists() and not p.is_file():
        print(f"FAIL: plan 路径不是普通文件，无法初始化: {p}", file=sys.stderr)
        return 1
    if p.exists() and not force:
        print(f"SKIP: plan 已存在: {p}（如需覆盖加 --force）")
        # 仍检查 gitignore：老项目 init 过但没写的情况要能补救
        wrote, tracked = ensure_gitignore(root)
        if wrote:
            print(f"OK: 已把 {GITIGNORE_ENTRY} 补进 .gitignore")
        if tracked:
            print(f"WARN: 状态文件已被 git 跟踪 — .gitignore 对已跟踪文件无效，请执行: git rm --cached -r {GITIGNORE_ENTRY}")
        return 0
    d.mkdir(parents=True, exist_ok=True)
    with state_lock(root):
        atomic_write(p, PLAN_TEMPLATE)
    print(f"OK: 已初始化 SOP 工作副本 → {p}")
    wrote, tracked = ensure_gitignore(root)
    if wrote:
        print(f"OK: 已把 {GITIGNORE_ENTRY} 补进 .gitignore（状态文件不入库）")
    else:
        print(f"OK: .gitignore 已覆盖 {GITIGNORE_ENTRY}")
    if tracked:
        print(f"WARN: 状态文件已被 git 跟踪 — .gitignore 对已跟踪文件无效，请执行: git rm --cached -r {GITIGNORE_ENTRY}")
    return 0


def cmd_status(root: Path) -> int:
    p = plan_path(root)
    if not p.exists():
        print("STATUS: 未初始化（先运行 init）")
        return 1
    if not p.is_file():
        print(f"FAIL: plan 路径不是普通文件: {p}（先修复该路径再运行 init）", file=sys.stderr)
        return 1
    text = read_text(p)
    meta = parse_meta(text)
    tasks = parse_tasks(text)
    active = [t for t in tasks if t["status"] in STATUS_ACTIVE]
    print("=== SOP 状态 ===")
    print(f"项目根:   {root}")
    print(f"plan:     {p}")
    for k in ("PLANNING", "SPRINT", "PLAN_APPROVED", "AUTONOMOUS", "SPRINT_STATUS"):
        print(f"{k:<16}: {meta.get(k, '(unset)')}")
    print(f"{'ACTIVE':<16}: {meta.get('ACTIVE', '(none)')}")
    print(f"{'NEXT':<16}: {meta.get('NEXT', '(none)')}")
    print(f"{'VERIFY':<16}: {meta.get('VERIFY', '(none)')}")
    print(f"活跃任务: {len(active)} 个 -> " + ", ".join(t["id"] for t in active))
    return 0


def cmd_doctor(root: Path) -> int:
    """环境与链路自检：定位「全流程跑不通」到底断在哪一环。"""
    print("=== doctor · 环境与链路自检 ===")
    problems: List[str] = []
    warns: List[str] = []

    # 1) Python 版本
    v = sys.version_info
    if v >= (3, 8):
        print(f"OK   Python {v.major}.{v.minor}.{v.micro}（当前解释器: {sys.executable or '(未知)'}）")
    else:
        print(f"FAIL Python {v.major}.{v.minor} — 需 3.8+")
        problems.append("Python 版本过低")

    # 2) 脚本自身位置
    me = Path(__file__).resolve()
    print(f"OK   脚本: {me}")

    # 3) 随包技能文件
    exp_root = me.parent.parent
    for s in (
        "sop-team", "sop-gate", "quality-checklists", "delivery-contracts", "release-ops",
        "stack-conventions", "product-spec", "architecture-design", "ux-design",
    ):
        sk = exp_root / "skills" / s / "SKILL.md"
        if sk.exists():
            print(f"OK   skill: {s}")
        else:
            print(f"WARN skill 缺失: {sk}")
            warns.append(f"skill {s} 缺失（插件可能不完整）")

    # 4) 项目根与状态目录
    print(f"OK   项目根: {root}")
    d = sop_dir(root)
    try:
        d.mkdir(parents=True, exist_ok=True)
        probe = d / ".write-probe"
        probe.write_text("x", encoding="utf-8")
        probe.unlink()
        print(f"OK   状态目录可写: {d}")
    except Exception as e:
        print(f"FAIL 状态目录不可写: {d} ({e})")
        problems.append("状态目录不可写")

    # 5) plan.md
    p = plan_path(root)
    if not p.exists():
        print("WARN plan 未初始化 — 首次使用请跑 init")
        warns.append("plan 未初始化")
    else:
        try:
            text = read_text(p)
            meta = parse_meta(text)
            tasks = parse_tasks(text)
            print(f"OK   plan 可解析: {len(meta)} 个元数据 · {len(tasks)} 个任务")
            if not meta:
                warns.append("plan 元数据为空，格式可能被破坏")
            pend = [t["id"] for t in tasks if re.match(r"^TASK-\d+$", t["id"]) and "✅" not in t["status"]]
            print(f"     状态: PLANNING={meta.get('PLANNING','?')} · APPROVED={meta.get('PLAN_APPROVED','?')} · "
                  f"ACTIVE={meta.get('ACTIVE','?')} · 未完成={len(pend)}")
            if not meta.get("VERIFY") or meta.get("VERIFY") in ("(none)",):
                print("WARN VERIFY 未设置 — 出口闸将无法通过")
                guess = detect_verify_command(root)
                if guess:
                    print(f'     回退探测到可用命令: {guess} —— 建议 set VERIFY "{guess}"')
                else:
                    print("     也未探测到项目验收入口，请显式设定 VERIFY")
                warns.append("VERIFY 未设置")
        except Exception as e:
            print(f"FAIL plan 解析失败: {e}")
            problems.append("plan 解析失败")

    # 6) 证据文件
    ev = evidence_path(root)
    if ev.exists():
        data = load_evidence(root)
        if data:
            print(f"OK   人工验收证据: {len(data)} 条（{'、'.join(list(data)[:5])}）")
        else:
            print(f"WARN 证据文件存在但内容损坏（无法解析为有效证据）: {ev}")
            warns.append("evidence.json 损坏")
    else:
        print("     人工验收证据: 无（尚无 manual 任务留证）")

    # 7) 补丁循环计数
    fu = load_followup(root)
    hot = {k: n for k, n in fu.items() if n >= 2}
    if hot:
        detail = "、".join(f"{k}×{n}" for k, n in sorted(hot.items()))
        print(f"WARN 补丁循环计数达阈值: {detail} — 应转 SPIKE 而非继续 patch")
        warns.append("存在连续失败 ≥2 轮的任务")
    elif fu:
        print("     补丁循环计数: " + "、".join(f"{k}×{n}" for k, n in sorted(fu.items())) + "（未达阈值）")
    else:
        print("     补丁循环计数: 无")

    # 7.5) 状态文件是否已进 git（本地执行面板不应被提交）
    tracked = False
    try:
        cp = subprocess.run(
            ["git", "ls-files", "--error-unmatch", GITIGNORE_ENTRY],
            cwd=str(root), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        tracked = cp.returncode == 0
    except Exception:
        pass
    if tracked:
        print(f"WARN 状态文件已被 git 跟踪 — plan/证据会随 commit 入库并互相覆盖")
        print(f'     修法: git rm --cached -r {GITIGNORE_ENTRY}  然后补 .gitignore')
        warns.append("状态文件已入 git")
    else:
        gi = root / ".gitignore"
        covered = any(
            _gitignore_covers(ln.strip())
            for ln in read_text(gi).splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ) if gi.is_file() else False
        if covered:
            print("OK   状态目录已在 .gitignore（不入库）")
        else:
            print("WARN 状态目录未进 .gitignore — 跑 init 会自动补上")
            warns.append(".gitignore 未覆盖状态目录")

    # 7.6) 并发状态锁 + 批准格式
    lock = sop_dir(root) / LOCK_NAME
    if lock.exists():
        try:
            info = json.loads(read_text(lock / "owner.json"))
            age = max(0.0, time.time() - float(info.get("ts", 0)))
        except Exception:
            age = LOCK_STALE_SEC + 1
        if age < LOCK_STALE_SEC:
            print(f"WARN 状态锁被占用（{age:.0f}s）— 另一进程可能正在写，稍后重试")
            warns.append("状态锁被占用")
        else:
            print(f"WARN 存在过期状态锁（{lock}）— 下次写入会自动清理，也可手动删除")
            warns.append("过期状态锁残留")
    else:
        print(f"OK   状态锁: 无残留（mkdir 原子锁；默认等待 {LOCK_DEFAULT_WAIT:.0f}s 后 fail-closed）")

    appr = parse_meta(read_text(p)).get("PLAN_APPROVED", "") if p.is_file() else ""
    if approval_valid(appr) or not appr or appr == "(none)":
        print("OK   批准格式: PLAN_APPROVED 为空或 YYYY-MM-DD（其它值一律 BLOCK）")
    else:
        print(f"WARN 批准格式: PLAN_APPROVED={appr} 不是 YYYY-MM-DD — gate-check 会 BLOCK")
        warns.append("批准格式非法")

    # 8) git 钩子：不能只看标记——插件移动 / 受管 Python 升级后，
    #    钩子还在但内嵌路径已失效，会静默软降级放行（假绿灯）。
    hook = root / HOOK_REL
    if hook.exists():
        try:
            body = hook.read_text(encoding="utf-8", errors="ignore")
            if HOOK_MARK_BEGIN not in body:
                print("WARN pre-commit 存在但不是本 SOP 安装的")
                warns.append("pre-commit 被他方占用")
            else:
                print("OK   git pre-commit 硬闸门已安装")
                m = re.search(r"^_SOP_PY=(.*)$", body, re.M)
                if not m:
                    print("WARN 钩子缺少 _SOP_PY 定义，无法确认闸门脚本位置")
                    warns.append("钩子脚本路径未定义")
                else:
                    sp = Path(_sh_unquote_path(m.group(1)))
                    if sp.is_file():
                        print(f"OK   钩子脚本路径有效: {sp}")
                    else:
                        print(f"FAIL 钩子脚本路径失效: {sp} — 钩子会拒绝 commit，请重装钩子")
                        problems.append("钩子脚本路径失效")

                mb = re.search(r"^_SOP_PY_BIN=(.*)$", body, re.M)
                if not mb:
                    print("WARN 旧版钩子未内嵌解释器 — PATH 无 Python 时会软降级放行")
                    warns.append("旧版钩子未内嵌解释器")
                else:
                    bp_raw = _sh_unquote_path(mb.group(1))
                    if not bp_raw:
                        print("WARN 钩子未记录解释器路径")
                        warns.append("钩子解释器未记录")
                    elif Path(bp_raw).is_file():
                        print(f"OK   钩子解释器路径有效: {bp_raw}")
                    elif shutil.which("python3") or shutil.which("python"):
                        print(f"WARN 钩子内嵌解释器失效（{bp_raw}），但 PATH 仍有 Python — 建议重装钩子")
                        warns.append("钩子内嵌解释器失效")
                    else:
                        print(f"FAIL 钩子解释器失效: {bp_raw} — PATH 也无 Python，硬闸门已软降级")
                        problems.append("钩子解释器失效")
        except Exception:
            print("WARN 无法读取 pre-commit")
    else:
        print("     硬锁: 未安装 git 钩子（可选，install-hook 开启）")

    # 8.5) 回归测试套件（只报存在性，不在 doctor 里跑——43 个用例要 ~60 秒）
    test_file = exp_root / "tests" / "test_sop_gate.py"
    if test_file.exists():
        print(f"OK   回归测试套件: {test_file}（手动运行: python tests/test_sop_gate.py）")
    else:
        print("WARN 回归测试套件缺失 — 插件可能不完整")
        warns.append("tests/test_sop_gate.py 缺失")

    # 9) git 仓库
    if (root / ".git").exists():
        print("OK   位于 git 仓库内")
    else:
        print("WARN 不在 git 仓库内 — 无法安装钩子、无法 commit")
        warns.append("非 git 仓库")

    # 结论
    print()
    if problems:
        print(f"结论: FAIL — {len(problems)} 个阻塞问题：" + "；".join(problems))
        return 1
    if warns:
        print(f"结论: OK（{len(warns)} 条提示，不阻塞）：" + "；".join(warns))
        return 0
    print("结论: OK — 全链路就绪")
    return 0


def cmd_gate_check(root: Path) -> int:
    p = plan_path(root)
    if not p.exists():
        print("BLOCK: 未初始化 plan（先运行 init）")
        return 1
    meta = parse_meta(read_text(p))
    planning = meta.get("PLANNING", "false").lower() in ("true", "1", "yes")
    approved = meta.get("PLAN_APPROVED", "(none)")
    print("=== gate-check ===")
    if planning:
        print("BLOCK: PLANNING=true — 请先完成规划并把 PLANNING 设为 false")
        return 1
    if not approval_valid(approved):
        # 只认真实日期。hacked / true / todo 这类非空占位符以前会解锁闸门。
        print(f"BLOCK: PLAN_APPROVED={approved or '(空)'} 无效 — 必须是由 approve 写入的 YYYY-MM-DD 日期")
        return 1
    print(f"OK: PLAN_APPROVED={approved} · SPRINT={meta.get('SPRINT','(none)')} · ACTIVE={meta.get('ACTIVE','(none)')}")
    return 0


def cmd_plan_check(root: Path, for_approve: bool = False) -> int:
    p = plan_path(root)
    if not p.exists():
        print("FAIL: plan 不存在（先运行 init）")
        return 1
    text = read_text(p)
    meta = parse_meta(text)
    tasks = parse_tasks(text)
    active = [t for t in tasks if t["status"] in STATUS_ACTIVE]
    order = execution_order(text)
    issues = 0

    print("=== plan-check ===")
    for msg in task_structure_issues(text):
        print(f"FAIL: {msg}")
        issues += 1
    done = [t for t in tasks if "✅" in t["status"]]
    all_done = bool(tasks) and len(done) == len(tasks)
    if not active:
        if all_done:
            # Sprint 干完了：这不是问题，是收尾信号。绝不能因此拦 commit。
            print("INFO: 全部任务已完成 — Sprint 可收尾（verify 后清理 Active 区块）")
        else:
            print("WARN: 无活跃 ⬜/🔧 任务")
            issues += 1
    if (not meta.get("ACTIVE") or meta["ACTIVE"] in ("(none)",)) and not all_done:
        print("WARN: ACTIVE 未设置")
        issues += 1
    if not meta.get("SPRINT") or meta["SPRINT"] in ("(none)",):
        print("WARN: SPRINT 未设置")
        issues += 1
    if not order and not all_done:
        print("WARN: 缺 **执行顺序** 行")
        issues += 1
    planning = meta.get("PLANNING", "false").lower() in ("true", "1", "yes")
    verify_cmd = (meta.get("VERIFY") or "").strip()
    if not verify_cmd or verify_cmd in ("(none)", "none"):
        if planning:
            print("INFO: VERIFY 未设置 — 规划期可后补，但 approve 前必须写入全量验收命令")
        else:
            print("WARN: VERIFY 未设置 — 收尾/打版 verify 必然 FAIL（写 <!-- VERIFY: <命令> -->）")
            issues += 1
    if planning:
        print("INFO: PLANNING=true — 仅规划阶段，暂不编码")
    elif for_approve:
        print("INFO: approve 前置校验 — 跳过 PLAN_APPROVED 检查（本次即将写入）")
    elif not meta.get("PLAN_APPROVED") or meta["PLAN_APPROVED"] in ("(none)",):
        print("FAIL: PLAN_APPROVED 未设置（run 硬闸门）")
        issues += 1

    for t in active:
        kind = classify_acceptance(t["acceptance"])
        if kind == "prose":
            print(f"WARN: {t['id']} 验收列不可执行 → task-verify 会 FAIL: {t['acceptance'] or '(空)'}")
            issues += 1
        if not t["target"] or t["target"] in ("…", "—"):
            print(f"WARN: {t['id']} 缺 Target/落点")
            issues += 1

    if issues:
        print(f"结果: FAIL（{issues} 项）— 修复后再 /run")
        return 1
    print("结果: OK — plan 结构合格")
    return 0


def _acceptance_cmd(acc: str) -> Optional[str]:
    """从验收列取命令：多个反引号时优先「像命令」的那一个。

    反引号也常用来圈路径/文件名（`src/`、`tests/`）。旧版总取第一个，
    「在 `src/` 目录执行 `echo ok`」会去执行 `src/` —— 轻则失败，
    重则第一个片段恰好是另一条能跑通的命令，造成假 PASS。
    """
    a = acc.strip()
    groups = [g.strip() for g in re.findall(r"`([^`]+)`", a) if g.strip()]
    if groups:
        for g in groups:
            if classify_acceptance(g) in ("exec", "manual"):
                return g
        return groups[0]
    return a or None


def followup_path(root: Path) -> Path:
    return sop_dir(root) / "followup.json"


def load_followup(root: Path) -> Dict[str, int]:
    p = followup_path(root)
    if not p.exists():
        return {}
    try:
        data = json.loads(read_text(p))
        if not isinstance(data, dict):
            return {}
        out: Dict[str, int] = {}
        for k, v in data.items():
            try:
                n = int(v)
            except (TypeError, ValueError):
                continue
            # 负数 / 天文数字都是损坏数据：负数会永远触发不了 ≥2 阈值，
            # 等于把补丁循环闸静默关掉。钳到 0..9999。
            out[str(k)] = max(0, min(n, 9999))
        return out
    except Exception:
        return {}


def save_followup(root: Path, data: Dict[str, int]) -> None:
    p = followup_path(root)
    atomic_write(p, json.dumps(data, ensure_ascii=False, indent=2))


def followup_bump(root: Path, tid: str, failed: bool) -> int:
    """记录同一 TASK 的连续失败轮次；PASS 则清零。返回当前计数。"""
    store = load_followup(root)
    if failed:
        store[tid] = store.get(tid, 0) + 1
        save_followup(root, store)
        return store[tid]
    if tid in store:
        store.pop(tid, None)
        save_followup(root, store)
    return 0


def warn_followup(tid: str, n: int) -> None:
    """同一 TASK 连续失败 ≥2 轮：判定为补丁循环，强制转 SPIKE。"""
    if n < 2:
        return
    print(file=sys.stderr)
    print(f"FOLLOWUP-GATE: {tid} 已连续失败 {n} 轮 — 停止打补丁", file=sys.stderr)
    print("  · 禁止再加判断、放宽断言、注释掉校验、加白名单特例", file=sys.stderr)
    print("  · 标 ⚠️ 回 /plan，由规划师立 SPIKE-* 定位根因后再拆 TASK", file=sys.stderr)
    print("  · 判据与五个高频反复区见 quality-checklists/references/patch-loop.md", file=sys.stderr)


def detect_verify_command(root: Path) -> Optional[str]:
    """plan 未设 VERIFY 时，回退探测项目既有的验收入口（不猜、只认实际存在的）。

    优先级按「跨平台可靠度」排序：跨平台命令在前，shell 脚本在后并做平台适配，
    避免在 Windows cmd.exe 下返回 `./x.sh` 这种必然失败的命令。
    """
    is_win = os.name == "nt"
    # 用「正在跑本脚本的解释器名」而非硬编码 python：
    # Linux/macOS 常见只有 python3，写死 python 会让回退探测的命令必然失败。
    py = Path(sys.executable).name or "python"

    # 1) Python 脚本 —— 跨平台最稳
    for rel in ("scripts/verify.py", "scripts/test.py", "verify.py", "test.py"):
        if (root / rel).is_file():
            return f"{py} {rel}"

    # 2) package.json（npm/npx 在 Windows 同样可用）
    pkg = root / "package.json"
    if pkg.exists():
        try:
            scripts = json.loads(read_text(pkg)).get("scripts") or {}
            if scripts.get("verify"):
                return "npm run verify"
            t = str(scripts.get("test", ""))
            if t and "no test specified" not in t:
                return "npm test"
        except Exception:
            pass

    # 3) pytest（配置或 tests/ 目录）
    if any((root / f).exists() for f in ("pyproject.toml", "pytest.ini", "tox.ini", "setup.cfg")):
        return "pytest -q"
    try:
        if any(root.glob("tests/test_*.py")) or any(root.glob("*/tests/test_*.py")):
            return "pytest -q"
    except Exception:
        pass

    # 4) shell 脚本 —— 放最后，Windows 需借 sh 执行
    for rel in ("scripts/verify.sh", "scripts/test.sh", "verify.sh"):
        if (root / rel).is_file():
            return f"sh {rel}" if is_win else f"./{rel}"

    return None


def evidence_path(root: Path) -> Path:
    return sop_dir(root) / "evidence.json"


def load_evidence(root: Path) -> Dict[str, Dict[str, str]]:
    p = evidence_path(root)
    if not p.exists():
        return {}
    try:
        data = json.loads(read_text(p))
        if not isinstance(data, dict):
            return {}
        # 结构校验：每个值必须是 dict 且 evidence 是字符串。
        # 只校验顶层 dict 会让 {"TASK-001": 123} 这种损坏数据溜进去，
        # 在 task-verify 里 have.get(...) 直接 AttributeError 崩溃（fail-open 的近亲）。
        out: Dict[str, Dict[str, str]] = {}
        for k, v in data.items():
            if isinstance(v, dict) and isinstance(v.get("evidence"), str):
                out[str(k)] = v
        return out
    except Exception:
        return {}


def save_evidence(root: Path, data: Dict[str, Dict[str, str]]) -> None:
    p = evidence_path(root)
    atomic_write(p, json.dumps(data, ensure_ascii=False, indent=2))


def cmd_task_verify(root: Path, task_id: Optional[str], evidence: Optional[str] = None) -> int:
    p = plan_path(root)
    if not p.exists():
        print("FAIL: plan 不存在")
        return 1
    text = read_text(p)
    meta = parse_meta(text)
    tid = task_id or meta.get("ACTIVE", "")
    if not tid or tid in ("(none)",):
        print("FAIL: 无 ACTIVE 任务 ID（请传 TASK_ID 或设置 ACTIVE）")
        return 1

    tasks = {t["id"]: t for t in parse_tasks(text)}
    t = tasks.get(tid)
    if not t:
        print(f"FAIL: plan 中找不到任务 {tid}")
        return 1

    acc = t["acceptance"]
    print(f"=== task-verify: {tid} ===")
    print(f"任务: {t['task']}")
    print(f"验收: {acc}")
    print(f"落点: {t['target']}")

    cmd = _acceptance_cmd(acc) or ""
    kind = classify_acceptance(acc)
    if kind == "manual" or cmd.startswith("manual:"):
        # 人工验收：必须留下证据才放行；否则返回 3（MANUAL-PENDING），不算 PASS
        ev_text = (evidence or "").strip()
        if ev_text:
            from datetime import datetime
            if len(ev_text) > 4000:
                ev_text = ev_text[:4000] + "…(已截断，完整证据请存文件并在证据里写路径)"
            with state_lock(root):
                store = load_evidence(root)
                store[tid] = {
                    "evidence": ev_text.replace("\r", " ").replace("\n", " "),
                    "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "acceptance": acc[:200],
                }
                save_evidence(root, store)
                followup_bump(root, tid, False)
            print(f"EVIDENCE: 已记录 {tid} 验收证据 → {ev_text}")
            print(f"PASS: {tid}（人工验收，证据已入档 .zcode/sop/evidence.json）")
            return 0
        store = load_evidence(root)
        have = store.get(tid, {})
        if have.get("evidence"):
            # 证据必须绑定当时的验收要求；plan 的 Acceptance 改过就失效。
            # 否则「验收要求被放宽/改坏」时旧证据仍能放行，是 fail-open。
            saved_acc = (have.get("acceptance") or "").strip()
            now_acc = acc[:200].strip()
            if saved_acc and saved_acc != now_acc:
                print("MANUAL-PENDING: 验收要求已变更，旧证据失效 — 请重新核对并留证", file=sys.stderr)
                print(f"  旧要求: {saved_acc}", file=sys.stderr)
                print(f"  新要求: {now_acc}", file=sys.stderr)
                print(f'  重留: python sop_gate.py task-verify {tid} --evidence "<新证据>"', file=sys.stderr)
                return 3
            if not saved_acc:
                # 老版本证据没有 acceptance 字段，无法确认对应哪版要求 → 保守重留
                print("MANUAL-PENDING: 旧证据未记录验收要求，无法确认仍有效 — 请重新留证", file=sys.stderr)
                return 3
            with state_lock(root):
                followup_bump(root, tid, False)
            print(f"PASS: {tid}（人工验收，已有证据 @{have.get('at', '?')}: {have['evidence']}）")
            return 0
        print("MANUAL-PENDING: 人工验收尚未留证 — 不视为 PASS", file=sys.stderr)
        print(f'  核对完成后执行: python sop_gate.py task-verify {tid} --evidence "<命令输出/截图路径/复核人>"', file=sys.stderr)
        print("  证据写入 .zcode/sop/evidence.json 并长期留档。", file=sys.stderr)
        return 3

    if kind == "exec" and cmd:
        rc = run_cmd(cmd, root)
        with state_lock(root):
            if rc == 0:
                followup_bump(root, tid, False)
            else:
                n = followup_bump(root, tid, True)
        if rc == 0:
            print(f"PASS: {tid}")
        else:
            print(f"FAIL: {tid} 验收命令退出码 {rc}（本任务连续失败 {n} 轮）")
            warn_followup(tid, n)
        return 0 if rc == 0 else 1

    # fail-closed
    print("FAIL: 验收列不可自动判定（描述性文字，禁止静默通过）", file=sys.stderr)
    print(f"      当前: {acc or '(空)'}", file=sys.stderr)
    print("      修法一: 写成可执行命令（npm test / pytest / python ...）", file=sys.stderr)
    print("      修法二: 显式写 manual: <步骤与证据要求>", file=sys.stderr)
    return 1


def cmd_verify(root: Path, force: bool = False) -> int:
    p = plan_path(root)
    if not p.exists():
        print("FAIL: plan 不存在")
        return 1
    text = read_text(p)
    meta = parse_meta(text)
    v = meta.get("VERIFY", "")
    auto = False
    if not v or v in ("(none)",):
        detected = detect_verify_command(root)
        if not detected:
            print("FAIL: VERIFY 未设置，且未探测到项目验收入口")
            print("      请在 plan 头部显式设定，例如：")
            print('        python sop_gate.py set VERIFY "npm test"')
            print("      探测范围：scripts/verify.sh · scripts/test.sh · package.json 的 verify/test · pytest 配置 · tests/")
            return 1
        v = detected
        auto = True
        print(f"WARN: VERIFY 未设置 — 已回退探测到：{v}")
        print(f'      建议固化写回 plan：python sop_gate.py set VERIFY "{v}"')

    # 前置 0：结构歧义（重复 ID / 状态混写）必须先拦下，否则后面取哪一行都能自圆其说
    for msg in task_structure_issues(text):
        print(f"FAIL: {msg}")
        return 1

    # 前置 0：必须真的解析到任务行，否则「零任务」会被误判成「全部完成」（fail-open）
    all_tasks = parse_tasks(text)
    main_tasks = [t for t in all_tasks if re.match(r"^TASK-\d+$", t["id"])]
    if not main_tasks and force:
        print("WARN: --force 放行「零任务」出口闸 —— 没有任何 TASK ✅ 能证明工作已完成，请在汇报中显式说明")
    if not main_tasks and not force:
        print(f"FAIL: plan 未解析到任何 TASK 行（共解析到 {len(all_tasks)} 条任务记录）")
        print("      出口闸靠「任务全部 ✅」证明做完了；解析不到任务 = 无法证明，不能放行。")
        print("      可能原因：plan.md 表格被改坏 / 被其它会话覆盖 / 只写了 SPIKE-REV-DOC。")
        print("      排查：python sop_gate.py doctor   看 plan 解析一节")
        print("      确认确实无需任务收尾时，加 --force。")
        return 1

    # 前置：Sprint 内任务必须全部 ✅（SPIKE/REV/DOC 不计入主路径）
    pending = [t["id"] for t in main_tasks if "✅" not in t["status"]]
    aux_pending = [
        t["id"] for t in all_tasks
        if not re.match(r"^TASK-\d+$", t["id"]) and "✅" not in t["status"]
    ]
    if aux_pending:
        print("提示: 辅助任务未完成（不阻塞出口闸）：" + ", ".join(aux_pending))
    if pending and not force:
        print("FAIL: 仍有未完成任务，不能收尾/发版：" + ", ".join(pending))
        print("      先把这些任务做完并 task-verify PASS、标 ✅；")
        print("      若确需跳过（用户明确接受残项），加 --force。")
        return 1
    if pending and force:
        print("WARN: --force 忽略未完成任务：" + ", ".join(pending))

    print("=== verify (Sprint / 打版前全量) ===")
    if auto:
        print(f"命令: {v}  [AUTO-DETECTED，非 plan 显式声明]")
    rc = run_cmd(v, root)
    if rc == 0:
        print("PASS: verify 全绿")
    else:
        print(f"FAIL: verify 退出码 {rc}")
    return 0 if rc == 0 else 1


def cmd_followup(root: Path, reset: bool = False, task_id: Optional[str] = None) -> int:
    """查看或清零「同一 TASK 连续失败轮次」——补丁循环的硬指标。"""
    if reset:
        removed = False
        with state_lock(root):
            store = load_followup(root)
            if task_id:
                if task_id in store:
                    store.pop(task_id)
                    save_followup(root, store)
                    removed = True
            else:
                save_followup(root, {})
        if task_id:
            print(f"OK: 已清零 {task_id} 的失败计数" if removed else f"SKIP: {task_id} 无失败计数")
        else:
            print("OK: 已清零全部失败计数")
        return 0

    store = load_followup(root)
    print("=== followup · 连续失败计数 ===")
    if not store:
        print("无记录 — 所有任务均未连续失败")
        return 0
    for k, n in sorted(store.items(), key=lambda x: -x[1]):
        flag = "  → 应转 SPIKE，停止打补丁" if n >= 2 else ""
        print(f"{k:<16} {n} 轮{flag}")
    if any(n >= 2 for n in store.values()):
        print()
        print("判据与处置见 quality-checklists/references/patch-loop.md")
    return 0


# ---------------------------------------------------------------------------
# release-check · 发版前置预检（吸收自 Super Cursor runner.sh）
# ---------------------------------------------------------------------------

def _list_git_tags(root: Path) -> List[str]:
    try:
        cp = subprocess.run(
            ["git", "tag", "--list"], cwd=str(root),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    except Exception:
        return []
    if cp.returncode != 0:
        return []
    return [ln.strip() for ln in (cp.stdout or "").splitlines() if ln.strip()]


def _parse_semver_tag(tag: str) -> Optional[Tuple[str, Tuple[int, int, int]]]:
    """从 tag 提取 (前缀, (major, minor, patch))；非 semver 返回 None。

    前缀 = tag 去掉尾部 semver 后的部分（如 'v' / 'release-' / ''）。
    next tag 复用同一前缀，保持仓库既有命名惯例。
    """
    m = re.search(r"(\d+)\.(\d+)\.(\d+)$", tag)
    if not m:
        return None
    prefix = tag[: m.start()]
    if prefix and not re.fullmatch(r"[A-Za-z0-9_.-]+", prefix):
        return None
    return prefix, (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def _bump_version(v: Tuple[int, int, int], bump: str) -> Tuple[int, int, int]:
    maj, mi, pa = v
    if bump == "major":
        return (maj + 1, 0, 0)
    if bump == "minor":
        return (maj, mi + 1, 0)
    return (maj, mi, pa + 1)


def cmd_release_check(root: Path, bump: Optional[str] = None) -> int:
    """发版前置预检：算 next_version、核 CHANGELOG 与 plan 残项。

    只预检不跑 VERIFY（出口闸仍由 verify 把守）；异常即 NOT-READY（fail-closed）。
    """
    print("=== release-check · 发版前置预检 ===")
    problems = 0

    # 1) 发版必须能打 tag → 必须 git 仓库
    try:
        cp = subprocess.run(
            ["git", "rev-parse", "--git-dir"], cwd=str(root),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if cp.returncode != 0:
            print("FAIL: 非 git 仓库 — 发版必须能打 annotated tag")
            return 1
    except Exception as e:
        print(f"FAIL: git 不可用（{type(e).__name__}）— 发版前置预检跑不了")
        return 1

    # 2) 工作区 WIP：只提示不拦（CHANGELOG / bump 通常就是此刻未提交的改动）
    try:
        cp = subprocess.run(
            ["git", "status", "--porcelain"], cwd=str(root),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        wip = [ln for ln in (cp.stdout or "").splitlines() if ln.strip()]
    except Exception:
        wip = []
    if wip:
        print(f"WARN 工作区有 {len(wip)} 处未提交改动（发版 commit 之前属正常；确认无意外残留）")
        for ln in wip[:5]:
            print(f"     {ln}")

    # 3) 版本解析：最新 semver tag → next_version（--bump > plan RELEASE_BUMP > patch）
    p = plan_path(root)
    meta: Dict[str, str] = {}
    if p.exists():
        meta = parse_meta(read_text(p))
    bump_eff = bump or (meta.get("RELEASE_BUMP") or "").strip() or "patch"
    tags = _list_git_tags(root)
    parsed_tags = []
    for t in tags:
        parsed = _parse_semver_tag(t)
        if parsed:
            parsed_tags.append(parsed)
    parsed_tags.sort(key=lambda x: x[1])
    if parsed_tags:
        prefix, latest_v = parsed_tags[-1]
        next_v = _bump_version(latest_v, bump_eff)
        latest_str = ".".join(str(n) for n in latest_v)
        next_str = ".".join(str(n) for n in next_v)
        print(f"latest_tag: {prefix}{latest_str}")
        print(f"next_version: {next_str}（bump={bump_eff}；--bump 或 plan RELEASE_BUMP 可改）")
        print(f"next_tag: {prefix}{next_str}")
        if f"{prefix}{next_str}" in tags:
            print(f"FAIL: {prefix}{next_str} 已存在 — 换 bump 档位或人工确认版本")
            problems += 1
    else:
        print("latest_tag: （无 semver tag）")
        print("next_version: 0.1.0（首个版本）")
        print("next_tag: v0.1.0（无历史惯例时用 v 前缀）")

    # 4) CHANGELOG [Unreleased] 检查（没有 CHANGELOG 的项目走 git log，跳过）
    cl = root / "CHANGELOG.md"
    if not cl.exists():
        print("INFO: 无 CHANGELOG.md — 跳过 Unreleased 检查（变更记录走 git log）")
    else:
        text = read_text(cl)
        m = re.search(r"^##\s*\[Unreleased\]\s*$", text, re.M)
        if not m:
            print("WARN: CHANGELOG 无 [Unreleased] 段 — 确认版本段是否已直接写好")
        else:
            rest = text[m.end():]
            m2 = re.search(r"^##\s*\[", rest, re.M)
            body = rest[: m2.start()] if m2 else rest
            if body.strip():
                print("OK: CHANGELOG [Unreleased] 有内容")
            else:
                print("WARN: CHANGELOG [Unreleased] 为空 — 本次发版要写什么？")

    # 5) plan 残项（与 verify 同口径：所有 TASK-* 必须 ✅）
    if p.exists():
        not_done = [
            t["id"] for t in parse_tasks(read_text(p))
            if t["id"].startswith("TASK-") and "✅" not in t["status"]
        ]
        if not_done:
            shown = ", ".join(not_done[:8]) + ("…" if len(not_done) > 8 else "")
            print(f"FAIL: plan 有未完成 TASK × {len(not_done)} — {shown}")
            problems += 1
        else:
            print("OK: plan TASK 全部 ✅")
    else:
        print("INFO: 无 plan（未用 SOP 流程）— 跳过任务检查")

    print()
    if problems:
        print("结论: NOT-READY — 先处理上述 FAIL 再打版")
        return 1
    print("结论: ready — 按发版清单继续（verify 仍必须 PASS，这里不替代出口闸）")
    return 0


# ---------------------------------------------------------------------------
# friction-log / friction-report · 摩擦度量（吸收自 Super Cursor runner.sh）
# ---------------------------------------------------------------------------

FRICTION_NAME = "friction.jsonl"


def friction_path(root: Path) -> Path:
    return sop_dir(root) / FRICTION_NAME


def cmd_friction_log(root: Path, task: str, rounds: int, rework: int,
                     verify: str, note: str) -> int:
    """追加一条任务摩擦记录到 .zcode/sop/friction.jsonl（JSONL，锁内写）。"""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", task or ""):
        die("task 必须是任务 ID（字母数字 . _ -），如 TASK-003")
    if rounds < 1 or rework < 0:
        die("rounds ≥ 1 且 rework ≥ 0")
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "task": task,
        "rounds": rounds,
        "rework": rework,
        "verify": verify,
        "note": (note or "")[:200],
    }
    sop_dir(root).mkdir(parents=True, exist_ok=True)
    with state_lock(root):
        with open(friction_path(root), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"OK: 已记录 {task}（rounds={rounds} rework={rework} verify={verify}）")
    return 0


def cmd_friction_report(root: Path) -> int:
    """汇总 friction.jsonl：通过率 / 平均轮次 / 返工 TOP / SPIKE 建议。

    与 followup 计数联动展示；坏行跳过并 WARN（fail-closed：不崩，但明示）。
    """
    print("=== friction-report · 摩擦汇总 ===")
    fp = friction_path(root)
    if not fp.exists():
        print("无记录 — 用 friction-log 逐 TASK 留痕（--task --verify --rounds --rework）")
        return 0
    entries: List[dict] = []
    bad = 0
    for ln in read_text(fp).splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            entries.append(json.loads(ln))
        except ValueError:
            bad += 1
    if bad:
        print(f"WARN 跳过 {bad} 行坏记录（非 JSON）")
    if not entries:
        print("无有效记录")
        return 0

    per_task: Dict[str, Dict[str, int]] = {}
    vc: Dict[str, int] = {"pass": 0, "fail": 0, "manual": 0}
    for e in entries:
        t = str(e.get("task", "?"))
        d = per_task.setdefault(t, {"logs": 0, "rounds": 0, "rework": 0, "fail": 0})
        d["logs"] += 1
        d["rounds"] += int(e.get("rounds", 1) or 1)
        d["rework"] += int(e.get("rework", 0) or 0)
        v = str(e.get("verify", "?"))
        vc[v] = vc.get(v, 0) + 1
        if v == "fail":
            d["fail"] += 1

    total = len(entries)
    pass_n = vc.get("pass", 0)
    rate = pass_n / total * 100 if total else 0.0
    log_total = sum(d["logs"] for d in per_task.values()) or 1
    avg_rounds = sum(d["rounds"] for d in per_task.values()) / log_total
    total_rework = sum(d["rework"] for d in per_task.values())
    print(f"记录 {total} 条 · 任务 {len(per_task)} 个 · verify 通过率 {rate:.0f}%"
          f"（pass {pass_n} / fail {vc.get('fail', 0)} / manual {vc.get('manual', 0)}）")
    print(f"平均轮次 {avg_rounds:.1f} · 总返工 {total_rework} 次")

    top = sorted(per_task.items(), key=lambda kv: (-kv[1]["rework"], -kv[1]["fail"]))[:5]
    if any(d["rework"] or d["fail"] for _, d in top):
        print("返工 TOP:")
        for t, d in top:
            if not (d["rework"] or d["fail"]):
                continue
            print(f"  {t:<16} rework={d['rework']} fail={d['fail']} rounds={d['rounds']}/{d['logs']}次")

    fu = load_followup(root)
    hot = {k: n for k, n in fu.items() if n >= 1}
    if hot:
        shown = ", ".join(f"{k}×{n}" for k, n in sorted(hot.items(), key=lambda x: -x[1]))
        print(f"followup 未清零: {shown}")
    spike = [t for t, d in per_task.items() if d["rework"] >= 2 or d["fail"] >= 2]
    if spike:
        print(f"高摩擦（rework≥2 或 fail≥2）: {', '.join(sorted(spike))} — 建议立 SPIKE，判据见 patch-loop.md")
    return 0


def cmd_next_task(root: Path, apply: bool = False) -> int:
    p = plan_path(root)
    if not p.exists():
        print("FAIL: plan 不存在")
        return 1
    text = read_text(p)
    meta = parse_meta(text)
    order = execution_order(text)
    tasks = {t["id"]: t for t in parse_tasks(text)}
    # 按执行顺序找第一个未完成的任务
    candidates = order if order else list(tasks.keys())
    skip_prefix = ("SPIKE-", "REV-", "DOC-")
    for tid in candidates:
        t = tasks.get(tid)
        if not t:
            continue
        if t["status"] not in STATUS_ACTIVE:
            continue
        if tid.startswith(skip_prefix):
            print(f"SKIP: {tid}（调研/审查类，不进入 /run 主路径）")
            continue
        print(f"NEXT: {tid}")
        print(f"      任务: {t['task']}")
        print(f"      验收: {t['acceptance']}")
        if apply:
            with state_lock(root):
                # 拿锁后重读，避免覆盖另一个会话刚写的 plan（编辑主权）
                latest = set_meta(set_meta(read_text(p), "ACTIVE", tid), "NEXT", tid)
                atomic_write(p, latest)
            print(f"APPLIED: ACTIVE={tid}（已写回 plan.md）")
        else:
            print("提示: 仅报告未改动 plan；要写回 ACTIVE 请加 --apply")
        return 0
    print("NONE: 无可执行 ACTIVE 任务（Sprint 可能已收尾）")
    return 0


def cmd_approve(root: Path, force: bool = False) -> int:
    p = plan_path(root)
    if not p.exists():
        print("FAIL: plan 不存在")
        return 1
    meta = parse_meta(read_text(p))

    # 前置硬校验 1：VERIFY 必须设置，否则出口闸永远走不通
    v = (meta.get("VERIFY") or "").strip()
    if (not v or v in ("(none)", "none")) and not force:
        print("BLOCK: VERIFY 未设置 — 批准前必须写入全量验收命令（否则 Sprint 收尾/发版必然 FAIL）")
        print('       修法: python sop_gate.py set VERIFY "<全量验收命令>"')
        return 1

    # 前置硬校验 2：plan 结构必须合格（规划期不校验 PLAN_APPROVED）
    if cmd_plan_check(root, for_approve=True) != 0 and not force:
        print("BLOCK: plan-check 未通过，拒绝 approve（确认无误可加 --force）")
        return 1

    today = date.today().isoformat()
    with state_lock(root):
        latest = read_text(p)
        latest = set_meta(latest, "PLAN_APPROVED", today)
        latest = set_meta(latest, "PLANNING", "false")
        atomic_write(p, latest)
    print(f"OK: 已写入 PLAN_APPROVED={today}，PLANNING=false — 闸门解锁，可 /run")
    return 0


def _meta_value_error(key: str, value: str) -> Optional[str]:
    """按键校验元数据值，防止 set 凭空造出一个「已批准」状态。"""
    v = value.strip()
    if key == "PLAN_APPROVED" and not approval_valid(v):
        return "PLAN_APPROVED 必须是 YYYY-MM-DD 真实日期（且通常由 approve 写入）"
    if key in ("PLANNING", "AUTONOMOUS"):
        if v.lower() not in ("true", "false", "1", "0", "yes", "no"):
            return f"{key} 只能是 true/false/1/0/yes/no"
    if key == "MAX_LOOPS":
        try:
            if not 1 <= int(v) <= 999:
                return "MAX_LOOPS 必须是 1..999 的整数"
        except ValueError:
            return "MAX_LOOPS 必须是 1..999 的整数"
    if key in ("ACTIVE", "NEXT", "LAST_DONE"):
        if v != "(none)" and not re.match(r"^(TASK|SPIKE|REV|DOC)-\d+$", v):
            return f"{key} 只能是 (none) 或 TASK/SPIKE/REV/DOC-<数字>"
    if key == "RELEASE_BUMP" and v not in ("patch", "minor", "major"):
        return "RELEASE_BUMP 只能是 patch/minor/major"
    return None


def cmd_set(root: Path, key: str, value: str) -> int:
    if key not in META_KEYS:
        die(f"未知元数据键 {key}；可用: {', '.join(META_KEYS)}")
    # 防元数据注入：value 里的 HTML 注释定界符会破坏 <!-- KEY: value --> 结构。
    # 虽然 parse_meta 用行首锚定让大多数注入无效，但拒绝比「寄希望于解析器」更稳。
    if "<!--" in value or "-->" in value or "\n" in value or "\r" in value:
        die(f"{key} 的值不能含 <!-- 、--> 或换行（会破坏 plan 元数据格式）")
    err = _meta_value_error(key, value)
    if err:
        die(err)
    p = plan_path(root)
    if not p.exists():
        print("FAIL: plan 不存在")
        return 1
    with state_lock(root):
        atomic_write(p, set_meta(read_text(p), key, value))
    print(f"OK: {key} = {value}")
    return 0


def _sh_quote_path(raw: str) -> str:
    """把路径包成 POSIX shell 单引号字面量，避免 `$` / 空格 / 反引号被展开。"""
    p = str(raw).replace("\\", "/")
    return "'" + p.replace("'", "'\\''") + "'"


def _sh_unquote_path(literal: str) -> str:
    """还原 _sh_quote_path 生成的单引号字面量，供 doctor 校验钩子内嵌路径。"""
    lit = literal.strip()
    if len(lit) >= 2 and lit.startswith("'") and lit.endswith("'"):
        return lit[1:-1].replace("'\\''", "'")
    return lit


def _sop_py_path() -> str:
    """返回本脚本的绝对路径（供 git hook 调用），用 POSIX 单引号安全包裹。

    路径可能含空格、`$`、反引号、`!`、`'` 等 shell 元字符。双引号下 `$var`
    会被展开（曾导致装到 `dir$name` 下的钩子路径被吃掉一半，闸门失效）；
    单引号下只有 `'` 需要特殊处理，标准做法是 `'...'\\''...'`。
    """
    return _sh_quote_path(str(Path(__file__).resolve()))


def cmd_install_hook(root: Path) -> int:
    git_dir = root / ".git"
    if not git_dir.exists():
        print("FAIL: 项目根下未找到 .git，无法安装 git hook")
        return 1
    hook = root / HOOK_REL
    hook.parent.mkdir(parents=True, exist_ok=True)
    if hook.exists() and not hook.is_file():
        print(f"FAIL: pre-commit 路径不是普通文件: {hook}", file=sys.stderr)
        return 1
    existing = read_text(hook) if hook.exists() else ""
    body = (HOOK_BODY
            .replace("__SOP_PY_PATH__", _sop_py_path())
            .replace("__SOP_PY_BIN__", _sh_quote_path(sys.executable or "")))

    # 只有起始标记没有结束标记 = 上次写入被中断 / 他人改坏了钩子。
    # 此时再插一遍会产生两个 BEGIN，后续 uninstall 会从第一个 BEGIN
    # 一路删到第二个 END，把用户自己的钩子内容一起吃掉。
    if HOOK_MARK_BEGIN in existing and HOOK_MARK_END not in existing:
        print("FAIL: pre-commit 里只有 sop-gate 起始标记、缺结束标记，拒绝重复安装", file=sys.stderr)
        print(f"      请先手工删除该残留标记或恢复钩子后再运行 install-hook: {hook}", file=sys.stderr)
        return 1

    if HOOK_MARK_BEGIN in existing:
        # 已装过：整体替换标记块，实现版本升级（如从只跑 plan-check 升到 plan+gate）
        pattern = re.compile(
            re.escape(HOOK_MARK_BEGIN) + r".*?" + re.escape(HOOK_MARK_END),
            re.DOTALL,
        )
        if pattern.search(existing):
            new = pattern.sub(body, existing, count=1)
            if new == existing:
                print("SKIP: pre-commit 已是最新 sop-gate 钩子")
                return 0
            atomic_write(hook, new)
            try:
                hook.chmod(0o755)
            except Exception:
                pass
            print(f"OK: 已升级 git pre-commit 硬闸门 → {hook}（plan-check + gate-check）")
            return 0

    # 保证 shebang 在顶部
    if existing.startswith("#!"):
        first_nl = existing.find("\n")
        new = existing[:first_nl + 1] + "\n" + body + "\n" + existing[first_nl + 1:]
    else:
        new = "#!/bin/sh\n" + body + "\n" + existing
    atomic_write(hook, new)
    try:
        hook.chmod(0o755)
    except Exception:
        pass
    print(f"OK: 已安装 git pre-commit 硬闸门 → {hook}（plan-check + gate-check）")
    print("提示：本机无 python3/python 时钩子软降级放行；闸门仍可由主理人手动执行。")
    return 0


def cmd_uninstall_hook(root: Path) -> int:
    hook = root / HOOK_REL
    if not hook.exists():
        print("SKIP: 无 pre-commit 钩子")
        return 0
    text = read_text(hook)
    pattern = re.compile(
        re.escape(HOOK_MARK_BEGIN) + r".*?" + re.escape(HOOK_MARK_END) + r"\n?",
        re.DOTALL,
    )
    new = pattern.sub("", text)
    if new == text:
        print("SKIP: 未发现 sop-gate 钩子标记")
        return 0
    atomic_write(hook, new)
    print(f"OK: 已卸载 sop-gate 钩子 → {hook}")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sop_gate.py",
        description="代码工程 SOP 硬约束闸门（跨平台·零依赖）",
    )
    p.add_argument("--root", dest="root_global", default=None, help="显式指定项目根")
    sub = p.add_subparsers(dest="cmd")

    pi = sub.add_parser("init", help="初始化 plan 工作副本")
    pi.add_argument("--force", action="store_true")
    pi.add_argument("--root")

    sub.add_parser("status", help="打印状态").add_argument("--root")
    sub.add_parser("doctor", help="环境与链路自检（排查为何跑不通）").add_argument("--root")
    sub.add_parser("gate-check", help="run 硬闸门").add_argument("--root")
    sub.add_parser("plan-check", help="plan 完整性检查").add_argument("--root")

    pv = sub.add_parser("task-verify", help="单任务验收（fail-closed，人工验收需证据）")
    pv.add_argument("task_id", nargs="?")
    pv.add_argument("--evidence", help="人工验收证据（命令输出/截图路径/复核人），写入 plan 留档")
    pv.add_argument("--root")

    pvf = sub.add_parser("verify", help="全量验收（要求任务全部完成）")
    pvf.add_argument("--force", action="store_true", help="忽略未完成任务，仅跑 VERIFY 命令")
    pvf.add_argument("--root")

    pn = sub.add_parser("next-task", help="下一 ACTIVE 任务")
    pn.add_argument("--apply", action="store_true", help="把结果写回 ACTIVE / NEXT")
    pn.add_argument("--root")

    pf = sub.add_parser("followup", help="查看/清零补丁循环计数（同一 TASK 连续失败轮次）")
    pf.add_argument("task_id", nargs="?")
    pf.add_argument("--reset", action="store_true", help="清零计数（可指定 task_id）")
    pf.add_argument("--root")

    pa = sub.add_parser("approve", help="写入 PLAN_APPROVED（含前置校验）")
    pa.add_argument("--force", action="store_true", help="跳过 VERIFY / plan-check 前置校验")
    pa.add_argument("--root")

    ps = sub.add_parser("set", help="设置元数据")
    ps.add_argument("key")
    ps.add_argument("value")
    ps.add_argument("--root")

    prc = sub.add_parser("release-check", help="发版前置预检（next_version / CHANGELOG / plan 残项）")
    prc.add_argument("--bump", choices=["patch", "minor", "major"],
                     help="覆盖 bump 档位（默认 patch；plan 可设 RELEASE_BUMP）")
    prc.add_argument("--root")

    pfl = sub.add_parser("friction-log", help="记一条任务摩擦数据（轮次/返工/验收结果）")
    pfl.add_argument("--task", required=True, help="任务 ID，如 TASK-003")
    pfl.add_argument("--verify", required=True, choices=["pass", "fail", "manual"])
    pfl.add_argument("--rounds", type=int, default=1, help="本轮 task-verify 跑了几轮（≥1）")
    pfl.add_argument("--rework", type=int, default=0, help="本轮引发的返工次数（≥0）")
    pfl.add_argument("--note", default="", help="一句话备注（≤200 字符）")
    pfl.add_argument("--root")

    sub.add_parser("friction-report", help="汇总摩擦数据（通过率/轮次/返工 TOP/SPIKE 建议）").add_argument("--root")

    sub.add_parser("install-hook", help="安装 git pre-commit").add_argument("--root")
    sub.add_parser("uninstall-hook", help="卸载 git pre-commit").add_argument("--root")
    return p


def _ensure_utf8_pipes() -> None:
    """管道 / 重定向时统一用 UTF-8 输出。

    Windows 的控制台代码页（常见 cp936）会让被捕获的输出变成乱码，
    agent 与 CI 读到的就是「�」。交互式终端保持原编码，人类照样看得懂。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            if not stream.isatty():
                stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def main() -> int:
    _ensure_utf8_pipes()
    parser = build_parser()
    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return 2
    explicit = getattr(args, "root", None) or args.root_global
    root = _detect_root(explicit)

    dispatch = {
        "init": lambda: cmd_init(root, args.force),
        "status": lambda: cmd_status(root),
        "doctor": lambda: cmd_doctor(root),
        "gate-check": lambda: cmd_gate_check(root),
        "plan-check": lambda: cmd_plan_check(root),
        "task-verify": lambda: cmd_task_verify(root, getattr(args, "task_id", None), getattr(args, "evidence", None)),
        "verify": lambda: cmd_verify(root, getattr(args, "force", False)),
        "next-task": lambda: cmd_next_task(root, getattr(args, "apply", False)),
        "followup": lambda: cmd_followup(root, getattr(args, "reset", False), getattr(args, "task_id", None)),
        "approve": lambda: cmd_approve(root, getattr(args, "force", False)),
        "set": lambda: cmd_set(root, args.key, args.value),
        "release-check": lambda: cmd_release_check(root, getattr(args, "bump", None)),
        "friction-log": lambda: cmd_friction_log(
            root, args.task, args.rounds, args.rework, args.verify, args.note),
        "friction-report": lambda: cmd_friction_report(root),
        "install-hook": lambda: cmd_install_hook(root),
        "uninstall-hook": lambda: cmd_uninstall_hook(root),
    }
    try:
        return dispatch[args.cmd]()
    except KeyboardInterrupt:
        print("BLOCK: 用户中断（rc=130）— 不视为 PASS", file=sys.stderr)
        return 130
    except Exception as e:  # 最后兜底：宁可 BLOCK，也不给 Traceback + 假绿灯
        print(f"INTERNAL-ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        print("      闸门按 BLOCK 处理。请运行 doctor 排查，或把完整输出回报给专家团。", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
