# 14. Light tells the story, sound sets the mood

Date: 2026-09-23

## Status

Accepted

Shapes how books are scored under 0003

## Context

The two scored books use light as their main instrument. In Drei Wasserschweine
wollen's wissen (Band 2), 58 of 120 moments change the light. About 25 of those
changes are mood lights: Blutrot for danger, Blossom whenever flamingos appear,
Gedimmt for sadness, Galaxie for flying, Showlicht for a performance. About ten
more exist only to take a mood light back to the light of the scene. Arche Boa
follows the same pattern.

Reading Wasserschweine 2 aloud showed that a lasting light change does not come
across as mood. The room is the setting of the story, so when it turns red or
dark, the listeners take it as a change of light in the story: night falls, a
lamp goes out, someone switches something on. A fear moment in Blutrot at
midnight makes the room brighter and red, and nothing in the text explains why.
Blossom is 80 % bright in the living room, so each flamingo scene in the night
lights the room up almost like daytime. Every mood light and its return also
count as one more event for the listeners to explain.

Sound does not have this problem. A heartbeat, giggling in the dark or a
beat under a rap add to the scene without claiming that the world of the story
has changed. Sound can also be layered and fades by itself, while the light is
a single state of the whole room.

A very short light change works differently from a lasting one. Nobody takes a
flash as the light of a scene. It is felt as a jolt, the way a sting in the music
is felt.

## Decision

Books are scored by the following rule.

- **A lasting light change needs a reason in the story.** It shows the time of
  day, a place with a light of its own, or a light the text names: the moon comes
  out, a motion detector switches on floodlights, a stage lights up.
- **Mood is carried by sound.** Loops give the atmosphere and one-shots give the
  beats. Where a moment has no fitting sound, silence is better than a mood
  light.
- **Light is used for mood only as a flash.** A flash is a short light change that
  returns to the light of the scene by itself. Its format and behaviour are
  decided in a separate ADR.
- **Brightness is compared by measured values, not by scene names.**
  `python3 server.py --scenes` shows the mean brightness of each scene. A lasting
  change does not make the room brighter than the time of day in the story allows.

## Consequences

- Books get far fewer light changes. In Wasserschweine 2 about 20 to 25 of the
  58 remain, and the cues that only took a mood light back disappear with it.
- Every light change that stays means something. The listeners can read the room
  as a clock of the story again.
- Moments that are now carried by light alone need a sound, or they become quiet.
  More sounds have to be found, and some beats are dropped.
- Scenes such as Blutrot, Blossom, Gedimmt and Galaxie stay on the bridge, but are
  used as flashes rather than as states.
- The two existing books have to be rescored. Choices that were confirmed under
  the old approach, such as Showlicht during the rap in Wasserschweine 2, are
  judged again by this rule.
- Until flashes exist, a mood moment has no light at all. This is intended: the
  book is better without the light than with a lasting mood light.
