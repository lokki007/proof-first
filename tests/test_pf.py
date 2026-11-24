"""Tests for hooks/pf.py. Run: python -m unittest discover tests

Transcripts are synthetic, modelled on real Claude Code and Codex CLI session
files and hook payloads (captured 2026-11, Claude Code 2.1, Codex CLI 0.169).
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

PF = Path(__file__).resolve().parents[1] / "hooks" / "pf.py"


# --- transcript builders ----------------------------------------------------

def claude_user(text, pid):
    return {"type": "user", "promptId": pid, "message": {"role": "user", "content": text}}


def claude_assistant(blocks, model="claude-test-1"):
    return {"type": "assistant", "message": {"role": "assistant", "model": model, "content": blocks}}


def claude_tool_result():
    return {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "x", "content": "ok"}]}}


def tool(name, **inp):
    return {"type": "tool_use", "id": "t", "name": name, "input": inp}


def text(t):
    return {"type": "text", "text": t}


def claude_turn(pid, prompt, tools=(), final="ok"):
    lines = [claude_user(prompt, pid)]
    for t in tools:
        lines += [claude_assistant([t]), claude_tool_result()]
    lines.append(claude_assistant([text(final)]))
    return lines


def codex_turn(tid, prompt, items=(), final="ok", model="gpt-test"):
    ev = lambda p: {"type": "event_msg", "payload": p}
    lines = [ev({"type": "task_started", "turn_id": tid}),
             {"type": "turn_context", "payload": {"turn_id": tid, "model": model}},
             ev({"type": "item_completed", "turn_id": tid,
                 "item": {"type": "UserMessage", "content": [{"type": "text", "text": prompt}]}})]
    for it in items:
        lines.append(ev({"type": "item_completed", "turn_id": tid, "item": it}))
    lines.append(ev({"type": "task_complete", "turn_id": tid, "last_agent_message": final}))
    return lines


def file_change():
    return {"type": "FileChange", "changes": {"note.txt": {"type": "add"}}}


def command(cmd):
    return {"type": "CommandExecution", "command": ["pwsh", "-Command", cmd]}


class PFTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "pfhome"
        self.env = dict(os.environ, PROOF_FIRST_HOME=str(self.home))
        self.env.pop("PROOF_FIRST_MODE", None)

    def tearDown(self):
        self.tmp.cleanup()

    # helpers
    def transcript(self, lines, codex=False):
        d = Path(self.tmp.name) / (".codex/sessions" if codex else ".claude/projects/p")
        d.mkdir(parents=True, exist_ok=True)
        p = d / ("rollout-test.jsonl" if codex else "session.jsonl")
        p.write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")
        return str(p)

    def run_pf(self, cmd, payload, mode=None):
        env = dict(self.env)
        if mode:
            env["PROOF_FIRST_MODE"] = mode
        data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        r = subprocess.run([sys.executable, str(PF), cmd], input=data, env=env,
                           capture_output=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout) if r.stdout.strip() else None

    def events(self):
        log = self.home / "log.jsonl"
        if not log.exists():
            return []
        return [json.loads(l)["event"] for l in log.read_text(encoding="utf-8").splitlines()]

    def stop(self, tp, key, final, mode=None, **extra):
        payload = {"session_id": "s1", "transcript_path": tp, "cwd": self.tmp.name,
                   "hook_event_name": "Stop", "stop_hook_active": False,
                   "last_assistant_message": final, **extra}
        payload["turn_id" if "codex" in tp else "prompt_id"] = key
        return self.run_pf("stop", payload, mode)

    # --- stop gate ------------------------------------------------------------
    def test_claude_missing_proof_blocks_in_block_mode(self):
        tp = self.transcript(claude_turn("p1", "make it", [tool("Edit", file_path="a.py")], "Done."))
        out = self.stop(tp, "p1", "Done.", mode="block")
        self.assertEqual(out["decision"], "block")
        self.assertIn("Proof: seen", out["reason"])
        self.assertEqual(self.events(), ["gate_block"])

    def test_warn_mode_is_default_and_never_blocks(self):
        tp = self.transcript(claude_turn("p1", "make it", [tool("Edit", file_path="a.py")], "Done."))
        self.assertIsNone(self.stop(tp, "p1", "Done."))
        self.assertEqual(self.events(), ["gate_warn"])

    def test_proof_with_evidence_passes(self):
        final = "Fixed.\nProof: tested — pytest passed (12 tests)"
        tp = self.transcript(claude_turn("p1", "fix", [tool("Edit", file_path="a.py"),
                                                       tool("Bash", command="pytest -q")], final))
        self.assertIsNone(self.stop(tp, "p1", final, mode="block"))
        self.assertEqual(self.events(), ["pass"])

    def test_seen_without_visual_evidence_blocks(self):
        final = "Done.\nProof: seen — the page looks right"
        tp = self.transcript(claude_turn("p1", "fix ui", [tool("Edit", file_path="a.css"),
                                                          tool("Bash", command="npm run build")], final))
        out = self.stop(tp, "p1", final, mode="block")
        self.assertIn("seen", out["reason"])

    def test_seen_with_browser_screenshot_passes(self):
        final = "Done.\nProof: seen — screenshot of /checkout shows the new total"
        tp = self.transcript(claude_turn("p1", "fix ui", [
            tool("Edit", file_path="a.css"), tool("mcp__browser__screenshot", url="http://localhost")], final))
        self.assertIsNone(self.stop(tp, "p1", final, mode="block"))

    def test_seen_with_image_read_passes(self):
        final = "Proof: seen — opened shot.png, button is blue"
        tp = self.transcript(claude_turn("p1", "fix ui", [
            tool("Edit", file_path="a.css"), tool("Read", file_path="C:/tmp/shot.png")], final))
        self.assertIsNone(self.stop(tp, "p1", final, mode="block"))

    def test_proof_line_without_evidence_text_is_sent_back(self):
        final = "Done.\nProof: tested"
        tp = self.transcript(claude_turn("p1", "x", [tool("Bash", command="make")], final))
        out = self.stop(tp, "p1", final, mode="block")
        self.assertIn("doesn't say what", out["reason"])

    def test_markdown_proof_line_is_accepted(self):
        for final in ["Done.\n**Proof:** tested — pytest passed",
                      "Done.\nProof: `tested` — pytest passed",
                      "Done.\n- **Proof: tested** — pytest passed"]:
            tp = self.transcript(claude_turn("p1", "x", [tool("Bash", command="pytest")], final))
            self.assertIsNone(self.stop(tp, "p1", final, mode="block"), final)

    def test_not_yet_is_an_honest_answer(self):
        final = "Changed the CSS.\nProof: not yet — couldn't open the page, staging is down"
        tp = self.transcript(claude_turn("p1", "x", [tool("Edit", file_path="a.css")], final))
        self.assertIsNone(self.stop(tp, "p1", final, mode="block"))
        self.assertEqual(self.events(), ["pass"])

    def test_waiting_on_running_work_counts_as_not_yet(self):
        final = "Pushed the fix. Waiting on CI for #481."
        tp = self.transcript(claude_turn("p1", "x", [tool("Bash", command="git push"),
                                                     tool("mcp__t3-code__watch_pull_request", pr=481)], final))
        self.assertIsNone(self.stop(tp, "p1", final, mode="block"))
        self.assertEqual(self.events(), ["pass"])

    def test_background_command_pause_counts_as_not_yet(self):
        final = "The release is running; I'll verify it live when it finishes."
        tp = self.transcript(claude_turn("p1", "x", [tool("Bash", command="./release.sh",
                                                          run_in_background=True)], final))
        self.assertIsNone(self.stop(tp, "p1", final, mode="block"))

    def test_waiting_words_without_a_wait_tool_are_sent_back(self):
        final = "Waiting on CI for #481."
        tp = self.transcript(claude_turn("p1", "x", [tool("Bash", command="git push")], final))
        self.assertIsNotNone(self.stop(tp, "p1", final, mode="block"))

    def test_done_after_a_wait_is_still_sent_back(self):
        final = "#464 is clear to merge: both CI checks passed."
        tp = self.transcript(claude_turn("p1", "x", [tool("mcp__t3-code__t3_background_wait", id="b1"),
                                                     tool("Bash", command="gh pr checks 464")], final))
        self.assertIsNotNone(self.stop(tp, "p1", final, mode="block"))

    def test_configured_quiet_reply_is_ignored(self):
        self.home.mkdir(parents=True, exist_ok=True)
        (self.home / "config.json").write_text(json.dumps({"quiet": [r"^Inbox: nothing new\.$", "("]}))
        tp = self.transcript(claude_turn("p1", "x", [tool("PowerShell", command="inbox pending")],
                                         "Inbox: nothing new."))
        self.assertIsNone(self.stop(tp, "p1", "Inbox: nothing new.", mode="block"))
        self.assertEqual(self.events(), [])
        tp = self.transcript(claude_turn("p2", "x", [tool("Edit", file_path="a.py")], "Inbox: nothing new."))
        self.assertIsNotNone(self.stop(tp, "p2", "Inbox: nothing new.", mode="block"))  # edits never quiet

    def test_tested_with_nothing_run_is_sent_back(self):
        final = "Done.\nProof: tested — it works"
        tp = self.transcript(claude_turn("p1", "x", [tool("Edit", file_path="a.py")], final))
        self.assertIn("nothing ran", self.stop(tp, "p1", final, mode="block")["reason"])

    def test_old_proof_words_still_work(self):
        final = "Done.\nProof: checked — pytest passed"
        tp = self.transcript(claude_turn("p1", "x", [tool("Bash", command="pytest")], final))
        self.assertIsNone(self.stop(tp, "p1", final, mode="block"))

    def test_handing_the_check_to_the_user_is_sent_back(self):
        final = "Fixed the footer link. Reload the page and check it works.\nProof: tested — pytest: 12 passed"
        tp = self.transcript(claude_turn("p1", "fix footer", [tool("Edit", file_path="a.py"),
                                                              tool("Bash", command="pytest")], final))
        self.assertIn("do it now", self.stop(tp, "p1", final, mode="block")["reason"])

    def test_not_yet_may_hand_over_honestly(self):
        final = "Built the APK. Can you check it on your phone? I have no device here.\nProof: not yet — needs the user's phone"
        tp = self.transcript(claude_turn("p1", "fix app", [tool("Edit", file_path="a.kt")], final))
        self.assertIsNone(self.stop(tp, "p1", final, mode="block"))

    def test_agent_doing_its_own_check_is_not_a_handoff(self):
        final = "I reloaded the page and checked the footer.\nProof: seen — screenshot of /about footer"
        tp = self.transcript(claude_turn("p1", "fix footer", [tool("Edit", file_path="a.py"),
                                                              tool("mcp__browser__screenshot")], final))
        self.assertIsNone(self.stop(tp, "p1", final, mode="block"))

    def test_url_in_any_command_is_not_seen(self):
        final = "Done.\nProof: seen — installed it"
        tp = self.transcript(claude_turn("p1", "x", [tool("Bash", command="git clone https://example.test/r")], final))
        self.assertIn("seen", self.stop(tp, "p1", final, mode="block")["reason"])

    def test_broken_in_a_request_is_not_a_rejection(self):
        tp = self.transcript(claude_turn("p1", "make it", [tool("Edit", file_path="a.py")], "Done."))
        self.prompt(tp, "fix the broken footer link", "p2")
        self.assertNotIn("rejected", self.events())

    def test_repeated_short_reply_finds_the_right_turn(self):
        # Claude Code may fire the prompt hook before the new prompt is in the transcript.
        lines = (claude_turn("p1", "nope", [], "Okay, what should change?")
                 + claude_turn("p2", "make it blue", [tool("Edit", file_path="a.css")], "Done."))
        tp = self.transcript(lines)
        self.prompt(tp, "nope", "p3")
        self.assertIn("rejected", self.events())

    def test_non_working_turn_is_ignored(self):
        tp = self.transcript(claude_turn("p1", "what is X?", [tool("Read", file_path="a.py")], "X is Y."))
        self.assertIsNone(self.stop(tp, "p1", "X is Y.", mode="block"))
        self.assertEqual(self.events(), [])

    def test_second_stop_in_same_turn_is_allowed(self):
        tp = self.transcript(claude_turn("p1", "make", [tool("Write", file_path="a.py")], "Done."))
        self.assertIsNotNone(self.stop(tp, "p1", "Done.", mode="block"))
        self.assertIsNone(self.stop(tp, "p1", "Done again.", mode="block"))
        self.assertEqual(self.events(), ["gate_block", "after_block"])

    def test_stop_hook_active_allows(self):
        tp = self.transcript(claude_turn("p1", "make", [tool("Write", file_path="a.py")], "Done."))
        self.assertIsNone(self.stop(tp, "p1", "Done.", mode="block", stop_hook_active=True))

    def test_codex_missing_proof_blocks_without_stop_hook_active_field(self):
        tp = self.transcript(codex_turn("t1", "make it", [file_change(), command("python a.py")],
                                        "Done."), codex=True)
        payload = {"session_id": "s1", "turn_id": "t1", "transcript_path": tp, "cwd": self.tmp.name,
                   "hook_event_name": "Stop", "model": "gpt-test", "last_assistant_message": "Done."}
        out = self.run_pf("stop", payload, "block")
        self.assertEqual(out["decision"], "block")
        self.assertIsNone(self.run_pf("stop", payload, "block"))  # loop guard without the field

    def test_codex_curl_counts_as_seen(self):
        final = "Live.\nProof: seen — curl https://example.test/health returned 200"
        tp = self.transcript(codex_turn("t1", "deploy", [command("curl -s https://example.test/health")],
                                        final), codex=True)
        payload = {"session_id": "s1", "turn_id": "t1", "transcript_path": tp, "cwd": self.tmp.name,
                   "last_assistant_message": final}
        self.assertIsNone(self.run_pf("stop", payload, "block"))
        self.assertEqual(self.events(), ["pass"])

    # --- rejections and stall -------------------------------------------------
    def prompt(self, tp, prompt, key):
        return self.run_pf("prompt", {"session_id": "s1", "transcript_path": tp, "cwd": self.tmp.name,
                                      "hook_event_name": "UserPromptSubmit", "prompt": prompt,
                                      "prompt_id": key})

    def test_two_rejections_trigger_stall_once(self):
        lines = (claude_turn("p1", "fix login", [tool("Edit", file_path="a.py")], "Fixed.")
                 + claude_turn("p2", "still doesn't work", [tool("Edit", file_path="a.py")], "Fixed now.")
                 + claude_turn("p3", "nope, same issue", [tool("Edit", file_path="a.py")], "Fixed again."))
        tp = self.transcript(lines)
        first = self.prompt(tp, "still doesn't work", "p2")
        self.assertIn("reproduce the problem yourself", first["hookSpecificOutput"]["additionalContext"])
        out = self.prompt(tp, "nope, same issue", "p3")
        self.assertIn("still broken twice", out["hookSpecificOutput"]["additionalContext"])
        lines += claude_turn("p4", "still broken", [], "")
        tp = self.transcript(lines)
        again = self.prompt(tp, "still broken", "p4")  # stall fires once per session
        self.assertNotIn("still broken twice", again["hookSpecificOutput"]["additionalContext"])
        ev = self.events()
        self.assertEqual(ev.count("stall"), 1)
        self.assertEqual(ev.count("rejected"), 3)

    def test_rejection_needs_previous_working_turn(self):
        tp = self.transcript(claude_turn("p1", "explain X", [], "X is Y.") + [claude_user("nope", "p2")])
        self.prompt(tp, "nope", "p2")
        self.assertNotIn("rejected", self.events())

    def test_still_in_a_normal_request_is_not_a_rejection(self):
        tp = self.transcript(claude_turn("p1", "make it", [tool("Edit", file_path="a.py")], "Done."))
        self.prompt(tp, "can you still add a dark mode toggle?", "p2")
        self.assertNotIn("rejected", self.events())

    def test_long_message_is_not_counted_as_rejection(self):
        tp = self.transcript(claude_turn("p1", "make it", [tool("Edit", file_path="a.py")], "Done."))
        self.prompt(tp, "still doesn't work. " + "Here is a long explanation. " * 20, "p2")
        self.assertNotIn("rejected", self.events())

    # --- robustness -----------------------------------------------------------
    def test_malformed_input_exits_quietly(self):
        self.assertIsNone(self.run_pf("stop", b"{not json"))
        self.assertIsNone(self.run_pf("prompt", b""))
        self.assertIsNone(self.run_pf("stop", {"transcript_path": "Z:/missing.jsonl"}))

    def test_log_holds_no_text_or_project_names(self):
        tp = self.transcript(claude_turn("p1", "secret client project", [tool("Edit", file_path="a.py")], "Done."))
        self.stop(tp, "p1", "Done.")
        raw = (self.home / "log.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("secret client", raw)
        self.assertNotIn(Path(self.tmp.name).name, raw)

    def test_large_transcript_stays_fast(self):
        filler = [claude_assistant([text("x" * 2000)]) for _ in range(2500)]  # about 5 MB
        tp = self.transcript(filler + claude_turn("p1", "make", [tool("Edit", file_path="a.py")], "Done."))
        t = time.perf_counter()
        self.stop(tp, "p1", "Done.")
        self.assertLess(time.perf_counter() - t, 3.0)  # includes interpreter start
        row = json.loads((self.home / "log.jsonl").read_text(encoding="utf-8").splitlines()[-1])
        self.assertLess(row["ms"], 150)

    def test_report_runs(self):
        tp = self.transcript(claude_turn("p1", "make", [tool("Edit", file_path="a.py")], "Done."))
        self.stop(tp, "p1", "Done.")
        r = subprocess.run([sys.executable, str(PF), "report"], env=self.env, capture_output=True, text=True)
        self.assertIn("claude-test-1", r.stdout)


if __name__ == "__main__":
    unittest.main()
