---
name: prove-it
description: Use before saying work is done, fixed or live. Shows how to check that it really works (look at it, run it, or say "not yet") and how to write the Proof line. Use for UI changes, bug fixes, deploys, data changes and anything a person will look at.
license: MIT
---

# Prove it

Before you say "done", check it the way the user would. Most "it's still broken" replies come from three mistakes, so avoid them:

1. **Checking your idea of the request.** Re-read the user's last message and tick off each thing they asked for, in their words.
2. **Handing the check back.** "Reload and check", "let me know if it works" and "tests not run" make the user your tester. Do the check yourself. Hand it over only when it needs their device, login or taste, and then write `Proof: not yet — why`.
3. **Looking without judging.** A screenshot proves something rendered, not that it's right. Compare it with the request, the design or the old version, and name one thing that could still be wrong.

If the user says it's still broken, reproduce the failure the way they saw it before you change code.

Then end with one line:

```
Proof: seen | tested | not yet — what you looked at or ran
```

## How to see it

| What you changed | How to see it |
|---|---|
| A web page or screen | Open it, reload, take a screenshot, and say what you see. Check the thing that changed. |
| A flow (login, checkout) | Click through it like a user, and capture the end. |
| An API | Send a real request (`curl`). Report the status and the part of the reply that matters. |
| Data | Count or query the real data (or staging) before and after. |
| A desktop or phone app | Take a screenshot of the window or device. |
| A deploy | Open the live URL, and confirm the new version is the one being served. |
| Code with no screen | Run the tests or the program (`tested`). |

## Good and bad proof lines

Good:
- `Proof: seen — screenshot of /pricing on a phone width, against the request: three cards stacked, nothing cut off; the badge colour is still a guess`
- `Proof: seen — curl https://app.example.com/version returns 1.4.2`
- `Proof: tested — pytest: 48 passed; I didn't open it in a browser`
- `Proof: not yet — the staging login is down; to check: open /settings and save the toggle`

Bad:
- `Proof: seen — looks good` (doesn't say what you looked at)
- `Proof: tested` (doesn't say what ran)
- `Done!` (no proof line)
- `Proof: tested — build passes. Reload the page and check the header.` (hands the real check to the user)

## If the proof-first hook is installed

It sends your message back once if:
- the proof line is missing or says nothing after the word;
- it says `tested`, but nothing ran;
- it says `seen`, but nothing was looked at (no browser, screenshot, image, live request or data query);
- it says `seen` or `tested`, but the message asks the user to do a check ("reload and check", "let me know if it works", "tests not run").

When the user says it's still broken, the hook reminds you to reproduce the problem first.
