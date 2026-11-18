# proof-first

**Your AI agent has to show it works before it says "done".**

For a year I logged how I work with AI coding agents. About **1 in 10 times** an agent said "done", my next message was "still doesn't work". It didn't matter which model:

| Model | Times it said "done" | I said "still broken" |
|---|---|---|
| Claude Opus 5.5 | 71 | 9.9% |
| GPT-5.6 Sol | 307 | 9.8% |
| GPT-5.5 | 243 | 9.1% |
| GPT-6 Astra | 122 | 9.8% |

Switching models doesn't fix it. So I read 616 of my corrections to see what went wrong. **About 9 in 10 were things the agent could have caught itself:**

| What went wrong | Share | Why the agent missed it |
|---|---|---|
| Still broken, or "done" when it wasn't | 37% | It often ran the build, then told me to "reload and check" |
| Built the wrong thing, ignored an instruction, did too much or too little | 33% | It checked against its own idea of the request, not my words |
| Looks wrong | 17% | It took a screenshot but didn't judge it |
| Asked me instead of doing it, wrong target, too wordy | 13% | |

Only about 7% needed something only I had: my taste, my device or my login.

So proof-first makes the agent check its work before it says "done", in the way I would have checked it. That's all this is.

## How it works

1. **Four rules** your agent reads ([`WORKING.md`](WORKING.md)):
   - Don't change anything while I'm just asking.
   - Ask before anything hard to undo; otherwise just do it.
   - Don't say "done" until you've shown it works: re-read my request, do the check yourself, judge what you see.
   - If I say it's still broken, see it fail first. If I say it twice, change course.
2. **A proof line.** Whenever the agent changed something, it ends with one of these:
   ```
   Proof: seen — I opened /checkout and the new total shows
   Proof: tested — the 48 tests pass
   Proof: not yet — I couldn't open the page, staging is down
   ```
3. **A small check** ([`hooks/pf.py`](hooks/pf.py)) that runs after every agent reply. It sends the reply back once in four cases:
   - the proof line is missing;
   - it says `seen` but the agent looked at nothing;
   - it says `tested` but nothing ran;
   - it claims proof but asks you to check ("reload and check", "let me know if it works", "tests not run").

   When you say "still doesn't work", it tells the agent to reproduce the problem before it touches code.
4. **Your numbers.** `pf.py report` shows, per model, how often you had to say "still broken".

There's also a skill, [`prove-it`](skills/prove-it/SKILL.md), that shows agents how to check each kind of work. My own preferences are in [`examples/ian.md`](examples/ian.md); copy it and make it yours.

## Install

Python 3.9+ is the only requirement. It works with **Claude Code** and **Codex CLI**, and the rules work with any agent that reads `AGENTS.md` or `CLAUDE.md`.

**1. Clone the repo.**

```bash
git clone https://github.com/lokki007/proof-first ~/proof-first
```

**2. Point your agent at the rules.** Add this line to `~/.claude/CLAUDE.md` (Claude Code) or `~/.codex/AGENTS.md` (Codex):

```
Follow the rules in ~/proof-first/WORKING.md.
```

**3. Add the skill.** Copy `skills/prove-it` into `~/.claude/skills/` (Claude Code) or `~/.agents/skills/` (Codex).

**4. Add the hook.** Put this in `~/.claude/settings.json` (Claude Code) or `~/.codex/hooks.json` (Codex), using your own path:

```json
{
  "hooks": {
    "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "python3 \"/home/you/proof-first/hooks/pf.py\" prompt", "timeout": 10 }] }],
    "Stop":             [{ "hooks": [{ "type": "command", "command": "python3 \"/home/you/proof-first/hooks/pf.py\" stop",   "timeout": 10 }] }]
  }
}
```

- **On Windows,** write `python` instead of `python3`.
- **For Codex,** don't put quotes around the Python path, and approve the new hooks the first time Codex asks.

**5. Check it works.** After one session that changes a file, run:

```bash
python3 ~/proof-first/hooks/pf.py report
```

## Start gentle

The check starts in **warn** mode: it only logs, and never sends anything back. Run it that way for a week to see your numbers. Then switch it on:

```bash
python3 ~/proof-first/hooks/pf.py mode block
```

## Good to know

- **It stays out of your way.** It only looks at replies where the agent changed files or ran commands. It sends a reply back at most once, it never calls the internet or another AI, and it takes a few milliseconds.
- **It logs counts, never your words.** The log is at `~/.proof-first/log.jsonl`, and project names are hashed.
- **If the hook breaks, your agent keeps working.** Errors go to `~/.proof-first/errors.log`.
- **It's a simple check.** It catches a missing or unbacked proof line. It can't tell a careful screenshot from a lazy one, so your "still broken" numbers are the real test.

To uninstall, remove the two hook entries, the line in `CLAUDE.md`/`AGENTS.md` and the skill folder, then delete `~/.proof-first/`.

**How the numbers were counted:** I used about 11,400 of my own messages to Codex, Claude Code and other agents, from Nov 2025 to Nov 2026, with automated messages removed. "Said done" means the agent's reply started with done/fixed/implemented or said "should now work". "Still broken" means my next short message said it didn't work. Older models (GPT-5.1 Codex Max) were worse, at about 17%. Visual work was slightly worse than code (12.6% vs 9.4%), but on small samples. For the corrections table, a model labelled 801 likely corrections (616 were real) with what went wrong and who could have caught it. I read a sample myself: most labels held, and a few were really new requests. A model reading in hindsight probably leans toward "the agent could have caught it", so treat 9 in 10 as an upper estimate.

Run the tests with `python3 -m unittest discover tests`.

MIT licensed. Take it and change it.
