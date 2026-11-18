#!/usr/bin/env python3
"""proof-first: agents must show it works before they say "done".

Usage:
    pf.py prompt              hook: runs when you send a message
    pf.py stop                hook: runs when the agent finishes
    pf.py report [days]       your numbers (default: last 14 days)
    pf.py mode [warn|block]   warn = only log; block = send unproven "done" back once

Works with Claude Code and Codex CLI. Standard library only, Python 3.9+.
Never breaks your session: every failure exits 0 with no output.
"""
import hashlib
import json
import os
import re
import sys
import time
import traceback
from collections import defaultdict
from pathlib import Path

HOME = Path(os.environ.get("PROOF_FIRST_HOME") or Path.home() / ".proof-first")
LOG = HOME / "log.jsonl"
TAIL_BYTES = 1_000_000
# --- patterns ---------------------------------------------------------------

# "Proof: seen — ...", also with markdown: "**Proof:** `seen` — ...".
# Older words still work: planned/edited -> not yet, checked/running -> tested.
PROOF_RE = re.compile(
    r"(?im)^[\s>#*_`-]*proof[*_`]*\s*:[\s*_`]*"
    r"(seen|tested|not\s+yet|planned|edited|checked|running)\b[*_`]*[\s\-:—–]*(.*)$"
)
PROOF_WORD = {"planned": "not yet", "edited": "not yet", "checked": "tested", "running": "tested"}
REJECT_RE = re.compile(
    r"(?i)\b(still (doesn'?t|does not|not|isn'?t|broken|the same|showing|failing|fails|wrong)"
    r"|nope|doesn'?t work|does not work|not working|isn'?t working|same (issue|problem|bug|error)"
    r"|didn'?t (fix|work|change)|nothing changed|(it'?s|is|looks|now|all) broken)\b"
)
# Heuristics for "seen": a live request, a query of real data, or a screenshot command...
SEEN_CMD_RE = re.compile(
    r"(?i)(\bcurl\b|\bwget\b|invoke-webrequest|invoke-restmethod|\bhttpie\b|\bxh\s+https?://|"
    r"\b(psql|sqlite3|mysql|mongosh)\b|\bselect\b.+\bfrom\b|screenshot)"
)
# ...or a browser, preview, computer-use or image tool (Claude Code names, Codex "server:tool").
SEEN_TOOL_RE = re.compile(
    r"(?i)(screenshot|preview_(snapshot|evaluate|act|navigate|open|wait_for)|browser|navigate|"
    r"computer|chrome|playwright|html_render|get_page_text|read_page|cua_repl|imageview|snapshot)"
)
# The agent asks the user to do the check it could do itself ("reload and check", "let me know
# if it works", "tests not run"). Found in 12% of replies the user then called broken, 5% overall.
HANDOFF_RE = re.compile(
    r"(?i)\b("
    r"(?:can|could) you (?:please )?(?:check|test|try|confirm|verify|reload|refresh|look at|open)"
    r"|please (?:check|test|try|confirm|verify|reload|refresh)"
    r"|(?:reload|refresh|restart|reopen|re-open)\b[^.\n]{0,60}\b(?:and|to) (?:check|see|confirm|verify|test)"
    r"|let me know (?:if|whether|how) (?:it|this|that|everything|the \w+) (?:works|worked|looks|is|goes|behaves)"
    r"|(?:tests?|testing) (?:were |was )?not run"
    r"|(?:i )?(?:haven'?t|have not|didn'?t|did not) (?:yet )?(?:tried|tested|verified|run|checked|opened|looked)"
    r"|if (?:it|this|that|the \w+) still (?:fails|doesn'?t|breaks|errors|shows|happens|isn'?t)"
    r"|confirm (?:that )?you (?:see|can|land|get)"
    r")")
IMAGE_RE = re.compile(r"(?i)\.(png|jpe?g|gif|webp|bmp)$")
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
CMD_TOOLS = {"Bash", "PowerShell"}

GATE_REASON = {
    "missing": "You changed files or ran commands but didn't show it works. Re-read the user's last "
               "message and check you did each thing they asked. Then end with one line: "
               "`Proof: seen — what you looked at`, `Proof: tested — what you ran`, or "
               "`Proof: not yet — why not`.",
    "no_evidence": "Your proof line doesn't say what you looked at or ran. Add it after the word, "
                   "e.g. `Proof: tested — pytest: 48 passed`.",
    "unbacked_seen": "Your proof line says `seen`, but you didn't look at anything this turn (no "
                     "screenshot, browser, live request or data query). Look now, or change it to "
                     "`tested` or `not yet`.",
    "unbacked_tested": "Your proof line says `tested`, but nothing ran this turn. Run the tests, "
                       "build or program now, or change it to `not yet`.",
    "handoff": "Your reply asks the user to check something (reload, confirm, try it, let me know) or "
               "says a check wasn't done. If you can do that check yourself, do it now. If only the "
               "user can (their device, login or taste), say so in `Proof: not yet — why`.",
}
REJECT_TEXT = ("proof-first: the user says it still doesn't work. Before changing code: re-read their "
               "message, reproduce the problem yourself the way they saw it, then fix it and check it "
               "the same way.")
