# 15. A flash returns to the light of the scene

Date: 2026-09-23

## Status

Accepted

Amends 0003, builds on 0014

## Context

ADR 0014 allows light to carry mood only as a flash. A flash is a short light
change that returns to the light of the scene by itself. A cue can do this today
only with two moments: one that switches to the flash scene and one that switches
back. The motion detector in Wasserschweine 2 is scored that way. The second moment
has to be triggered by hand or timed from the reading pace, so the length of the
flash depends on the reader instead of on the effect, and the return moment also
has to name the light of the scene again. If that light changes later in the
score, the copy has to be changed as well.

A flash also behaves differently from a scene where state is concerned. "Back",
"Ab hier probelesen" and a page turn from the Vorlese-App rebuild the light from
the cumulative state of the list (0003, 0008). A flash is not part of that state,
in the same way that a one-shot is not part of the loop.

The Hue bridge handles about one scene recall per second reliably. A recall can
carry its own transition time, so a flash can switch on hard and fade back softly.

## Decision

A moment gets an optional field `flash`, next to `scene`:

    "flash": {"name": "Blutrot", "room": "Wohnzimmer", "seconds": 2}

- `name` and `room` work as in `scene`. `seconds` is the length of the flash
  between 1 and 10 and defaults to 2. There is no `dynamic`, because a palette has
  no time to move within a flash.
- **The flash switches on without a transition and returns to the light of the
  scene after `seconds`, with a soft transition of about one second.** The light of
  the scene is the cumulative scene at this moment, including the moment's own
  `scene`. A moment with both first flashes and then settles into its new scene:
  a scream, then darkness.
- **A flash is not state.** The cumulative state ignores it, so "Back", "Ab hier
  probelesen" and a page turn that skips a moment never play its flash, just like
  its one-shot. A page turn onto the moment's own page and the closing moment play
  both, as they already play the one-shot (0008, 0011).
- **Anything that sets the light ends a running flash.** The next moment, "Back",
  a page turn or the closing moment discards the pending return, and the light of
  the new position applies at once. Leaving the reading view during a flash
  performs the return immediately, so that the room is never left in a flash.
- In dry mode both recalls are only logged, as with any scene.
- **Editor.** Every moment row gets a field «Blitz» between «Licht» and «Teppich».
  It opens the same scene picker as «Licht», with chips for the length
  (1 · 2 · 4 · 8 s). Choosing a scene plays the flash in the room, including the
  return to the light of this moment.
- **Taking the moments along** to a new default room (0012) moves the room of
  their flashes as well. A book whose flashes play in another room than its
  scenes is mixed and is not offered the move.
- **A flash plays in the room of the light it returns to.** The return recalls
  the light of the scene, so a flash in another room would leave that room in the
  flash. The flash picker names the room of that light.
- **Shelf check.** The shelf reports a flash with an unknown scene, a length
  outside 1 to 10 seconds, a flash before any moment has set a light, and a flash
  in another room than that light. A scene without `room` gets its room from the
  bridge. Neither reading nor the editor plays a flash that has nothing to return
  to or that names another room, so that no room is left in a flash.

## Consequences

- A mood beat in light is one moment instead of two, and its length is part of
  the score instead of depending on the reader.
- The return always goes to the current light of the scene, so changing that
  light later in the editor needs no second edit.
- Two recalls within one second can be dropped by the bridge. The minimum length
  of one second avoids this for a single flash. A moment that follows a flash
  within a second can still lose the return; the next light change repairs it.
- A book with scenes in several rooms can flash only in the room of the current
  light. Returning to the last light of each room would allow more, but needs the
  room of every scene without `room` from the bridge, and no book needs it yet.
- The reading device only knows the rooms a book names. If the flash or the light
  leaves out `room` and the two lie in different rooms, the flash still plays; the
  shelf reports it.
- The return timer lives on the reading device. If the device sleeps during a
  flash, the return comes when it wakes up.
- The board sends scene recalls one at a time and in order, and drops a waiting
  recall once a newer one is queued. Otherwise a flash could overtake its own
  return and stay on. The length of a flash counts from the moment the bridge
  has switched it.
- A flash to the scene that is already on has no visible effect. The editor does
  not prevent this, because the light of the scene can still change before the
  book is read.
