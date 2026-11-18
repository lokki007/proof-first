# How to work with me

Four rules for AI agents.

**1. If I'm asking or exploring, don't change anything.**
"How does this work?" or "explain first" means: answer, don't edit.

**2. Ask before anything hard to undo. Otherwise, just do it.**
That means data and migrations, money, deleting things, production settings, and public APIs. For everything else in the job I gave you, go ahead and tell me afterwards. "Do it all" means all of that job, nothing extra.

**3. Don't say "done" until you've shown it works.**
Before you say it, do three things:

- **Re-read my last message.** Check off each thing I asked for, in my words, not yours.
- **Do the check yourself.** Don't end with "reload and check", "let me know if it works" or "tests not run". If you can do the check, do it. Hand it to me only if it needs my device, my login or my taste, and say so.
- **Judge it; don't just look at it.** Compare it with what I asked for (or the design, or the old version), and name one thing that could still be wrong.

Then end your message with one proof line:

```
Proof: seen — I opened /checkout and the new total shows
Proof: tested — the 48 tests pass and the build works
Proof: not yet — I changed the CSS but couldn't open the page
```

| Word | Means |
|---|---|
| `seen` | You looked at the real result (a screenshot, the live page, a real request, or the real data) and compared it with what I asked for. |
| `tested` | You ran something: tests, a build, or the program itself. |
| `not yet` | You haven't checked it, and you say why. |

Anything a person will look at needs `seen`: pages, screens, deploys and data changes. "Not yet" is a fine answer. A wrong "done" is not.

**4. If I say it's still broken, see it fail first. If I say it twice, change course.**
The first time, reproduce the problem the way I saw it before you touch code, then check the fix the same way. The second time, don't try the same fix a third time. Write a short handoff note:

```
Goal: what I asked for
Done: what works now (with proof)
Failed: what you tried and why it didn't work
Next: the one next step
```

Then suggest a different approach, or a different model.

---

If `~/.proof-first/me.md` exists, read it too. It holds my personal preferences.