STALL_TEXT = ("proof-first: the user has said it's still broken twice. Don't try the same fix again. "
              "Write a short handoff note (Goal / Done / Failed / Next) and suggest a different "
              "approach or a different model.")


# --- small helpers ----------------------------------------------------------

def home():
    HOME.mkdir(parents=True, exist_ok=True)
    return HOME


def config():
    try:
        return json.loads((HOME / "config.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def mode():
    return os.environ.get("PROOF_FIRST_MODE") or config().get("mode") or "warn"


def project_key(cwd):
    """Salted short hash of the project folder, so the log never holds names."""
    root = Path(cwd or ".")
    for p in [root, *root.parents]:
        if (p / ".git").exists():
            root = p
            break
    salt_file = home() / "salt"
    if not salt_file.exists():
        salt_file.write_text(os.urandom(16).hex())
    return hashlib.sha1((salt_file.read_text().strip() + str(root).lower()).encode()).hexdigest()[:10]


def log(event, ctx, **extra):
    row = {"ts": round(time.time(), 3), "harness": ctx.get("harness"), "session": ctx.get("session"),
           "model": ctx.get("model"), "project": ctx.get("project"), "event": event,
           "ms": round((time.perf_counter() - ctx["t0"]) * 1000, 1)}
    row.update({k: v for k, v in extra.items() if v is not None})
    with open(home() / "log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def read_log(max_bytes=4_000_000):
    if not LOG.exists():
        return []
    rows = []
    for line in tail_lines(LOG, max_bytes):
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass
    return rows


def tail_lines(path, max_bytes=TAIL_BYTES):
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - max_bytes))
        data = f.read()
    lines = data.decode("utf-8", "replace").splitlines()
    if size > max_bytes and lines:
        lines = lines[1:]  # first line is probably cut
    return lines


def jsonl(path, max_bytes=TAIL_BYTES):
    out = []
    for line in tail_lines(path, max_bytes):
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


# --- transcript readers -----------------------------------------------------
# Each returns a list of turns, oldest first. A turn is a dict:
#   {"key", "user_text", "edits", "commands", "tools", "images", "final_text", "model"}

def new_turn(key, user_text=""):
    return {"key": key, "user_text": user_text, "edits": 0, "commands": [], "tools": [],
            "images": 0, "final_text": "", "model": None}


def claude_user_text(msg):
    """Text of a real user prompt, or None for tool results / meta lines."""
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return None
        texts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
        return "\n".join(texts) if texts else None
    return None


def claude_turns(path):
    turns, model = [], None
    for d in jsonl(path):
        if d.get("isSidechain"):
            continue
        t = d.get("type")
        if t == "attachment" and isinstance(d.get("attachment"), dict):
            ident = d["attachment"].get("identity") or {}
            model = ident.get("modelId") or model
            continue
        msg = d.get("message") or {}
        if t == "user" and not d.get("isMeta"):
            text = claude_user_text(msg)
            if text is not None:
                turns.append(new_turn(d.get("promptId") or d.get("uuid"), text))
                continue
        if t == "assistant" and turns:
            turn = turns[-1]
            m = msg.get("model")
            if m and not m.startswith("<"):
                turn["model"] = model = m
            for b in msg.get("content") or []:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "text" and b.get("text", "").strip():
                    turn["final_text"] = b["text"]
                elif b.get("type") == "tool_use":
                    name, inp = b.get("name", ""), b.get("input") or {}
                    turn["tools"].append(name)
                    if name in EDIT_TOOLS:
                        turn["edits"] += 1
                    elif name in CMD_TOOLS:
                        turn["commands"].append(str(inp.get("command", "")))
                    elif name == "Read" and IMAGE_RE.search(str(inp.get("file_path", ""))):
                        turn["images"] += 1
    for turn in turns:
        turn["model"] = turn["model"] or model
    return turns


def codex_turns(path):
    turns, by_id, model = [], {}, None

    def get(tid):
        if tid not in by_id:
            by_id[tid] = new_turn(tid)
            turns.append(by_id[tid])
        return by_id[tid]

    for d in jsonl(path):
        p = d.get("payload") if isinstance(d.get("payload"), dict) else {}
        t, pt = d.get("type"), p.get("type")
        if t == "turn_context":
            model = p.get("model") or model
            if p.get("turn_id"):
                get(p["turn_id"])["model"] = model
        elif t == "event_msg" and pt == "task_started" and p.get("turn_id"):
            get(p["turn_id"])
        elif t == "event_msg" and pt == "task_complete" and p.get("turn_id"):
            get(p["turn_id"])["final_text"] = p.get("last_agent_message") or ""
        elif t == "event_msg" and pt == "item_completed" and p.get("turn_id"):
            turn, item = get(p["turn_id"]), p.get("item") or {}
            kind = item.get("type")
            if kind == "UserMessage":
                turn["user_text"] = " ".join(c.get("text", "") for c in item.get("content") or []
                                             if isinstance(c, dict))
            elif kind == "FileChange":
                turn["edits"] += max(1, len(item.get("changes") or {}))
            elif kind == "CommandExecution":
                cmd = item.get("command")
                turn["commands"].append(" ".join(cmd) if isinstance(cmd, list) else str(cmd or ""))
            elif kind == "ImageView":
                turn["images"] += 1
            elif kind == "McpToolCall":
                turn["tools"].append(f"{item.get('server')}:{item.get('tool') or item.get('name')}")
            elif kind == "AgentMessage":
                texts = [c.get("text", "") for c in item.get("content") or [] if isinstance(c, dict)]
                if any(x.strip() for x in texts):
                    turn["final_text"] = "\n".join(texts)
    for turn in turns:
        turn["model"] = turn["model"] or model
    return turns


def is_working(turn):
    return bool(turn and (turn["edits"] or turn["commands"]))


def evidence(turn):
    cmds = " \n".join(turn["commands"])
    seen = (bool(turn["images"]) or any(SEEN_TOOL_RE.search(t) for t in turn["tools"])
            or bool(SEEN_CMD_RE.search(cmds)))
    tested = seen or bool(turn["commands"])
    return {"seen": seen, "tested": tested}


def proof_of(text):
    """Return (word, says_what) for the last proof line: word is seen/tested/not yet or None."""
    lines = (text or "").strip().splitlines()[-15:]
    m = None
    for m in PROOF_RE.finditer("\n".join(lines)):
        pass
    if not m:
        return None, False
    word = re.sub(r"\s+", " ", m.group(1).lower())
    return PROOF_WORD.get(word, word), bool(m.group(2).strip(" *_`"))


# --- hook context -----------------------------------------------------------

def context(payload):
    tp = payload.get("transcript_path") or ""
    norm = tp.replace("\\", "/")
    harness = "codex" if ("/.codex/" in norm or Path(norm).name.startswith("rollout-")) else "claude-code"
    turns = []
    if tp and Path(tp).exists():
        turns = codex_turns(tp) if harness == "codex" else claude_turns(tp)
    model = payload.get("model") or next((t["model"] for t in reversed(turns) if t["model"]), None)
    return {"harness": harness, "session": payload.get("session_id"), "model": model,
            "project": project_key(payload.get("cwd")), "turns": turns,
            "turn_key": payload.get("turn_id") or payload.get("prompt_id")}


def current_turn(ctx, payload):
    turns, key = ctx["turns"], ctx["turn_key"]
    if key:
        for t in reversed(turns):
            if t["key"] == key:
                return t
    return turns[-1] if turns else None


def previous_turn(ctx, payload):
    """The turn the user is replying to (the new prompt may or may not be logged yet)."""
    turns, key, prompt = ctx["turns"], ctx["turn_key"], (payload.get("prompt") or "").strip()
    idx = len(turns)  # default: the new prompt is not in the transcript yet
    if key:
        for i in range(len(turns) - 1, -1, -1):
            if turns[i]["key"] == key:
                idx = i
                break
    elif turns and prompt and turns[-1]["user_text"].strip() == prompt:
        idx = len(turns) - 1
    return turns[idx - 1] if idx >= 1 else None


# --- commands ---------------------------------------------------------------

def cmd_prompt(payload, t0):
    ctx = context(payload)
    ctx["t0"] = t0
    prev = previous_turn(ctx, payload)
    prompt = (payload.get("prompt") or "").strip()
    out = None
    if is_working(prev) and len(prompt) <= 200 and REJECT_RE.search(prompt):
        log("rejected", ctx, rung=proof_of(prev["final_text"])[0])
        rows = [r for r in read_log() if ctx["session"] and r.get("session") == ctx["session"]]
        text = REJECT_TEXT
        if rows and (sum(r.get("event") == "rejected" for r in rows) >= 2
                and not any(r.get("event") == "stall" for r in rows)):
            log("stall", ctx)
            text = STALL_TEXT
        out = {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": text}}
    log("prompt", ctx, prev_working=is_working(prev))
    return out


def cmd_stop(payload, t0):
    ctx = context(payload)
    ctx["t0"] = t0
    turn = current_turn(ctx, payload)
    if not is_working(turn):
        return None
    text = payload.get("last_assistant_message") or turn["final_text"]
    rung, has_text = proof_of(text)
    ev = evidence(turn)
    problem = None
    if rung is None:
        problem = "missing"
    elif not has_text:
        problem = "no_evidence"
    elif rung == "seen" and not ev["seen"]:
        problem = "unbacked_seen"
    elif rung == "tested" and not ev["tested"]:
        problem = "unbacked_tested"
    elif rung in ("seen", "tested") and HANDOFF_RE.search(text or ""):
        problem = "handoff"  # only for seen/tested: "not yet" may hand over honestly

    state = home() / "blocked"
    state.mkdir(exist_ok=True)
    key = hashlib.sha1(f"{ctx['session']}|{ctx['turn_key'] or turn['key']}".encode()).hexdigest()[:16]
    flag = state / key
    if flag.exists() or payload.get("stop_hook_active"):
        log("after_block", ctx, rung=rung, problem=problem)
        return None
    if problem is None:
        log("pass", ctx, rung=rung)
        return None
    if mode() != "block":
        log("gate_warn", ctx, rung=rung, problem=problem)
        return None
    flag.write_text(str(time.time()))
    log("gate_block", ctx, rung=rung, problem=problem)
    return {"decision": "block", "reason": "proof-first: " + GATE_REASON[problem]}


def cmd_mode(args):
    if args:
        if args[0] not in ("warn", "block"):
            print("mode must be warn or block")
            return
        cfg = config()
        cfg["mode"] = args[0]
        (home() / "config.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    print("mode:", mode())


def cmd_report(args):
    days = float(args[0]) if args else 14.0
    since = time.time() - days * 86400
    rows = [r for r in read_log(50_000_000) if r.get("ts", 0) >= since]
    if not rows:
        print(f"No proof-first events in the last {days:g} days (log: {LOG}).")
        return
    stats = defaultdict(lambda: defaultdict(int))
    handoffs = defaultdict(int)
    ms = defaultdict(list)
    last = {}
    for r in rows:
        k = (r.get("harness") or "?", r.get("model") or "?")
        ev = r.get("event")
        stats[k][ev] += 1
        if ev in ("gate_warn", "gate_block") and r.get("problem") == "handoff":
            handoffs[k] += 1
        ms[k].append(r.get("ms") or 0)
        last[k[0]] = max(last.get(k[0], 0), r.get("ts", 0))
    print(f"proof-first: last {days:g} days, mode = {mode()}\n")
    hdr = (f"{'app':12} {'model':24} {'changes':>8} {'you said broken':>16} "
           f"{'no proof':>9} {'left to you':>12} {'speed':>7}")
    print(hdr)
    print("-" * len(hdr))
    pct = lambda a, b: f"{a} ({100 * a / b:.0f}%)" if b else str(a)
    for k in sorted(stats, key=lambda x: -stats[x]["prompt"]):
        s = stats[k]
        changes = s["pass"] + s["gate_warn"] + s["gate_block"]
        noproof = s["gate_warn"] + s["gate_block"] - handoffs[k]
        p95 = sorted(ms[k])[int(0.95 * (len(ms[k]) - 1))] if ms[k] else 0
        print(f"{k[0]:12} {k[1][:24]:24} {changes:8} {pct(s['rejected'], changes):>16} "
              f"{pct(noproof, changes):>9} {pct(handoffs[k], changes):>12} {p95:5.0f}ms")
    print("\nchanges         = times the agent finished after changing files or running commands")
    print("you said broken = your next message was \"still doesn't work\", \"nope\", ...")
    print("no proof        = finished without a believable Proof line (logged in warn mode, sent back in block mode)")
    print("left to you     = had proof, but asked you to do a check it could have done itself")
    print("speed           = how long the hook took (95% of runs were faster)")
    print("last seen: " + ", ".join(f"{h} {time.strftime('%Y-%m-%d %H:%M', time.localtime(t))}"
                                    for h, t in sorted(last.items())))
    err = HOME / "errors.log"
    if err.exists() and err.stat().st_size:
        print(f"note: hook errors were recorded in {err}")


def main(argv):
    t0 = time.perf_counter()
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "report":
        return cmd_report(argv[2:])
    if cmd == "mode":
        return cmd_mode(argv[2:])
    if cmd not in ("prompt", "stop"):
        print(__doc__)
        return
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", "replace")
        payload = json.loads(raw) if raw.strip() else {}
        if not isinstance(payload, dict):
            return
        out = cmd_prompt(payload, t0) if cmd == "prompt" else cmd_stop(payload, t0)
        if out:
            sys.stdout.write(json.dumps(out))
    except Exception:
        try:
            with open(home() / "errors.log", "a", encoding="utf-8") as f:
                f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + cmd + "\n" + traceback.format_exc() + "\n")
        except Exception:
            pass


if __name__ == "__main__":
    main(sys.argv)
    sys.exit(0)
