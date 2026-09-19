# 2. Local server as bridge between browser UI and Hue

Date: 2026-09-19

## Status

Accepted

Amended by 0006

## Context

The app plays sounds and switches Hue light scenes while reading picture books aloud. It is operated from an iPad or iPhone in the home network.

The household runs Apple Home as its main smart home system. Hue lights are exposed to Apple Home via Matter; the Hue Bridge is a v2 (square) bridge, not a Bridge Pro. Scenes used by Hue switches live in the Hue ecosystem, all other scenes in Apple Home.

Constraints that shaped the decision:

- A browser page cannot use the CLIP API v2 directly: it is served over HTTPS with a self-signed certificate that browsers reject, and it does not allow cross-origin requests. A page hosted outside the home network cannot reach the bridge at all.
- The v1 API is reachable over plain HTTP from a page in the home network (an HTTPS page may not call it), but it does not support dynamic scenes, and the page would have to hold the application key in the browser.
- The page has to be served from a device in the home network in any case.
- Apple Home cannot be controlled from a web page, and its scenes are static. Dynamic Hue scenes are only available through Hue.
- The app is a small private project. Setup and maintenance effort should stay minimal.

## Decision

A local Python server (`server.py`) runs on the always-on Mac in the home network. It uses only the Python standard library.

The server:

- serves the browser UI (`static/`), the sound files (`sounds/`) and the book files (`books/`, via `/api/books`);
- recalls Hue scenes on behalf of the UI through the CLIP API v2, authenticated with an application key stored in `config.json` (created once via `server.py --pair`);
- resolves scenes by name and optional room or zone at runtime, case-insensitively, and rejects ambiguous or missing names with an explanatory error;
- accepts the bridge's self-signed certificate without verification;
- serves only files inside `static/` and `sounds/`, checked against the resolved file path, so that `config.json` and the source are never exposed;
- runs in dry-run mode without `config.json`: scene recalls are logged, sounds work normally.

Audio runs in the browser via the Web Audio API. Loops are crossfaded with gain nodes, because iOS does not allow setting the volume of media elements from script.

The UI is accessed over plain HTTP in the home network. There is no authentication.

## Consequences

- The app controls Hue directly and bypasses Apple Home. Scenes used by the app must exist in the Hue app and are not visible as scenes in Apple Home. This extends the existing split (Hue for switch scenes, Apple Home for everything else) to one more use case.
- Dynamic Hue scenes can be used, which Apple Home cannot provide.
- The Mac must be running and reachable. If the server is down, the app does not work at all.
- Without HTTPS, browser features that require a secure context are unavailable, notably microphone access and the Screen Wake Lock API. Device auto-lock must be disabled manually while reading. Any future voice triggering needs HTTPS in the home network or a native app.
- TLS to the bridge is unverified. Acceptable in the home network, not beyond it.
- Any device in the home network can trigger scenes. Acceptable for a household app.
- Renaming a scene in the Hue app breaks the book files that reference it. The error surfaces in the UI and the book file must be updated.
- No dependencies to install or update. Tests (`tests/test_server.py`) run against a simulated bridge, so the bridge integration itself is only verified manually.
