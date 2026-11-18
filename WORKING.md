# How to work with me

Four rules for AI agents.

**1. If I'm asking or exploring, don't change anything.**
"How does this work?" or "explain first" means: answer, don't edit.

**2. Ask before anything hard to undo. Otherwise, just do it.**
That means data and migrations, money, deleting things, production settings, and public APIs. For everything else in the job I gave you, go ahead and tell me afterwards. "Do it all" means all of that job, nothing extra.

**3. Don't say "done" until you've shown it works.**
If you changed files or ran commands, end your message with one proof line:

```
Proof: seen — I opened /checkout and the new total shows
Proof: tested — the 48 tests pass and the build works
Proof: not yet — I changed the CSS but couldn't open the page
```

| Word | Means |
|---|---|
| `seen` | You looked at the real result: a screenshot, the live page, a real request, or the real data. |
| `tested` | You ran something: tests, a build, or the program itself. |
| `not yet` | You haven't checked it, and you say why. |

Anything a person will look at needs `seen`: pages, screens, deploys and data changes. "Not yet" is a fine answer. A wrong "done" is not.

**4. If I say it's still broken twice, stop and change course.**
Don't try the same fix a third time. Write a short handoff note:

```
Goal: what I asked for
Done: what works now (with proof)
Failed: what you tried and why it didn't work
Next: the one next step
```

Then suggest a different approach, or a different model.

---

If `~/.proof-first/me.md` exists, read it too. It holds my personal preferences.
