# 4. Audio plays regardless of silent mode

Date: 2026-09-19

## Status

Accepted

## Context

Audio runs in the browser via the Web Audio API (see ADR 0002). On iPadOS and iOS, Safari treats Web Audio as ambient sound by default: it is muted while the device is in silent mode (Control Center or the ring/silent switch). Media elements are not affected, which makes the behavior easy to miss. There is no error and the app looks fully functional, the lights switch, only the sound is missing.

The iPad is often in silent mode while reading, so that notifications do not interrupt. The first real use of the app failed exactly this way.

Two options were considered:

- Keep the default: silent mode doubles as the off switch for the app's sound. Safari cannot detect silent mode, so the UI could only show a general reminder, not a targeted warning.
- Declare the page as media playback: sound plays regardless of silent mode, like a music player.

## Decision

Before creating the `AudioContext`, the UI sets `navigator.audioSession.type = "playback"` where the Audio Session API is available (Safari 17 and later). Sound effects and loops then play regardless of silent mode.

## Consequences

- Silent mode no longer mutes the app. To read without sound, lower the volume or use a book without sound cues.
- Starting the app's audio interrupts other audio playback on the device, such as music or podcasts.
- Devices before iPadOS/iOS 17 keep the default behavior and stay silent in silent mode, without any hint in the UI.
- On iPad and iPhone every browser uses WebKit, so this applies regardless of the browser used. Desktop browsers do not mute Web Audio in this way; the setting changes nothing there.
