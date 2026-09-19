# 6. Book editor in the app, protected by a PIN

Date: 2026-09-19

## Status

Accepted

Amends 0002, 0003

## Context

Writing book files by hand (ADR 0003) means working from memory: exact scene and room names from `server.py --scenes`, exact sound file names, and the three-way semantics of `loop` (file name, `null`, absent). Whether a scene fits a moment can only be judged by seeing it, which the hand-written file does not allow. ADR 0005 reports mistakes early, but does not remove the need to make them.

Books are prepared on the Mac, but in the app, with the lights in view. Sounds are downloaded on the Mac directly into `sounds/`. The iPad remains the reading device and may be used for small corrections.

An editor writes files on the server. Until now the app had no authentication (ADR 0002), because it could only switch lights, which is harmless and not persistent. Writing books is persistent, and children use the same iPad.

## Decision

**Editor.** The shelf offers "Bearbeiten" per book and "Neues Buch". The editor is a list of moments:

- scenes are picked from the scenes on the bridge, grouped by room or zone; picking a scene recalls it immediately, so choosing is trying out;
- sounds are picked from the files in `sounds/`, re-read every time the picker opens, and can be listened to before picking;
- `loop` is presented as an explicit choice between "keep playing", "switch to …" and "fade out";
- moments can be inserted, reordered and deleted, with a short-lived undo after deleting;
- "read from here" switches to reading mode at that moment, with light and loop set to the state they would have there.

Scenes are not created or changed in the app; that stays in the Hue app. Sounds are not uploaded through the app; they are placed in `sounds/` on the Mac.

**Saving.** Every change is saved immediately; there is no draft and no save button. The server writes `books/<id>.json` atomically, keeps fields the editor does not know (such as `triggers`), and refuses to save a book that could not be opened (ADR 0005). Problems that do not prevent opening are allowed, so that a book can be saved while it is being built. The file format stays the same, so files can still be edited by hand and kept in git.

Each save carries the version of the file the editor started from (a hash of its content). If the file has changed since, for example because it was edited by hand on the Mac while the editor was open on the iPad, the server refuses the save instead of overwriting it, and the editor offers to reload.

The server writes books in a fixed layout with one moment per line, so that a change to one moment is a one-line diff and files stay easy to edit by hand.

A new book gets its file name from its title (lower case, umlauts spelled out, a number appended if taken). Renaming the title later does not rename the file. Deleting books and renaming files stays on the Mac.

**PIN.** Editing requires a PIN; reading never does.

- The PIN has six digits and is set on the Mac with `server.py --pin`. Only a PBKDF2 hash is stored, in `config.json`.
- Entering the correct PIN creates a random session token, kept in server memory and sent as an `HttpOnly`, `SameSite=Strict` cookie. It is valid until the server restarts.
- After five wrong attempts, PIN entry is locked for one minute.
- Every write request, and loading a book for editing, must carry the session cookie and a custom request header, and its `Host` header must be `localhost`, a `.local` name or an IP address. A web page on the internet can produce neither: the header would need a CORS permission the server never grants, and a DNS rebinding attack arrives with the attacker's own domain as host. This blocks cross-site requests and DNS rebinding from web pages opened on any device in the home network.
- Requests from the Mac itself (`localhost`) need no PIN, since whoever sits at the Mac can edit the files directly anyway. The header and host checks still apply.
- As long as no PIN is set, editing works only on the Mac. Other devices do not show "Bearbeiten" or "Neues Buch"; the shelf says how to set a PIN.
- Write requests can only create, change or delete files named `books/<valid id>.json`.

## Consequences

- Preparing a book no longer requires remembering or copying names, and scenes are judged by seeing them. Hand-editing remains possible. This replaces the consequence of ADR 0003 that there is no UI for editing cues.
- Every change is persistent at once. Mistakes are undone in the editor or, beyond that, with git.
- The first save from the editor reformats a hand-written book file into the fixed layout. Formatting choices made by hand are not kept.
- The app is no longer free of authentication (ADR 0002). The PIN keeps out children, guests in the home network and web pages. It does not protect against someone who captures traffic in the home network: the app runs over plain HTTP, so PIN and session cookie travel unencrypted. Real protection would require HTTPS, which ADR 0002 left out.
- Triggering scenes stays open to every device in the home network, as before; the editor's scene preview uses the same endpoint.
- The PIN has to be entered again on the iPad after every server restart.
- With six digits and the lockout, guessing takes months on average. Fewer digits would reduce the PIN to a child lock.
