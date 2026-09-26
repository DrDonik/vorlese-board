# 16. The editor draws the light of the book

Date: 2026-09-25

## Status

Accepted

Builds on 0006, 0014 and 0015

## Context

ADR 0014 makes the light the clock of the story. A lasting change needs a reason
in the story, and it must not make the room brighter than the time of day
allows. Brightness is to be compared by measured values, not by scene names.

Those values exist only in the terminal (`python3 server.py --scenes`). The editor
shows each moment as text, and a moment without a light change says
«unverändert». Whether the light of a book follows the story, grows darker
towards the night and never jumps without reason can only be judged by keeping
the whole sequence in mind, or by reading it on the Mac next to the scene list.
The scoring of Wasserschweine 2 found several such breaks only when the book was
read aloud.

## Decision

**The editor shows a light rail to the left of the moments.** It is always
visible while the bridge is known and exists only in the editor. The reading view
stays without it, so that nothing on the screen competes with the book.

- **Top to bottom are the moments, not time.** Each moment draws its own piece of
  the rail across its full height, so the rail stays aligned when a moment is
  opened.
- **The deflection to the right is the mean brightness** of the scene's lamps, the
  same value as in `--scenes`. At the left edge the room is dark.
- **The colour of the line is the colour of the room.** It is the colour of the
  lamps, mixed by their brightness and shown at full brightness, so that a
  dimmed red stays recognisable as red. Lamps without a colour of their own
  count as 2700 K. A room with all lamps off is drawn in grey.
- **The line is a staircase.** A moment that sets a scene draws a horizontal step
  at its top. A moment without a scene continues the line straight on, just as
  the cumulative state does (0003). Before the first scene there is no line.
- **A flash is a short spike** that leaves the line and returns to it, in the
  colour and brightness of the flash (0015). A flash that would not play, because
  there is no light to return to or it lies in another room, is not drawn.
- **A scene the bridge cannot resolve** (missing, ambiguous, without lamps) is a
  band in the warning colour until the next scene. The shelf check names a
  missing or ambiguous scene; a scene without lamps is only shown on the rail.
- **Tapping the rail next to a moment opens that moment.** The rail is hidden from
  screen readers, because every moment already names its light in text.
- **Without a bridge, in dry mode or when it cannot be reached, there is no rail.**
  The rail knows the values from the bridge only and does not guess.
- On the iPad the rail sits in the free margin left of the editor column. Where the
  margin is too narrow, as on the iPhone, it becomes narrower and the moments
  make room for it.

The server adds `brightness` (mean in percent) and `color` (`#rrggbb`, or `null`
when the scene is dark) to every scene in `/api/scenes`. It computes both from the
scene data it already fetches, so no extra request to the bridge is needed. The
editor loads the scenes once when it opens and takes over the fresh list whenever
the light picker loads it.

## Consequences

- The dramaturgy of the light can be checked at a glance: a room that gets
  brighter at night, a jump without reason or a missing change of the time of day
  show up as shape instead of having to be read out of names.
- The mean brightness is not the perceived one. A light strip at 80 % is darker than
  a ceiling lamp at 80 %. Within one room the comparison holds, and it is the same
  comparison ADR 0014 already asks for.
- A scene with contrasting colours mixes towards white. Blossom in one of the rooms
  draws as an almost white line. Drawing each lamp as its own stripe would be more exact but
  restless; the mixed colour is the start.
- Dynamic scenes are drawn with the mean of their static state.
- The rail shows the light of each scene regardless of its room. In a book whose
  scenes lie in several rooms, it mixes rooms in one line.
- A scene changed in the Hue app appears on the rail after the editor or the light
  picker has been opened again.
