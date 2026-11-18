# proof-first

**A small kit that makes AI coding agents prove their work before calling it done.** It contains a one-page set of rules, one skill and one hook script. It works with Claude Code and Codex CLI, and the rules work with any agent that reads `AGENTS.md` or `CLAUDE.md`.

This is how I work with AI after years of daily use, built from what my own logs showed. Take it, change it, make it yours.

## Why: what a year of my logs showed

I analysed about 11,400 of my own messages to AI agents (Codex, Claude Code, a Telegram agent and an orchestrator app) from November 2025 to November 2026. I expected the analysis to tell me which model to use. It didn't.

**1. About 1 in 10 "done" claims was wrong, whichever model made it.** Here is how often I rejected an assistant's "done" in my very next message ("still doesn't work", "nope"):

| Model I was replying to | "Done" claims | I rejected |
|---|---|---|
| Claude Opus 5.5 | 71 | 9.9% |
| GPT-5.6 Sol | 307 | 9.8% |
| GPT-5.5 | 243 | 9.1% |
| GPT-6 Astra | 122 | 9.8% |
| Older generation (GPT-5.1 Codex Max) | 12 | about 17% |

The current models were within one point of each other. The older generation really was worse, but that era is over. Switching between current models won't fix this.

**2. Visual work was a little worse, and harder to prove.** On creative and visual work, 12.6% of "done" claims were rejected (95 claims across the current models). On software work, 9.4% were (381 claims). The samples are small, so that gap is a hint, not a finding. The cause is easy to see in the logs, though: a test run can't show that a page looks right, so agents stop at "I edited the CSS" and call it done.

**3. My corrections were almost always the same one: you said it's done, and I can't see it working.** Writing the rule into my instructions didn't fix it. Something had to check the claim when it was made.

**4. My short replies carry the stage of the work.** "eli5 first, don't implement" means explain. "Do it all" means finish the job I named. "Still broken" means show me. Agents misread these mostly after a model or harness switch dropped the context.

proof-first turns those findings into rules plus one automatic check.

*Method:* a "done" claim is an assistant message that opens with done/fixed/implemented, or says "should now work" or "is now live". A rejection is a short next message saying it still doesn't work. Automated messages were excluded: goal continuations, skill and tool injections, image notes and relays. These are text matches, not hand labels, so treat the numbers as directional.

## What's inside

| File | What it does |
|---|---|
| [`WORKING.md`](WORKING.md) | The rules your agent reads: stages, when to stop and ask, the proof ladder, the stall rule, handoff notes. |
| [`skills/prove-it`](skills/prove-it/SKILL.md) | How to reach "seen" for each kind of task, and how to report it. |
| [`hooks/pf.py`](hooks/pf.py) | The automatic check, plus a local log and a report. Python 3.9+, standard library only. |
| [`examples/ian.md`](examples/ian.md) | My personal layer: preferences and which model I use for what. A template for yours. |
| [`tests/`](tests/test_pf.py) | Tests modelled on real hook payloads and transcripts from both harnesses. |

### What the hook does

- **When a working turn ends** (the agent changed files or ran commands), it looks for a line like this:

  ```
  Proof: seen — screenshot of /checkout after reload shows the new total
  ```

  The hook sends the agent back **once** to fix any of these:
  - The proof line is missing, or names a rung but no evidence.
  - It claims `checked` and no command ran in that turn.
  - It claims `seen` and the turn has no `seen` evidence. That means a browser, preview, screenshot or image tool, a live request (`curl`, `wget`, `Invoke-WebRequest`), or a query of real data (`psql`, `sqlite3`, `select … from`).

  It never blocks twice in one turn, and turns that only read or answer questions are never touched. These checks are heuristics: they catch a missing or unbacked claim, not a lazy screenshot.
- **When you reply "still doesn't work"** right after a working turn, it records a rejection. After two in one session, it tells the agent to apply the stall rule: stop retrying, write a handoff note, and propose another approach or another model.
- **It logs counts, never text.** Each line of `~/.proof-first/log.jsonl` holds:
  - the time, harness, session id and model;
  - a salted hash of the project folder;
  - the event, the proof rung and the problem found;
  - how long the hook took.

  No message text, paths or project names are logged.
