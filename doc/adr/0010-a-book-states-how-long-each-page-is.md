# 10. A book states how long each page is

Date: 2026-09-21

## Status

Accepted

Amends 0009

## Context

ADR 9 divides the knowledge about a mid-page moment in two: the author knows
*where* in the text it sits, the board measures *how fast* tonight's reader
reads. The board multiplies the two and arms a timer.

Reading a picture book showed that a third thing is missing, and that neither
of the two knows it: **how long this one page is compared to the others.**

The book that exposed it alternates almost regularly between a picture page and
a page of verse:

```text
page  2   4   6   8  10  12  14  16  18      page  3   5   7   9  11  13  15  17
     1400 459 1164 1194 1082 1272 528 1237 324     599 523 638 619 607 1338 665 1135
```

A factor of four between the longest and the shortest page. The pace of ADR 9
is a single median over the last five page turns, so it lands between the two
sorts and is wrong on *every* page, alternately too short and too long. On the
long pages every moment crowded into the first half — an effect written for 97 %
of the page fired after 58 of its 104 seconds. On the shortest page the last
moment was still 29 seconds away when the page was turned, and a page turn
drops what is pending: it fell out silently.

Both failures have one cause, and it is not a bad estimate. The estimate is
being asked a question it has no data for.

So: who knows a page's length?

- **The reader does not**, in advance, and would have to be asked every evening.
- **The board knows it afterwards** — it sees every page turn and could remember
  how long each page took. But that knowledge would then live in the device,
  beside the book rather than in it. The file would carry `page` and `at` and
  leave out the third part of the same answer: invisible, not checkable by the
  shelf, not correctable by hand, not in the diff, and gone the moment the book
  is passed on. Whoever received the file would get a book that only starts
  working properly after one read-through, with nothing on screen saying why.
- **The author knows it**, by looking at the page. It is a property of the book,
  like the position `at` is, and unlike the pace it does not change with the
  reader.

That last point is what settles it. A book file answers "when" for every moment;
splitting one answer across the file and one device's storage would be the
inconsistency, and it would have to earn itself. It does not.

This does not contradict ADR 9's reason for keeping duration out of the book.
What was rejected there was writing a *duration* into a book — seconds, which
would be re-guessed for every reader. A relative length is not a duration. It
says how this page compares to the book's own pages, and that comparison holds
for the grandparents as much as for the parents.

## Decision

**A page moment may say how long its page is.** An optional `span` on a cue that
carries a `page`: how many normal pages of this book that page is worth.

```json
{ "label": "Im Wald",     "page": 7, "span": 0.6, "scene": {"name": "Wald"} },
{ "label": "Es knackt",   "at": 0.6, "oneshot": "ast.mp3" },
{ "label": "Die Lichtung", "page": 8, "span": 1.9 }
```

Absent means 1, so every book written so far keeps running exactly as before.

**The numbers are relative, so there is no global way to get them wrong.** The
board does not read `span` as a duration; it divides by it. Every measured page
turn is divided by the `span` of the page being left before it enters the
median, so the median measures seconds *per normal page* rather than per page.
A moment then fires at `at × span × median`. Doubling every `span` in a book
doubles the median too and changes nothing. Only the pages' proportion to one
another matters — which is the only thing the author can actually see.

The clamp of ADR 9, 15 to 240 seconds, now applies to the normal page. A `span`
is a number between 0.2 and 5; outside that the shelf reports it (ADR 5) and the
board reads it as 1, so a mistyped file plays at worst as it does today.

**In the editor it sits where the page is chosen.** The "when" sheet gains a
second slider under the page, from short to long, and one is never obliged to
touch it: a book is authored as before and every page is normal. One touches it
when an effect on that page came too early, which is exactly what one notices
while reading a trial run.

## Consequences

- The estimate can be right, which the one before could not. For the book above,
  the worst moment moves from 46 seconds too early to within a few seconds.
- The fuse bar becomes worth looking at. It was already the only warning before
  a one-shot fires (ADR 9), but on a long page it filled at the wrong speed.
- A book file is complete again: everything about "when" stands in it, in one
  place, checked by the shelf and readable by hand. It can be passed on and
  works on the first evening on someone else's board.
- Seventeen more numbers may be written per book, but none of them has to be.
  A book with no `span` at all behaves exactly as it does today, badly on a
  picture book and well on a book of even pages.
- Pages that carry no moment of their own cannot state a length, and their turns
  enter the median as normal pages. They have no `at` moments to place — a
  position always belongs to a page that has a cue — so only the median is
  slightly noisier. Accepted.
- The author now guesses something that the board could measure. If that guess
  turns out to be the annoying part, the board can offer its measurement in the
  editor for the author to accept with one tap — the number would still end up
  in the book. That is a separate decision and is not taken here.
