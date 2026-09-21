# 10. The book is closed and put on the shelf

Date: 2026-09-21

## Status

Accepted

Amends 0008, builds on 0009

## Context

An evening in the Super Vorlese-App ends in three steps. Only the last of them
reaches the room, and therefore the board:

1. The last page is on screen. The room's `page` is that page.
2. The closing overlay opens — the mood ritual for a synced pair, the plain
   „Ende" for a reader who is alone. The book is still open behind it, `page` is
   unchanged, and the app writes only `mood.open`, and only when a partner is
   there to coordinate with.
3. „Buch ins Regal stellen". The reader leaves the book, the app rewinds it to
   page 1 so that reopening begins a fresh read — and writes that 1 into the
   room.

Step 3 is what the board saw before this decision, and it read it as a page
turn: the evening ended with the light of page 1 and the loop of the opening
scene, as if the story were starting over in an empty room. The one thing the
board must not do at the end of the evening is start again from the beginning.

The signal is there, and it is unambiguous. `closeToFirstPage` is reachable only
from the last page, because the closing overlay only opens there. **A jump from
the last page to page 1 is the book going onto the shelf**; every other write of
1 comes from turning back from page 2. What the board lacked was the number of
the last page — its own cue list does not know it, since the last moment of a
book need not sit on its last page. The room says it: `book.pageCount`, written
when the room is created, next to the `hash` and `title` the board already
reads. No change in the other app, no rules deploy (ADR 8 still holds).

That leaves the question of what the end *is* for the board. Its own end-of-book
state so far was "the last moment, and no next one" — a state the reader arrives
at by tapping. Over a distance nobody taps, so the board would simply stand
wherever the last page turn left it. Three answers were considered:

- **Do nothing but say so.** Honest, but it leaves the closing image of a book
  unreachable over a distance.
- **Advance to the last moment of the book.** Symmetric to ADR 8's rule that a
  page without its own moment belongs to the page before it. But that rule
  exists to get the light right for *what comes next*, and at the end nothing
  comes next. What would be left is a silent light change — the skipped
  moments' one-shots stay mute (ADR 3) — at the most delicate minute of the
  evening, asserting moments that were never read.
- **Let the book say what its end looks like.** The author knows whether this
  book ends on a night light, on darkness, or on nothing at all.

## Decision

**A book may carry a closing moment, and it is a moment like any other.**

```json
{ "page": 20,    "label": "Abendrot",  "scene": {"name": "Abendrot"} },
{ "page": "end", "label": "Nachtlicht", "scene": {"name": "Nachtlicht"}, "loop": null }
```

`page` already answers "when does this moment come", and "when the book is
closed" is an answer to that question. Hence the same field rather than a second
one: page, position and closing moment exclude each other, and in one field they
do so by themselves. `"loop": null` fades the sound carpet out, which is what
most books will want; a closing moment with no `oneshot` is silent, which is
what most evenings want.

**It is reached from two directions, and does the same thing from both.** The
app puts the book on the shelf, or whoever is at the board taps "weiter" past
the last moment of the story. The first is a page turn onto the closing moment
in the sense of ADR 8 — restore the cumulative state, play the entry one-shot —
and the second is an ordinary tap. A book with a closing moment therefore ends
the same way at home and over a distance, which is the property ADR 9 was
written for.

**The closing moment belongs to no page**, not even the last one. Turning onto a
page the book gives no moment of its own advances to the last moment of the
preceding page (ADR 8) but never into the closing moment: a page that is being
read is not the end of the book.

**Without a closing moment, the board changes nothing.** Light and loop stay as
the reading left them. The board never switches anything off on its own — that
was true of "Ende des Buchs" before this decision and stays true now.

**The end is visible.** The chip that shows the room's page reads „Ende", and
the reading screen says once that the app has closed the book (rules 3 and 4).
The chip is about the room; where the board itself stands is what its own screen
shows, unchanged (ADR 8).

**Nothing waits any more.** A position still pending on the last page (ADR 9)
expires with the closing, exactly as a page turn expires the positions of the
page being left. The pause between closing the book and opening it again is not
reading, so it is not measured into the pace either.

**Reading the same book again starts over.** The next page turn ends the closed
state, and the board treats that turn as entering the page — with its one-shot —
even though it moves backwards through the cue list. Whoever is reading the book
a second time is at its beginning, not returning to a page they have read.

**The shelf checks it** (ADR 5): `"end"` is the only text `page` accepts, it
must be the last moment of the book, and it carries no `at`. A closing moment
alone is not page numbering: a book that has one and no page numbers cannot
follow the app, and the shelf says so.

## Consequences

- The board depends on one more field of the other app's room, `book.pageCount`,
  with the same terms as ADR 8: one household, both repositories, and it breaks
  if that field goes away. A room created without a book descriptor carries no
  page count; there the end is not detected and the closing moment is only
  reachable by tapping.
- A book of exactly two pages cannot be told apart: turning back from page 2 and
  closing the book both write 1 from the last page. Irrelevant for books with a
  cue list, and named here rather than guarded against.
- If the stream was down while the app moved onto the last page, the board never
  saw it there and follows the closing onto page 1 as before. It reconnects on
  its own; only this one moment is lost.
- Reloading the board's browser after the end reconnects fresh, reads page 1 and
  goes to the start of the book. The closed state is deliberately not stored: it
  belongs to an evening, not to a device.
- **The mood ritual is invisible to the board.** It runs under the light and the
  loop of the last moment reached, which suits it — the children are saying how
  the story felt, and the story's light is the right backdrop. But a position on
  the last page that has not fired yet can still go off in the middle of it,
  one-shot and all, because the board learns of the end only afterwards. Curing
  that would mean reading `mood.open`, which is written only when a partner is
  present and is taken back when the ritual is cancelled. Not worth reversing
  ADR 8's "the rest of the room is none of the board's business" for.
- Leaving a book on the board itself ("Andere Bücher") does not trigger the
  closing moment. Whoever goes back to the shelf is usually fetching the next
  book and does not want a night light.