- **It never breaks your session.** Any error is written to `~/.proof-first/errors.log`, and the hook exits quietly. It typically takes 5–40 ms, plus Python start-up.

## Install (5 minutes)

**1. Clone the repo.**

```bash
git clone https://github.com/lokki007/proof-first ~/proof-first
```

**2. Make your agent read the rules.** Add one line to your global instruction file. For Claude Code that's `~/.claude/CLAUDE.md`. For Codex it's `~/.codex/AGENTS.md`. Any agent that reads `AGENTS.md` works too.

```
Follow the rules in ~/proof-first/WORKING.md.
```

**3. Install the skill.** Copy `skills/prove-it` into your skills folder: `~/.claude/skills/` for Claude Code, or `~/.agents/skills/` for Codex and other Agent Skills readers.

**4. Add the hooks.** Use absolute paths, and replace `python3` with `python` on Windows.

- **Claude Code** goes in `~/.claude/settings.json`; merge it into any existing `"hooks"` block:

  ```json
  {
    "hooks": {
      "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "python3 \"/home/you/proof-first/hooks/pf.py\" prompt", "timeout": 10 }] }],
      "Stop":             [{ "hooks": [{ "type": "command", "command": "python3 \"/home/you/proof-first/hooks/pf.py\" stop",   "timeout": 10 }] }]
    }
  }
  ```

- **Codex CLI** goes in `~/.codex/hooks.json`; hooks must be enabled with `[features] hooks = true` in `config.toml`:

  ```json
  {
    "hooks": {
      "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "python3 \"/home/you/proof-first/hooks/pf.py\" prompt", "timeout": 10 }] }],
      "Stop":             [{ "hooks": [{ "type": "command", "command": "python3 \"/home/you/proof-first/hooks/pf.py\" stop",   "timeout": 10 }] }]
    }
  }
  ```

  Codex has two quirks:
  - **New hooks don't run until you approve them.** Codex keeps a trust list for hooks, so start Codex once in interactive mode and approve them.
  - **On Windows, don't put quotes around the interpreter.** Codex runs hook commands through PowerShell, where `"C:\path\python.exe" args` is not a command. Use `python "C:\path\pf.py" stop` instead.

**5. Check it works.** Run one session that edits a file, then:

```bash
python3 ~/proof-first/hooks/pf.py report
```

You should see a row for your harness and model.

### Rollout: warn first, then block

The hook starts in **warn** mode. It logs every turn that would have been sent back, but never sends anything back. That first week gives you a baseline. Then turn the check on:

```bash
python3 ~/proof-first/hooks/pf.py mode block
```

Compare `pf.py report` a few weeks later. The rejection rate (`rej%`) is the number to watch. If more than about 15% of working turns get sent back (`gate%`), the check is too strict for your work, so tell me in an issue.

## Make it yours

Copy [`examples/ian.md`](examples/ian.md) to `~/.proof-first/me.md` and rewrite it. `WORKING.md` tells the agent to read it, and your file wins where it is more specific. Keep `WORKING.md` universal and put your own habits in `me.md`.

## Uninstall

1. Remove the two hook entries that mention `pf.py`.
2. Remove the line you added to `CLAUDE.md` / `AGENTS.md`.
3. Delete `skills/prove-it` from your skills folder.
4. Delete `~/.proof-first/`.

## Glossary

- **Harness:** the program that runs the agent, such as Claude Code or Codex CLI.
- **Hook:** a script the harness runs on an event, such as "user sent a prompt" or "agent is about to stop".
- **Working turn:** a turn in which the agent changed files or ran commands.
- **Proof rung:** `planned < edited < checked < running < seen`. See [`WORKING.md`](WORKING.md).
- **Rejection:** your short reply right after a working turn, saying it doesn't work.
- **Stall:** two rejections in one session.
- **Handoff note:** a five-line state summary, so another model or session can carry on without starting over.

## What it deliberately doesn't do

- **It doesn't switch models automatically.** Switching mid-task loses the context that short replies depend on, and my data showed no gap between models big enough to route on. It tells the agent to suggest a switch when you're stuck, and the handoff note carries the context over.
- **It doesn't rank models.** `pf.py report` shows your own counts, and you decide.
- **It doesn't call an LLM, or anything over the network.**

## Tests

```bash
python3 -m unittest discover tests
```

MIT licensed.
