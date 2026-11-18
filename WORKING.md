# How to work with me

These rules are for the AI agent. They come from a year of my own logs: the most common friction was an agent saying "done" when the result was not done in a way I could see.

## 1. Read the stage of the work

Each message I send is one of four stages. Start in **explore** until I name a job. A short reply keeps the current stage unless it clearly names another one.

| Stage | Sounds like | What you do |
|---|---|---|
| Explore | "how does X work", "eli5", "don't implement yet" | Read, explain, and don't edit anything. |
| Decide | "what are the options", "which is better" | Give the options and trade-offs, then wait for my choice. |
| Build | "do it", "go", "fix it", "do it all" | Do the whole agreed job without asking about routine steps. |
| Check | "does it work?", "show me", "still broken" | Lead with evidence, not a summary of what you changed. |

"Do it all" means all of the named job, not the work next to it.

## 2. Stop and ask only at the decision line

Explain and wait before anything that is hard to undo or changes what other people depend on:
- data models and migrations
- public interfaces
- money and billing
- deleting things
- production settings

Inside the agreed scope, everything else is routine: do it, and tell me afterwards.

## 3. Prove it, then say it

The proof ladder, from weakest to strongest:

| Rung | Meaning |
|---|---|
| `planned` | Written down, nothing changed yet. |
| `edited` | Files changed; nothing has run them. |
| `checked` | Something ran: tests, a build, the program itself. |
| `running` | Deployed or started where it will be used. |
| `seen` | The user-facing result was observed: a screenshot or browser check, a live HTTP request, or a query of the real data. |

**Every turn in which you changed files or ran commands ends with one line:**

```
Proof: <rung> — <what you ran or saw>
```

For example: `Proof: seen — screenshot of /checkout after reload shows the new total`.

Only write "done", "fixed" or "works" when the rung matches the task:
- UI, visual and user-facing work needs `seen`.
- A deploy needs `running`, plus one live request.
- A data change needs `seen`: counts from the real store, or a dry run on staging.
- Docs and plans need `edited`.
- Everything else needs at least `checked`.

If you can't reach the needed rung, say so plainly: "edited and checked; not seen because the staging login is down". That is a good answer. A confident "done" that turns out wrong costs me more than an honest "not yet".

The `prove-it` skill shows how to reach `seen` for each kind of task.

## 4. Stall rule

If I reject a result twice in one session ("still doesn't work", "nope"), stop retrying the same approach:

1. Write a handoff note (format below).
2. Say what you think failed, and why.
3. Propose either a different approach or a different model or harness for this step.

## 5. Handoff note

Write one whenever work moves to another model, harness or session:

```
Goal: <the outcome I asked for, in my words>
Decided: <decisions already made, and who made them>
State: <what exists now> — Proof: <rung> — <evidence>
Tried and failed: <approach → why it failed>
Next: <the single next step>
```

Print it, or save it to `~/.proof-first/handoffs/<project>.md`. Never save it inside the repository.

## 6. My personal layer

If `~/.proof-first/me.md` exists, read it after this file. It holds my own preferences, and it wins where it is more specific than this file.
