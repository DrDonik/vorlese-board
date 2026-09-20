# 9. Moments inside a page are timed from the reading pace

Date: 2026-09-20

## Status

Accepted

Amends 0003, builds on 0008

## Context

With ADR 8, a page turn triggers the moment that carries that page. A moment in
the middle of a page has no event of its own: the child walks into the forest at
the top of page 7 and a branch cracks four sentences later, but the room only
ever reports the start of the page.

Over a distance nobody is at the board, so such moments never fire. The same
book would then sound richer at home than over a distance, and nothing on screen
would say what is missing. Making every moment a page moment avoids that by
giving up the branch — and a book that is prepared moment by moment should not
have to be written for the poorer of the two situations.

What is worth noticing is **who knows what**:

- The author of the book knows *where in the text* the moment sits: roughly in
  the middle of page 7. That is a position, and it is stable.
- The author does not know *how long* the page takes. The grandparents read more
  slowly than the parents, and both more slowly on a page with a picture to talk
  about. A duration written into the book would be re-guessed for every reader.
- The board sees every page turn, and therefore knows tonight's pace of this
  evening's reader, measured rather than assumed.

And one property of the content makes an estimate good enough: a mid-page effect
is atmosphere, not a cut. It may crack somewhat early or somewhat late without
spoiling anything. That is not true of the light at the start of a page, which is
why only the moments *between* pages are guessed.

## Decision

**A moment between two pages says where it sits; the board works out when that
is.** A cue without a `page` may carry `"at"`, a fraction strictly between 0 and
1 — its position within the page.

```json
{ "page": 7, "label": "Im Wald",   "scene": {"name": "Wald"}, "loop": "wald.mp3" },
{ "at": 0.6, "label": "Es knackt", "oneshot": "ast.mp3" },
{ "page": 8, "label": "Die Lichtung", "scene": {"name": "Lichtung"} }
```

**The estimate is the median of the last five page-turn intervals**, clamped to
between 15 and 240 seconds, so that one long pause over a picture does not
stretch the rest of the evening and a rapid flick through two pages does not
compress it. Until two page turns have been seen, a default of 60 seconds
applies. The estimate is per reading session; it is not stored and not carried
over to the next evening.

**One rule holds the two control paths together:**

> The next moment comes when someone taps or when its estimated time is
> reached — whichever happens first. A page turn overrides both.

This is what keeps "weiter" meaningful and keeps a single answer to "where are
we". The timer is not a second sequencer running beside the board; it is one
more way to trigger the very next moment, the same one the screen is showing.
Tapping ahead of the timer cancels it. A page turn drops every moment still
pending on the page being left; they do not catch up.

Timers are armed only while a room is connected (ADR 8), and only while the room
is on the position's own page. If the app has moved on — including onto a page
the book gives no moment of its own — the moment waits for a tap rather than for
a clock that is measuring the wrong page. Reading from a paper book is
unchanged: nothing fires by itself.

**The guess is visible, because the board acts on its own.** The upcoming moment
carries a thin bar that fills toward its estimated time. Whoever is at the board
sees what is about to happen and can tap to bring it forward — the estimate is
offered, not imposed (rules 3 and 7).

**The shelf checks it** (ADR 5): `at` must be a number strictly between 0 and 1,
must ascend within a page, and must not sit on a cue that carries a `page` or in
a book that has no pages at all.

## Consequences

- A book is authored once and works in both situations. Over a distance it runs
  through by itself; at home the same book can be taken over by tapping at any
  moment.
- The first page of an evening is guessed from the default, and a page that is
  paused over is guessed badly. The branch then cracks into a conversation, or
  the page is turned before it cracks at all and it falls out silently. Accepted:
  atmosphere, not a cut.
- A fired one-shot cannot be taken back. The bar is the only warning, and it is
  the reason the bar exists (rule 6 is not satisfiable here; rule 3 is).
- The board now does something nobody asked it to do at that instant. That is a
  departure from ADR 3, where every change came from a tap, and it is the reason
  this is a decision rather than a detail.
- Timing lives in the board, not in the book. A book carries positions, which
  stay true for every reader; nothing in a book file needs revisiting when a
  different person reads it.
- When positions turn out to be too coarse — when it matters that the branch
  cracks on *that* word — the answer is not a better estimate but the `triggers`
  field from ADR 3 and voice recognition. Over a distance the reader's voice
  comes out of the video call's speaker in the child's room, where the board
  stands, so one implementation would serve both situations. That is a separate
  decision, to be recorded if it is taken.
