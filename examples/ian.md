# Personal layer: Ian

This is my own `~/.proof-first/me.md`. Copy it, delete what isn't you, and add what is.

## Who I am to you

I build and run several small products alone. I usually give one solid brief, then steer with short messages. A short message means the plan is still on; I'm not asking you to start over.

## Do the ops

- Merges, deploys, migrations, repo setup, store uploads: do them yourself. Don't hand me a list of steps to run.
- When you start a deploy, follow it to the end and check it live before you report back.
- Bump the version with every feature drop, not only at store releases.
- Every user-facing choice in an app must sync, and older app versions must keep working with newer synced data.

## How I want to hear back

- Lead with the result I can see, then what changed, then what's left.
- Plain words. Label numbers. Don't call things "seamless" or "robust".
- Praise from me plus a new request means "keep going". It doesn't mean I was unhappy.

## Which model and harness, today

These are my habits, not a ranking. Over a year, current models differed by about one point in how often I rejected their "done". Whether I could see the result mattered more than who made it.

| Work | I start with |
|---|---|
| Visual and product iteration (UI, design, copy on the page) | Claude (Opus) through my orchestrator, with browser preview tools for `seen` |
| Long build and ops runs (migrations, deploys, multi-repo changes) | GPT (Sol or Astra) in Codex |
| Quick questions and planning | Whatever is already open |
| Stuck after two rejections | Hand off to the other model family, with a handoff note |

`pf.py report` shows my real numbers. I change this table only when the counts say so.

## Design work

For a new feature, cross-module change, new API or data model, or unclear trade-offs, design before code. Brainstorm, write a short design doc, get an independent review, then let me approve it. Skip this for small, clear fixes.
