# 3. Cue list per book as interaction model

Date: 2026-09-19

## Status

Accepted

## Context

While reading aloud, attention belongs to the book and the children. Operating the app must not require looking for the right control, and it happens in a dimmed room.

Two interaction models were considered:

- A free board: fixed buttons for moods and effects ("night", "thunderstorm", "forest"), combined freely while reading. Universal and needs no preparation, but requires choosing the right button in the moment.
- A cue list per book: the sequence of light and sound changes is prepared in advance, and while reading only "next" is triggered. Needs preparation per book, but reduces operation to a single action.

## Decision

Each book is a JSON file in `books/` with an ordered list of cues. A cue has a `label` and optionally:

- `scene`: a Hue scene (`name`, optional `room`, optional `dynamic`);
- `loop`: a background sound. A file name crossfades to that sound, `null` fades out, an absent field keeps the current loop;
- `oneshot`: a single sound effect, played once;
- `triggers`: keywords for possible future voice triggering. Stored but not used.

The UI shows the upcoming cue in large type; tapping anywhere on that area triggers it. "Back" restores the cumulative state (last scene, current loop) of the previous cue without replaying one-shot effects. Arrow and page keys work as well, so that Bluetooth page turners can be used.

The UI uses a dark, low-luminance palette so that the screen does not compete with the room lighting.

## Consequences

- Each book needs a prepared cue file before it can be used. There is no UI for editing cues; files are written by hand or with an agent.
- Improvising while reading is limited to moving forward and back through the list. Skipping ahead or combining effects freely is not possible.
- "Back" depends on computing the cumulative state from the start of the list, which is why the semantics of an absent `loop` field ("keep") differ from `null` ("fade out"). Changing these semantics affects existing book files.
- "Back" from the first cue to the start fades out the loop but leaves the light as it is. The lighting from before reading is not restored.
- Book files are not validated up front. Missing sounds are reported when a book is opened, but scene names are only resolved when their cue is triggered, so a typo or a renamed scene only surfaces in the middle of reading.
- The `triggers` field keeps the data model open for voice triggering without committing to it. How voice triggering would work is a separate decision, to be recorded when it is implemented.
