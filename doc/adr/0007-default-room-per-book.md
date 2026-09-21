# 7. Default room per book, as a filter only

Date: 2026-09-19

## Status

Accepted

Amends 0003, 0006

Amended by 0012

## Context

The editor picks scenes from the bridge, grouped by room or zone (ADR 0006). The list contains every scene of the home, while a book is normally staged in one room. For each moment, the author scrolls past scenes that will never be chosen, or has to know the scene name to search for it. The problem grows with the number of rooms, not with the size of the book.

Two ways to use a room stored on the book were considered:

- as a filter: the picker starts with that room, the cues keep their own `scene.room`;
- as an inheritance default: a `scene` without `room` resolves in the book's room.

Inheritance would additionally allow moving a whole book to another room with one change, and would shorten the files. It would also make the field read-critical: `book_problems`, `Bridge.resolve` and the reading client's call to `/api/scene` would all have to carry the book room, and a missing `scene.room` would change meaning from "unique across the home" to "the book's room".

## Decision

A book may carry a `room` field next to `title`. It only decides what the light picker shows; it never takes part in resolving a scene. Cues keep the room of their scene explicitly, so a book stays unambiguous and reading ignores the field entirely.

- The editor shows the room under the title as "Standardraum", with "Alle Räume" when it is not set. It is picked from the rooms and zones known to the bridge, in the same sheet as scenes and sounds.
- Picking the first scene of a book that has no room set stores that scene's room. The open list stays as it is and says what happened, so nothing moves under the finger. Configuring it up front is therefore never necessary.
- The light picker starts filtered to that room and drops the room headings, which carry no information with one room. A line under the search switches between "Nur «Raum»" and "Alle Räume" for that one visit; it never writes to the book. The stored room changes in exactly two ways: through the chip, and once automatically with the first scene of a book that has none.
- A scene already chosen in a moment stays visible and selected regardless of the filter or the search, as does a scene that is no longer on the bridge. Where the list would not contain it, it is pinned above with its own room; tapping it recalls it, like any other entry.
- If the room holds no scenes, for example after it was renamed in the Hue app, the picker says so and shows all rooms instead of an empty list. The same case in the room picker keeps the stored room as a selected entry marked "nicht auf der Bridge".
- The server accepts `room` as a book field and reports a non-text value as a problem, like `title`. A room that no longer exists is not a book problem: it does not affect reading, and the shelf lists what breaks reading.
- Books are written with `title`, `room`, unknown fields, then `cues`, so the layout stays the same no matter in which order the editor sends the fields.

## Consequences

- Preparing a book in a home with several rooms means scrolling one room's scenes instead of all of them, without a setup step.
- The field is editor-only. A book file carries a value that the reading mode ignores, and the room of a cue is stored twice: once per scene and once for the book.
- Deliberately mixing rooms in one book still works, through "Alle Räume zeigen"; the book's default is not changed by picking a scene elsewhere.
- Moving a book to another room still means changing every cue. If that becomes a real need, inheritance can be added on top of the same field, at the cost described above.
