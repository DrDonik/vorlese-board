# 17. No automated tests or linter

Date: 2026-11-18

## Status

Accepted

Amends 0002

## Context

The repository started with a test suite (`tests/test_server.py`) that ran the server against a simulated Hue bridge, while rule 8 of `AGENTS.md` already said not to propose tests or a linter. The two never ran anywhere automatically, and since #14 eight of the 39 tests failed without anyone noticing.

The rule comes from the maintainer's other projects, where tests were removed for a reason that applies here as well: once a suite exists, it becomes the yardstick of every review. Each new feature draws the question where its tests are, each test draws objections about missing edge cases, and both the coding agent and the review bot can invent edge cases without end. Review effort and token budget move from the feature to its tests. [ADR 8 of the Super Vorlese-App](https://github.com/DrDonik/super-vorlese-app/blob/main/doc/adr/0008-no-tests-or-linter.md) records the same decision.

Tests pay off where someone else bears the breakage: shipped code, several contributors, failures that surface late or silently. None of that holds here. The app has one maintainer who is also its only user, and a break shows the next time a book is read.

## Decision

There are no automated tests and no linter. The test suite is removed, and with it the consequence in ADR 0002 that tests run against a simulated bridge: the bridge integration and the server alike are verified by using them.

## Consequences

- Reviews look at the change itself, not at a suite around it.
- A regression surfaces in use rather than in a test run. That is accepted for a personal app.
- Agents and reviewers do not propose tests or a linter; rule 8 of `AGENTS.md` points here.
