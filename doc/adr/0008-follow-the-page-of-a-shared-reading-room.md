# 8. The board follows the page of a shared reading room

Date: 2026-09-20

## Status

Accepted

Amends 0002, 0003

## Context

The household runs a second reading app: the
[Super Vorlese-App](https://github.com/DrDonik/super-vorlese-app), a static page
on GitHub Pages with a Firebase Realtime Database behind it. Two people on two
devices see the same book, and whoever turns a page turns it for everyone. It is
used for bedtime reading over a distance — grandparents reading to a grandchild
on a separate video call — and for reading a re-typeset book off the iPad at
home.

The board and that app answer to the same evening from two sides. Two situations
made the gap visible:

1. **Reading over a distance.** The lights are in the child's room; the person
   reading is elsewhere. Nobody in the child's room can operate the board — the
   child is in the call, and an adult tapping "weiter" beside them is the
   arrangement the board exists to avoid.
2. **Reading from the iPad at home.** The book is on the screen, and turning the
   page is already the gesture that marks every moment in the story. Tapping
   "weiter" on a second surface repeats a decision that has just been made.

Three facts about the other app frame every possible answer.

- **It cannot call the board.** It is served over HTTPS, the board over plain
  HTTP in the home network (ADR 2). Safari blocks that direction. This is the
  same wall that ADR 2 already hit with the bridge's own API.
- **It should not be changed for this.** Its room schema rejects unknown keys
  (`$other: false` in `database.rules.json`), so any new field means a rules
  deploy for an app that runs on other people's devices in other households. Its
  ADRs 26, 27, 36 and 37 deliberately shrink what a room carries and what the app
  becomes. A household gadget is the wrong reason to grow it.
- **It already publishes what the board needs.** A synchronised room carries
  `page`, refreshed on every page turn, plus `book.hash` and `book.title`. The
  database rules grant read access to anyone who knows the six-digit code.

One property of browsers makes the remaining direction cheap: a page served over
HTTP may open an HTTPS connection — it is only the reverse that is blocked. The
board's own page can therefore subscribe to a room with a plain `EventSource` on
the database's REST streaming endpoint. No SDK, no dependency, and no new code in
`server.py`.

## Decision

**The board follows a room. It reads, and never writes.** That is not only a
convention: the other app's database rules reject every key the board could
invent, and a page write would be indistinguishable from a page turn. The
board contributes nothing to the room, holds no lease (ADR 27 there), and cannot
keep a room alive.

**Moments carry a page.** A cue may have `"page": <number>`, the page value as
the other app publishes it. Page numbers ascend through the cue list. The cue
carrying a page number is that page's entry; cues after it without one belong to
the same page.

```json
{ "page": 7, "label": "Im Wald",      "scene": {"name": "Wald"}, "loop": "wald.mp3" },
{            "label": "Es knackt",    "oneshot": "ast.mp3" },
{ "page": 8, "label": "Die Lichtung", "scene": {"name": "Lichtung"} }
```

**A page turn is "ab hier lesen".** It moves to that page's entry cue and
restores the cumulative state there — the light and the loop as they would be
when read from the start. Turning *forward* onto a page also plays its entry
cue's one-shot: that effect is what entering the page sounds like. Turning back
does not, exactly as "Zurück" does not (ADR 3) — a page one returns to is being
re-read, and a thunderclap repeated on the way there startles rather than helps.
One-shots of cues that are skipped never play, in either direction. This is the
semantics ADR 3 already defines for "Zurück" and ADR 6 for "ab hier lesen"; no
third rule enters the app.

**A page the book gives no moment of its own belongs to the page before it.**
Turning onto such a page moves the board to the *last* cue of the preceding
page, not to that page's entry. Its light and loop therefore apply — the page
has been read — and a position still pending there (ADR 9) is left behind
rather than going off a page later, measured against the wrong page.

**The room speaks, but the board is not demoted to a display.** "Weiter",
"Zurück" and the page-turner keys keep working while a room is connected; they
are how a cue between two pages is reached. The next page turn overrides
whatever they did. There is exactly one place that says where the reading is:
the board's own screen.

**Connecting starts with the code, because that is what the person has.** The
shelf offers "Mit der Vorlese-App verbinden" and takes the six digits. The board
reads the room, matches `book.hash` against the `sync.hash` recorded in each book
file, and opens the matching book at the room's current page. If no book matches,
the shelf names the room's book title and asks which book on the shelf it is;
that choice records the hash in the book file. Nobody has to know which book file
belongs to which PDF.

The code itself is kept per book in `localStorage` on the board device, not in
the book file: it is a shared secret that belongs to an arrangement between two
devices and expires with the room, while the book file describes the book.
Opening a book reconnects its last code without asking.

**Connecting never asks for the PIN.** Recording the hash writes a book file and
therefore needs edit access (ADR 6), but connecting does not: the remembered code
alone carries the pairing on this device. Where the PIN would be needed, the hash
is silently not written rather than a dialog appearing in front of someone who
only wants to start reading. The next connection from the Mac records it.

**The connection is visible.** The reading screen says whether it is connected
and which page the room is on. A dropped stream reconnects on its own; the
database delivers the whole room node on connect, so the board lands on the
current page without asking anyone.

**The shelf checks the new fields** (ADR 5): pages must be numbers, must ascend,
a cue before the first page marker is a problem, and `sync.hash` must be a
string. A book without any `page` behaves exactly as before.

## Consequences

- Nothing changes in the Super Vorlese-App. There is no pull request there, no
  schema change, and no rules deploy.
- Reading with a room requires the internet in the room where the board stands.
  Reading without one still touches nothing outside the home network.
- The board depends on the other project's database URL and on the meaning of
  `page`, both hard-coded there. If either changes, the board breaks with it.
  Acceptable: one household, both repositories, and no backward compatibility is
  owed (rule 2).
- A room lives 45 days without a page turn. After a long break the pair creates a
  new code, and the board is told the new one. The recorded `sync.hash` survives
  that; only the code is re-entered.
- Because the board never writes, it can never renew a room's lease. A room that
  only the board watches ages out — which is correct, since nobody is reading in
  it.
- The book file gains a durable link to a specific re-typeset PDF. Re-typesetting
  a book changes its hash, and the link has to be made again.
- Backgrounding the board's browser tab drops the stream. Audio stops there
  anyway, so nothing is lost that was not already lost; returning to the tab
  restores both.
- Moments between two pages are only reached by tapping. Over a distance nobody
  taps, so they fall out. ADR 9 answers that; without it, this decision serves
  reading at home better than reading over a distance.
