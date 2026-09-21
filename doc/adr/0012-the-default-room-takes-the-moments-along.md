# 12. The default room takes the moments along

Date: 2026-09-21

## Status

Accepted

Amends 0007

## Context

ADR 0007 made the book's `room` a filter and nothing else, and accepted one
consequence: moving a book to another room means changing every cue by hand. That
is the second of the two reasons the chip is ever tapped. The first is setting up,
where the book has no scenes yet and there is nothing to move.

In the second case the editor is actively unhelpful today. The chip changes where
the light picker starts, while every moment keeps pointing into the old room, so
the author walks through the whole book repeating the same edit. Nothing in the
interface says that the two have drifted apart.

Inheritance would fix it in the file instead of in the editor, and was rejected in
0007 for reasons that still hold: `room` would become read-critical, and
`book_problems`, `Bridge.resolve` and `/api/scene` would all have to carry the
book's room. A bulk rewrite in the editor reaches the same goal and leaves reading
untouched.

Hue offers no identity for a scene beyond its name and its room, so the only
possible join between two rooms is the scene name. A move can therefore end in
scenes that do not exist in the target room. That is a statement the author has to
see before tapping, not a surprise afterwards.

## Decision

When the moments of a book all play scenes from one room and the default room is
set to a different one, the room picker offers to take the moments along. Moving
writes `scene.room` of every moment; the names never change.

- The offer lives in the line under the picker's search, the same slot the light
  picker uses to say what it shows. No confirmation dialog, no nested sheet, and
  the decision stays in the sheet where it arises.
- The line names how many moments play in which room and how many of their scenes
  the target room already has, before the tap. After the move it names the room
  the moments play in now and how many scenes are missing there.
- Moments whose scene the target room does not have are moved as well. The author
  may be about to create them in the Hue app, and the server reports every missing
  scene as a problem on the next save.
- The move is reversible twice over: «Rückgängig» in the same line, and, because
  only the room is written, choosing the old room again offers the exact same step
  back.
- No offer where there is nothing unambiguous to move: a book whose moments name
  more than one room, or that leaves a scene without a room, keeps them and the
  line says so. A target room the bridge does not know, which includes every room
  in dry mode, produces no offer at all.
- The offer follows from the state, not from the tap. A book whose stored room has
  drifted from its cues, after hand-editing or a rename in the Hue app, is offered
  the move as soon as the picker opens.

## Consequences

- Moving a finished book to another room is one tap instead of one edit per moment.
- The stored room and the room of the cues can still differ, by hand-editing or by
  «Alle Räume zeigen». The editor now offers to align them but never does it on its
  own, so `room` stays what 0007 made it: a filter that reading ignores.
- Renaming a room in the Hue app is not repaired by this: the old name is not on
  the bridge, so it cannot be a target. Picking the new name and moving is the way
  through, and it is the same single tap.
- Nothing changes in the file format, the server or the reading mode.
