# 5. Validate books on the shelf

Date: 2026-09-19

## Status

Accepted

Amends 0003

## Context

Book files are written by hand (ADR 0003). The author has to reproduce scene names, room names and sound file names exactly, and has to remember the semantics of the `loop` field. Mistakes only surfaced while reading: a syntax error showed as "Datei fehlerhaft" without a location, missing sounds were reported when the book was opened, and scene names were only resolved when their cue was triggered, in the middle of reading.

Preparing a book happens on the Mac and in the app itself, not while reading. The place to learn about problems is therefore the shelf, before a book is opened, with enough detail to fix each problem without guessing.

A book editor in the app is planned (ADR 0006). It will need the same checks when saving, so they belong on the server, not in the UI.

## Decision

The server checks every book whenever the shelf is loaded (`GET /api/books`) and returns the problems per book as ready-to-display German sentences, each naming the moment by number and label.

Two severities:

- **Cannot be opened** (`error`): invalid JSON (with line and column), not UTF-8, no `cues` list, a cue that is not an object, or a file name that is not a valid book id. The shelf shows the book greyed out with the reason. `GET /api/books/<id>` refuses such a book with the same reason.
- **Problems** (`problems`): the book opens, but something will not work as intended. Checked are:
  - missing or empty `label`;
  - unknown fields, on the book, on a cue and on `scene` (typically a typo such as `oneshoot`, which would otherwise be silently ignored);
  - field types (`scene.name`, `scene.room`, `scene.dynamic`, `loop`, `oneshot`, `triggers`);
  - sound files that do not exist in `sounds/`;
  - scenes that do not resolve to exactly one Hue scene, using the same matching and the same messages as recalling a scene while reading.

Problems do not block opening a book. A wrong scene in one moment should not prevent reading the rest.

Scenes are fetched fresh from the bridge on every shelf load, which also refreshes the cache used while reading. If the bridge cannot be reached, scenes are not checked and the shelf says so. In dry-run mode scenes are not checked either.

The shelf reloads when returning from a book and when the page becomes visible again, so that a book file edited on the Mac is re-checked by switching back to the browser.

## Consequences

- Typos in scene or sound names, and scenes renamed in the Hue app, show up on the shelf before reading, not in the middle of it. This replaces the consequence of ADR 0003 that book files are not validated up front.
- Loading the shelf now waits for the bridge (about a second with a reachable bridge, up to the five-second timeout with an unreachable one).
- Fields not listed in the book format are reported as problems. Extending the format means extending the list of known fields in `server.py`.
- Problems are plain sentences, not structured data. Sufficient for display; the planned editor may need structured problems per moment and would change the API then.
