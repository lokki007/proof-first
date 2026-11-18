---
name: prove-it
description: Use before saying work is done, fixed or live. Shows how to check that it really works (look at it, run it, or say "not yet") and how to write the Proof line. Use for UI changes, bug fixes, deploys, data changes and anything a person will look at.
license: MIT
---

# Prove it

Before you say "done", check it the way the user would. Then end with one line:

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
- `Proof: seen — screenshot of /pricing on a phone width: three cards stacked, nothing cut off`
- `Proof: seen — curl https://app.example.com/version returns 1.4.2`
- `Proof: tested — pytest: 48 passed; I didn't open it in a browser`
- `Proof: not yet — the staging login is down; to check: open /settings and save the toggle`

Bad:
- `Proof: seen — looks good` (doesn't say what you looked at)
- `Proof: tested` (doesn't say what ran)
- `Done!` (no proof line)

## If the proof-first hook is installed

It sends your message back once if:
- the proof line is missing or says nothing after the word;
- it says `tested`, but nothing ran;
- it says `seen`, but nothing was looked at (no browser, screenshot, image, live request or data query).
