# Purpose
This web app's purpose is to accompany story reading for kids with light and sound effects. It runs as a server and is accessed from a device (phone or tablet). It controls hue lights and plays sounds on the device. Books are "preprogrammed" using json files calling existing scenes on the hue bridge and playing sounds from a local folder for now.

# Implementation Guidelines
1. The app is intended for technically firm people who like to play around with gadgets in their lifes.
2. Always think user experience first. If the intended user experience or user flow is unclear, ask.
3. When proposing functionalities or architecture, always think it through on the meta-level. The context of the UI element in question is usually the level where decisions fall out automatically. Why does the user interact with this element? How did they get here? What do they want to achieve? What does this element do in the entire in-app and out-of-app workflow? What other exisitng or not-yet-existing elements are related?
4. Adhere to the Eight Golden Rules of Interface Design: @InterfaceDesign.md
5. Never jump straight to implementation. Always present your plan and the resulting user experience first and deliberate with the person requesting new code. Only implement new code when the requester explicitely states you should.
6. All new code will be carefully reviewed by an expert for correctness, security, edge cases, maintainability, and fit with the existing codebase. Implement with a goal of a single positive review and no iterations needed.
7. This is a personal, iPad first app and the maintainer controls all instances, so changes may freely break older clients or stored data without migration paths or fallbacks. Backward compatibility is never required. iPhone compatibility is a nice-to-have, not a must-have. 

# Pull Requests
Write the body in German as usual, but trigger auto-closing of issues with an English keyword: GitHub only auto-closes on `Closes #123` / `Fixes #123` / `Resolves #123`. Therefore: Name every issue the PR finishes on its own `Closes` line at the end of the body; the German prose above it may still explain what was fixed.

Significant architecture and product-scope decisions are recorded as ADRs in `doc/adr/`; consult them for context and add a new one when making such a decision.

Do not propose adding automated tests or a linter.

# Secrets
`config.json` contains the Hue bridge app key in plain text and is git-ignored. Never read, print, grep, or otherwise open it, not even partially. To learn whether the app is paired, rely on the server's startup output ("mit Bridge" / "Trockenmodus"). Use a placeholder like `{"bridge_ip": "192.168.x.x", "app_key": "<key>"}` when its format matters.
