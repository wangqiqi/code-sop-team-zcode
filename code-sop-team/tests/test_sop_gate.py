#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sop_gate.py 回归测试（Python 标准库 unittest，零依赖）。

运行：
    python tests/test_sop_gate.py
    python -m unittest discover -s tests -v

覆盖：闸门语义、畸形输入 fail-closed、跨平台、状态竞态、已修 bug 的回归。
每个用例在独立临时 git 仓库中跑，互不污染。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parent.parent
SOP = PKG_ROOT / "bin" / "sop_gate.py"

PLAN_OK = """<!-- VERIFY: echo all-green -->
<!-- PLANNING: true -->
<!-- SPRINT: S1 -->
<!-- PLAN_APPROVED: (none) -->
<!-- ACTIVE: TASK-001 -->
<!-- NEXT: (none) -->

# Plan

| ID | Task | Priority | Status | Acceptance | Target |
|----|------|----------|--------|------------|--------|
| TASK-001 | 检查脚本 | P0 | ⬜ | `echo ok` | scripts/ |

**执行顺序**: `TASK-001`
"""


class GateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sop-test-"))
        subprocess.run(["git", "init", "-q", str(self.tmp)], check=False, capture_output=True)
        self.plan = self.tmp / ".zcode/sop/plan.md"
        self.run_gate("init")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_gate(self, *args, env=None, check=False):
        e = os.environ.copy()
        if env:
            e.update(env)
        r = subprocess.run(
            [sys.executable, str(SOP), *args, "--root", str(self.tmp)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=e, timeout=30,
        )
        if check:
            self.assertEqual(r.returncode, 0, f"{args}: rc={r.returncode}\n{r.stdout}\n{r.stderr}")
        return r

    def write_plan(self, text):
        self.plan.parent.mkdir(parents=True, exist_ok=True)
        self.plan.write_text(text, encoding="utf-8")

    def mark_done(self, tid="TASK-001"):
        t = self.plan.read_text(encoding="utf-8")
        self.plan.write_text(t.replace(f"| {tid} |", f"| {tid} |", 1).replace("| ⬜ |", "| ✅ |", 1), encoding="utf-8")

    # ---- 基础链路 ----

    def test_01_init_idempotent_and_gitignore(self):
        gi = self.tmp / ".gitignore"
        self.assertIn(".zcode/sop/", gi.read_text(encoding="utf-8"))
        before = gi.read_text(encoding="utf-8")
        self.run_gate("init")
        self.assertEqual(gi.read_text(encoding="utf-8"), before, "init 应幂等，不重复写 .gitignore")

    def test_02_gate_check_blocks_before_approve(self):
        self.write_plan(PLAN_OK)
        self.assertEqual(self.run_gate("gate-check").returncode, 1)

    def test_03_approve_unlocks(self):
        self.write_plan(PLAN_OK)
        self.assertEqual(self.run_gate("approve").returncode, 0)
        self.assertEqual(self.run_gate("gate-check").returncode, 0)

    def test_04_task_verify_exec_pass(self):
        self.write_plan(PLAN_OK)
        self.assertEqual(self.run_gate("task-verify", "TASK-001").returncode, 0)

    def test_05_task_verify_prose_fails_closed(self):
        self.write_plan(PLAN_OK.replace("`echo ok` | scripts/", "功能正常 | scripts/"))
        self.assertEqual(self.run_gate("task-verify", "TASK-001").returncode, 1)

    def test_06_manual_without_evidence_pending(self):
        self.write_plan(PLAN_OK.replace("`echo ok`", "manual: 检查登录页"))
        self.assertEqual(self.run_gate("task-verify", "TASK-001").returncode, 3)

    def test_07_manual_with_evidence_pass(self):
        self.write_plan(PLAN_OK.replace("`echo ok`", "manual: 检查登录页"))
        self.assertEqual(self.run_gate("task-verify", "TASK-001", "--evidence", "复核人A, a.png").returncode, 0)

    def test_08_manual_evidence_bound_to_acceptance(self):
        """BUG-1 回归：验收要求变更后旧证据必须失效。"""
        self.write_plan(PLAN_OK.replace("`echo ok`", "manual: 检查登录页有验证码"))
        self.run_gate("task-verify", "TASK-001", "--evidence", "复核人A, a.png")
        self.write_plan(PLAN_OK.replace("`echo ok`", "manual: 核对生产库备份可恢复"))
        self.assertEqual(self.run_gate("task-verify", "TASK-001").returncode, 3,
                         "验收要求变了，旧证据必须失效")

    def test_09_verify_requires_done_tasks(self):
        self.write_plan(PLAN_OK)
        self.assertEqual(self.run_gate("verify").returncode, 1)

    def test_10_verify_zero_tasks_fail_closed(self):
        """BUG-2 回归：plan 无任务时不能当成全部完成。"""
        self.write_plan("<!-- VERIFY: echo ok -->\n\n# Plan\n\n表格写坏了\n")
        self.assertEqual(self.run_gate("verify").returncode, 1)

    def test_11_followup_counts_and_resets(self):
        self.write_plan(PLAN_OK.replace("`echo ok`", "python -c \"raise SystemExit(1)\""))
        self.run_gate("task-verify", "TASK-001")
        r = self.run_gate("task-verify", "TASK-001")
        self.assertIn("FOLLOWUP-GATE", r.stderr)
        fu = json.loads((self.tmp / ".zcode/sop/followup.json").read_text(encoding="utf-8"))
        self.assertEqual(fu["TASK-001"], 2)
        self.run_gate("followup", "--reset")
        self.assertNotIn("TASK-001", (self.tmp / ".zcode/sop/followup.json").read_text(encoding="utf-8"))

    def test_12_timeout_protection(self):
        self.write_plan(PLAN_OK.replace("<!-- VERIFY: echo all-green -->",
                                        '<!-- VERIFY: python -c "import time;time.sleep(30)" -->'))
        # 任务标完成才能进到命令执行
        t = self.plan.read_text(encoding="utf-8")
        self.plan.write_text(t.replace("| ⬜ |", "| ✅ |"), encoding="utf-8")
        r = self.run_gate("verify", env={"SOP_VERIFY_TIMEOUT": "1"})
        self.assertEqual(r.returncode, 1)
        self.assertIn("未退出", r.stderr + r.stdout)
        self.assertIn("SOP_VERIFY_TIMEOUT", r.stderr + r.stdout)

    # ---- 本轮新发现的 bug 回归 ----

    def test_13_pipeline_in_acceptance_not_truncated(self):
        """BUG-3 回归：Acceptance 的管道符不能被表格解析截断。"""
        self.write_plan(PLAN_OK.replace("`echo ok`", "`echo hello | grep hello`"))
        r = self.run_gate("task-verify", "TASK-001")
        self.assertEqual(r.returncode, 0, f"含管道符的验收命令应完整执行：{r.stdout}\n{r.stderr}")
        self.assertIn("验收: `echo hello | grep hello`", r.stdout)

    def test_14_escaped_pipeline_in_acceptance(self):
        """BUG-3b：markdown 转义的 \\| 应还原为管道符。"""
        self.write_plan(PLAN_OK.replace("`echo ok`", "`echo hello \\| grep hello`"))
        r = self.run_gate("task-verify", "TASK-001")
        self.assertEqual(r.returncode, 0, f"转义管道符应还原执行：{r.stdout}\n{r.stderr}")
        self.assertIn("验收: `echo hello | grep hello`", r.stdout)

    def test_15_detect_uses_current_interpreter(self):
        """BUG-4 回归：VERIFY 回退探测不能用机器上不存在的 python。"""
        (self.tmp / "scripts").mkdir(exist_ok=True)
        (self.tmp / "scripts/verify.py").write_text("print('ok')\n", encoding="utf-8")
        plan = PLAN_OK.replace("<!-- VERIFY: echo all-green -->", "<!-- VERIFY: (none) -->")
        self.write_plan(plan.replace("| ⬜ |", "| ✅ |"))
        r = self.run_gate("verify")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("探测", r.stdout)
        # 探测出的命令必须是当前解释器的可执行名，不能是硬编码 python
        py_name = Path(sys.executable).name  # python / python3 / python.exe
        self.assertIn(f"{py_name} scripts/verify.py", r.stdout)

    def test_16_hook_path_with_dollar_safe(self):
        """BUG-5 回归：脚本装在含 $ 的路径时，钩子路径不能被 shell 展开。"""
        # 把脚本复制到含 $ 的路径，再从该路径安装钩子
        weird = self.tmp / "dir$name"
        weird.mkdir(exist_ok=True)
        subprocess.run(["git", "init", "-q", str(weird)], capture_output=True)
        copied = weird / "sop_gate_copy.py"
        shutil.copy2(SOP, copied)
        r = subprocess.run(
            [sys.executable, str(copied), "install-hook", "--root", str(weird)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        body = (weird / ".git/hooks/pre-commit").read_text(encoding="utf-8")
        self.assertIn("dir$name", body, "钩子里的路径不能被 shell 展开掉 $name")
        self.assertNotIn('_SOP_PY="', body, "应用单引号而非双引号引用路径")
        self.assertIn("_SOP_PY='", body)

    def test_16b_hook_blocks_if_script_missing(self):
        """BUG-5b：闸门脚本不存在时 fail-closed（曾静默放行）。"""
        # 安装时脚本存在
        self.write_plan(PLAN_OK)
        self.run_gate("install-hook")
        body = (self.tmp / ".git/hooks/pre-commit").read_text(encoding="utf-8")
        self.assertIn("[ ! -f", body, "钩子应检查脚本是否存在")
        self.assertIn("exit 1", body, "脚本缺失应 BLOCK 而非放行")

    def test_17_malformed_evidence_no_crash(self):
        """BUG-6 回归：evidence.json 结构损坏不能崩溃，应 fail-closed。"""
        self.write_plan(PLAN_OK.replace("`echo ok`", "manual: 检查登录页"))
        ev = self.tmp / ".zcode/sop/evidence.json"
        for bad in ('{"TASK-001": 123}', '{"TASK-001": "abc"}', '{"TASK-001": []}', '{', '[]'):
            ev.write_text(bad, encoding="utf-8")
            r = self.run_gate("task-verify", "TASK-001")
            self.assertNotIn("Traceback", r.stderr, f"畸形 evidence {bad} 导致崩溃")
            self.assertIn(r.returncode, (0, 3), f"畸形 evidence {bad} rc={r.returncode}")

    def test_18_doctor_detects_corrupt_evidence(self):
        ev = self.tmp / ".zcode/sop/evidence.json"
        ev.write_text('{"TASK-001": 123}', encoding="utf-8")
        r = self.run_gate("doctor")
        self.assertIn("损坏", r.stdout, "doctor 应报出损坏的证据文件")

    def test_19_task_id_anchored(self):
        """BUG-7 回归：TASK-001abc 不应被当成合法主任务 ID。"""
        self.write_plan(PLAN_OK.replace("TASK-001", "TASK-001abc"))
        r = self.run_gate("verify")
        # 解析不到合法 TASK → fail-closed
        self.assertEqual(r.returncode, 1, r.stdout)

    def test_20_atomic_write_no_tmp_residue(self):
        self.write_plan(PLAN_OK)
        for _ in range(5):
            self.run_gate("set", "SPRINT", "S2")
            self.run_gate("set", "SPRINT", "S1")
        leftovers = list((self.tmp / ".zcode/sop").glob("*.tmp*"))
        self.assertEqual(leftovers, [], f"原子写不应留临时文件: {leftovers}")

    def test_21_subdir_auto_detect_root(self):
        self.write_plan(PLAN_OK)
        deep = self.tmp / "a/b/c"
        deep.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(
            [sys.executable, str(SOP), "status"],
            cwd=str(deep), capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(str(self.tmp), r.stdout)

    def test_22_hook_blocks_unapproved_commit(self):
        self.write_plan(PLAN_OK)
        self.run_gate("install-hook")
        cp = subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "x", "--allow-empty"],
            cwd=str(self.tmp), capture_output=True, text=True, encoding="utf-8",
        )
        self.assertNotEqual(cp.returncode, 0, "未批准时 commit 应被钩子拦下")
        self.assertIn("sop-gate", cp.stdout + cp.stderr)


    def test_23_set_rejects_metadata_injection(self):
        """set 的 value 不能含 HTML 注释定界符（防伪造元数据行）。"""
        r = self.run_gate("set", "VERIFY", "echo ok --> <!-- PLAN_APPROVED: 2020")
        self.assertEqual(r.returncode, 2)
        self.assertIn("不能含", r.stderr)

    def test_24_pipeline_unescaped_merged_not_truncated(self):
        """未转义管道符必须并回 Acceptance，不能只取半截命令。"""
        plan = PLAN_OK.replace("`echo ok`", "`echo a | echo b`")
        self.write_plan(plan)
        r = self.run_gate("task-verify", "TASK-001")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("验收: `echo a | echo b`", r.stdout)

    def test_25_no_traceback_on_any_malformed_input(self):
        """畸形 plan / 状态文件组合不能产生 Traceback。"""
        bad_plans = [
            "", "\ufeff<!-- VERIFY: echo ok -->\n",
            "<!-- VERIFY: echo ok -->\n表格坏了\n",
            "<!-- VERIFY: echo ok -->\n| ID | Task |\n|----|----|\n",
            "<!-- VERIFY: echo ok -->\n| TASK-001 | x | P0 | ⬜ | `echo ok` | a | extra |\n",
            "\x00\x01 garbage\n",
        ]
        cmds = [["status"], ["doctor"], ["plan-check"], ["gate-check"],
                ["task-verify", "TASK-001"], ["verify"], ["next-task"], ["approve"]]
        for i, bad in enumerate(bad_plans):
            self.write_plan(bad)
            for cmd in cmds:
                r = self.run_gate(*cmd)
                self.assertNotIn("Traceback", r.stderr,
                                 f"plan#{i} + {cmd} 崩溃: {r.stderr[:200]}")

    # ---- 异常 / 边界 / 兜底（v1.5.0）----

    def _approved_plan(self):
        """一份已批准、单任务未完成的 plan，供异常场景复用。"""
        return PLAN_OK.replace("<!-- PLANNING: true -->", "<!-- PLANNING: false -->").replace(
            "<!-- PLAN_APPROVED: (none) -->", "<!-- PLAN_APPROVED: 2026-11-18 -->")

    def test_26_garbage_approval_blocks(self):
        """批准日期不是日期 → 不能解锁闸门（原来任意非空字符串都放行）。"""
        self.write_plan(self._approved_plan().replace("PLAN_APPROVED: 2026-11-18",
                                                      "PLAN_APPROVED: hacked"))
        r = self.run_gate("gate-check")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("PLAN_APPROVED", r.stdout + r.stderr)

    def test_27_blank_evidence_is_pending(self):
        """空白证据不能算人工验收 PASS（原来 '   ' 也能留证放行）。"""
        self.write_plan(self._approved_plan().replace("`echo ok`", "manual: 检查页面"))
        r = self.run_gate("task-verify", "TASK-001", "--evidence", "   ")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        ev = self.tmp / ".zcode/sop/evidence.json"
        self.assertFalse(ev.exists(), "空白证据不应写入 evidence.json")

    def test_28_duplicate_task_ids_fail_closed(self):
        """重复 TASK ID 不能被后者覆盖造成假完成。"""
        dup = self._approved_plan().replace(
            "| TASK-001 | 检查脚本 | P0 | ⬜ | `echo ok` | scripts/ |",
            "| TASK-001 | 已完成 | P0 | ✅ | `echo ok` | scripts/ |\n"
            "| TASK-001 | 未完成 | P0 | ⬜ | `echo ok` | scripts/ |")
        self.write_plan(dup)
        for cmd in (["plan-check"], ["verify"]):
            r = self.run_gate(*cmd)
            self.assertEqual(r.returncode, 1, f"{cmd}: {r.stdout}{r.stderr}")
            self.assertIn("重复", r.stdout + r.stderr)

    def test_29_ambiguous_status_fails_closed(self):
        """⬜ + ✅ 混写不能既算活跃又算完成。"""
        amb = self._approved_plan().replace("| P0 | ⬜ |", "| P0 | ⬜ ✅ |")
        self.write_plan(amb)
        for cmd in (["plan-check"], ["verify"]):
            r = self.run_gate(*cmd)
            self.assertEqual(r.returncode, 1, f"{cmd}: {r.stdout}{r.stderr}")
            self.assertIn("状态", r.stdout + r.stderr)

    def test_30_orphan_hook_marker_rejected(self):
        """钩子只残留起始标记时不能再插一遍（会造成卸载误删他人脚本）。"""
        self.write_plan(self._approved_plan())
        self.run_gate("install-hook")
        hook = self.tmp / ".git/hooks/pre-commit"
        body = hook.read_text(encoding="utf-8")
        orphan = body.replace("# <<< code-sop-gate <<<", "")
        hook.write_text(orphan, encoding="utf-8")
        r = self.run_gate("install-hook")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(hook.read_text(encoding="utf-8"), orphan, "失败时不能改动原钩子")
        self.assertIn("标记", r.stderr)

    def test_31_huge_timeout_no_traceback(self):
        """超时值越界要钳制并警告，不能抛 Traceback。"""
        self.write_plan(self._approved_plan().replace("| ⬜ |", "| ✅ |"))
        r = self.run_gate("verify", env={"SOP_VERIFY_TIMEOUT": "1" + "0" * 30})
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("SOP_VERIFY_TIMEOUT", r.stdout + r.stderr)

    def test_32_invalid_env_root_rejected(self):
        """SOP_PROJECT_ROOT 指错要报错，不能悄悄退回 cwd 跑错项目。"""
        e = os.environ.copy()
        e["SOP_PROJECT_ROOT"] = str(self.tmp / "no-such-dir")
        r = subprocess.run(
            [sys.executable, str(SOP), "status", "--root", str(self.tmp)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", env=e,
        )
        # 显式 --root 优先，仍应成功；单独测 env 时才报错
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r2 = subprocess.run(
            [sys.executable, str(SOP), "status"],
            cwd=str(self.tmp), capture_output=True, text=True, encoding="utf-8", errors="replace", env=e,
        )
        self.assertEqual(r2.returncode, 2, r2.stdout + r2.stderr)
        self.assertIn("SOP_PROJECT_ROOT", r2.stderr)

    def test_33_gitignore_glob_is_idempotent(self):
        """用户已有 .zcode/sop/* 时 init 不应重复追加。"""
        gi = self.tmp / ".gitignore"
        gi.write_text(".zcode/sop/*\n", encoding="utf-8")
        self.run_gate("init")
        self.assertEqual(gi.read_text(encoding="utf-8").count(".zcode/sop/"), 1)

    def test_34_plan_path_is_directory_no_traceback(self):
        """plan.md 被误建成目录时不能崩溃，闸门 fail-closed。"""
        self.plan.unlink(missing_ok=True)
        self.plan.mkdir(parents=True)
        for cmd in (["status"], ["plan-check"], ["gate-check"], ["task-verify", "TASK-001"], ["verify"]):
            r = self.run_gate(*cmd)
            self.assertNotIn("Traceback", r.stderr, f"{cmd} 崩溃: {r.stderr[:200]}")
            self.assertNotEqual(r.returncode, 0, f"{cmd} 不应放行目录型 plan")

    def test_35_prefer_executable_backtick(self):
        """多个反引号时选可执行命令，而不是路径片段。"""
        self.write_plan(self._approved_plan().replace("`echo ok`", "在 `src/` 目录执行 `echo ok`"))
        r = self.run_gate("task-verify", "TASK-001")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("执行验收命令: echo ok", r.stdout)

    def test_36_negative_followup_clamped(self):
        """负的失败计数不能污染 followup 视图。"""
        (self.tmp / ".zcode/sop/followup.json").write_text(
            '{"TASK-001": -5}', encoding="utf-8")
        r = self.run_gate("followup")
        self.assertNotIn("-5", r.stdout)
        self.assertIn("0 轮", r.stdout)

    def test_37_no_lock_residue_and_contention_blocked(self):
        """状态锁用后清理；残留锁在超时后 fail-closed 而不是硬等。"""
        self.write_plan(self._approved_plan())
        self.assertEqual(self.run_gate("task-verify", "TASK-001").returncode, 0)
        lock = self.tmp / ".zcode/sop/.lock"
        self.assertFalse(lock.exists(), "状态锁必须释放，不能留下死锁")
        # 放一个「刚创建」的锁，模拟另一进程正在写 → 应在等待后 BLOCK
        lock.mkdir()
        (lock / "owner.json").write_text(
            json.dumps({"pid": -1, "ts": __import__("time").time()}), encoding="utf-8")
        r = self.run_gate("set", "SPRINT", "S2", env={"SOP_STATE_LOCK_WAIT": "0.2"})
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("锁", r.stdout + r.stderr)
        # 过期锁应被自动清理后正常执行
        (lock / "owner.json").write_text(
            json.dumps({"pid": -1, "ts": 0}), encoding="utf-8")
        self.assertEqual(self.run_gate("set", "SPRINT", "S2").returncode, 0)

    def test_38_force_zero_tasks_warns(self):
        """--force 零任务放行必须显式警告，不能静默。"""
        self.write_plan("<!-- VERIFY: echo ok -->\n<!-- PLAN_APPROVED: 2026-11-18 -->\n\n表格坏了\n")
        r = self.run_gate("verify", "--force")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("零任务", r.stdout + r.stderr)

    def test_39_set_validates_key_values(self):
        """set 对关键键做值校验，防止凭空造出批准日期/非法开关。"""
        for key, val in (("PLAN_APPROVED", "hacked"), ("PLANNING", "maybe"),
                         ("MAX_LOOPS", "abc")):
            r = self.run_gate("set", key, val)
            self.assertEqual(r.returncode, 2, f"{key}={val}: {r.stdout}{r.stderr}")
        self.assertEqual(self.run_gate("set", "PLAN_APPROVED", "2026-11-18").returncode, 0)
        self.assertEqual(self.run_gate("set", "PLANNING", "false").returncode, 0)
        self.assertEqual(self.run_gate("set", "MAX_LOOPS", "15").returncode, 0)

    def test_40_doctor_reports_lock_and_validation(self):
        """doctor 应把新增的失效模式纳入自检输出。"""
        r = self.run_gate("doctor")
        self.assertIn("状态锁", r.stdout)
        self.assertIn("批准格式", r.stdout)

    def test_41_hook_embeds_current_interpreter(self):
        """钩子要内嵌当前解释器绝对路径：普通 Windows 无 Python，会话解释器也不在 PATH。"""
        self.write_plan(self._approved_plan())
        self.assertEqual(self.run_gate("install-hook").returncode, 0)
        body = (self.tmp / ".git/hooks/pre-commit").read_text(encoding="utf-8")
        self.assertIn("_SOP_PY_BIN='", body)
        self.assertIn("$_SOP_PY_BIN", body)
        self.assertIn(Path(sys.executable).name, body, "应嵌入当前解释器（ZCode 会话解释器）")

    def test_42_doctor_detects_stale_hook(self):
        """钩子内嵌路径失效时 doctor 必须 FAIL：不能「报 OK 但钩子已软降级」。"""
        import re
        self.write_plan(self._approved_plan())
        self.assertEqual(self.run_gate("install-hook").returncode, 0)
        hook = self.tmp / ".git/hooks/pre-commit"
        body = hook.read_text(encoding="utf-8")
        body = re.sub(r"^_SOP_PY=.*$", "_SOP_PY='/definitely/missing/sop_gate.py'", body, flags=re.M)
        body = re.sub(r"^_SOP_PY_BIN=.*$", "_SOP_PY_BIN='/definitely/missing/python.exe'", body, flags=re.M)
        hook.write_text(body, encoding="utf-8")
        r = self.run_gate("doctor", env={"PATH": ""})
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("钩子脚本路径失效", r.stdout)
        self.assertIn("钩子解释器失效", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
