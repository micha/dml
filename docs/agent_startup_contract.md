# Agent Startup Contract

This file defines mandatory startup behavior after `td usage -q`.

## Required Sequence

1. Run `td usage --new-session` once at conversation start (or after `/clear`).
2. Run `td usage -q`.
3. Read this file before any other action.

## Session Safety

- Do not run `td usage --new-session` again mid-task.
- Use `td current` or `td context <id>` to refresh state.
- Start work with `td start <id>` before implementing changes.

## Work Logging and Handoff

- Add meaningful progress notes with `td log <id> "..."`.
- Capture state with `td handoff <id>` before stopping.
- Submit with `td review <id>` when ready.

## Scope and Validation

- Treat issue acceptance criteria as the source of completion truth.
- If build/test execution is expected, run commands and record outcomes.
- If criteria are ambiguous, log a recommendation to improve them.
