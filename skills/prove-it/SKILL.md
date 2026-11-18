---
name: prove-it
description: Use before saying work is done, fixed, live or working. Shows how to reach the right proof rung (edited, checked, running, seen) for each kind of task and how to report it with a Proof line. Use for UI changes, bug fixes, deploys, data changes and anything the user will look at.
license: MIT
---

# Prove it

An agent's "done" is only useful if the user would agree after looking. This skill shows how to reach the proof the task needs, and how to report it.

## Which rung the task needs

| Task | Rung needed |
|---|---|
| UI, styling, layout, anything visual | `seen` |
| User-facing behavior (login, checkout, forms) | `seen` |
| API endpoint | `seen` (real request) |
| Data change, migration, backfill | `seen` (counts from the real store, or a dry run on staging) |
| Deploy | `running`, plus one live request |
| Library code, refactor, internal logic | `checked` |
| Docs, plans | `edited` |

## How to reach `seen`

Use whatever tools you have. Prefer the one closest to what the user will do.

| Kind of work | How |
|---|---|
| Web page | Open it in a browser or preview tool, reload, take a screenshot, and say what is visible. Check the specific thing that changed, not just that the page loads. |
| Flow (login, checkout) | Walk the flow in the browser as the user would, and capture the end state. |
| API | Make a real request (`curl`, `Invoke-WebRequest`). Report the status code and the relevant part of the body. |
| Data | Run a count or select query against the real or staging store, before and after. |
| Desktop or mobile app | Take a window or device screenshot, then read the image. |
| Deploy | Request the live URL, and confirm the new version is what is served (a version string, a changed text, a header). |

If a local visual-check skill exists (for example one that compares rendered UI with a reference), use it for visual work.

## When you can't reach it

Say which rung you reached and why you stopped:

> Edited and checked: the build passes and unit tests are green. Not seen: the staging site needs a login I don't have. To see it: open /settings and check that the toggle saves.

That is a complete, honest answer. Don't round it up to "done".

## The report

End every turn that changed files or ran commands with one line:

```
Proof: <planned|edited|checked|running|seen> — <what you ran or saw>
```

Good:
- `Proof: seen — screenshot of /pricing at 390px shows the three cards stacked, no overflow`
- `Proof: running — deployed v1.4.2; curl https://app.example.com/version returns 1.4.2`
- `Proof: checked — pytest: 48 passed; not seen in the browser`

Bad:
- `Proof: seen — looks good` (names no evidence)
- `Proof: checked` (nothing after the rung)
- `Done!` (no proof line)

If the proof-first hook is installed, it checks this line and sends the turn back once for a fix in these cases:
- The line is missing, or it has no evidence after the rung.
- It claims `checked` and no command ran.
- It claims `seen` and the same turn has no browser, preview, screenshot or image tool call, no live request (`curl`, `wget`, `Invoke-WebRequest`), and no query of real data.
