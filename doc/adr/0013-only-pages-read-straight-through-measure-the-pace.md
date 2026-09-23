# 13. Only pages read straight through measure the pace

Date: 2026-09-23

## Status

Accepted

Amends 0009 and 0010

## Context

ADR 9 estimates the reading pace as the median of the last five page-turn
intervals, and ADR 10 divides each of them by the `span` of the page being left.
Every turn forward by exactly one page is a sample.

Nobody reads a book strictly forward, and two habits feed the median with
samples that are not reading at all:

- **Peeking ahead.** How long does the chapter go on, what is on the next
  picture? Flicking from page 7 to 10 and back gives three samples of one to
  three seconds each. Three of five samples are a majority: the median drops to
  the 15-second floor, and for the next two or three pages every mid-page moment
  fires far too early.
- **Going back.** From 7 to 6 and forward again measures the short second look
  at page 6 as if it were a reading of it, and the turn from 7 to 8 measures only
  the part of page 7 read after returning.

A page at the lower bound of `span` is a third, quieter source of noise. 0.2 is
where a picture-only page or a page with a single sentence ends up, whatever it
really takes. The few seconds of turning the page or a short pause are divided
by 0.2 and so count five times over.

## Decision

**A turn counts only if the page was read straight through:** entered from the
page before it and left to the page after it. Going back, jumping, and the page
the board finds when it connects never count, and neither does the page after
one of them. Its reading is either unknown or split in two.

**A page left after less than 10 seconds was glanced at, not read.** The
threshold applies to the time actually spent on the page, before dividing by
`span`. After the division, a four-second glance at a page of `span` 0.2 would
count as 20 seconds of normal reading and pass.

**A page of `span` 0.2 does not count.** It still has its length for placing its
own moments; it just does not measure the reader.

**The median runs over the last seven counted pages instead of five.** It then
takes four bad samples to move it instead of three. A real change of tempo, such
as a tired child lingering on the pictures, shows up one page later.

Unchanged: the clamp between 15 and 240 seconds per normal page, the default of
60 seconds until two samples exist, and that nothing is stored beyond the
connection.

### Why the 10 seconds are not derived from the 15-second floor

The two numbers answer different questions and are measured in different units.
The floor is about the reader and is counted in seconds per normal page: nobody
reads a whole normal page in less than 15 seconds. The threshold is about a
gesture and is counted in seconds on the clock: whoever turns the page again
within 10 seconds was not reading. `span` links them. On a page of length `s`,
10 seconds on the clock are 10/`s` seconds of normal reading.

Tying the threshold to the floor, which means dropping every sample below 15
seconds per normal page, would have two effects:

- The median could no longer fall below 15 seconds. The floor would become
  pointless instead of being a safeguard.
- It would cut off the lower half of a genuinely fast reader's samples and push
  the estimate upward. The median would stop being a median.

The one place where the two meet is the fastest reader the floor still allows.
At 15 seconds per normal page, a page with `span` below 2/3 takes less than 10
seconds and is dropped. Such a reader gets fewer samples, not wrong ones. At a
typical pace of a minute per page, only a `span` below 1/6 would fall under the
threshold, and `span` does not go that low.

The window of seven is independent of both. It fixes how many bad samples the
median absorbs (three), not what a sample is worth.

## Consequences

- Peeking ahead no longer moves the estimate. The glances fall under the
  threshold, and the page returned to after the jump back does not count.
- After going back, the first reading of the page left and the second look at
  the earlier page no longer count. One distorted sample remains: the page
  returned to counts from the moment of returning. The same holds for a page
  peeked away from in the middle, which counts only the part read before the
  peek. The median absorbs one of these; guarding against it would mean
  withdrawing samples after the fact. Not worth it.
- An evening yields fewer samples. The default of 60 seconds holds longer after
  connecting: the first page never counts, so the earliest estimate comes after
  the third turn instead of the second.
- A book made mostly of `span` 0.2 pages is barely measured and runs mostly on
  the default. Such a book has hardly any mid-page moments to place.
