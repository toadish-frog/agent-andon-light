# Claude Code Hook Integration: Agent Andon Light

`settings.snippet.json` maps agent events to `andon-light` CLI calls.

## Hook → Color Mapping

| Hook event | Color | Meaning |
| --- | --- | --- |
| `SessionStart` | idle (red) | Default state — a new session starts "not working yet" |
| `UserPromptSubmit` | working (green) | You just gave it something to do |
| `PreToolUse` | working (green) | Fires on every tool call — keeps the light green through tool-heavy stretches |
| `Notification` | waiting (yellow) | General "needs your attention" |
| `PermissionRequest` | waiting (yellow) | Specifically waiting on a permission decision (e.g. approve a `Bash`/`npm install` call) |
| `PreCompact` | flashing green (compacting) | Internal context compaction — still "alive," distinct from ordinary working |
| `Stop` | idle (red) | Turn/session ended normally |
| `SessionEnd` | idle (red) | Session terminated for any reason, including abrupt ones `Stop` doesn't cover |

Commands run synchronously, not `async` — see [Why Not `async`](#why-not-async) below. The `hooks` object from `settings.snippet.json` merges into `~/.claude/settings.json` (global) or a project's `.claude/settings.json`. This config has no visibility into what's wired up on the far side of the serial link — it just runs `andon-light` commands, and firmware ([`../device/firmware/`](../device/firmware/)) does the rest. Restart Claude Code (or start a new session) to pick up a config change.

## Design Notes

### `PreToolUse` Keeps the Watchdog Fed

`UserPromptSubmit`/`Notification`/`Stop` only fire at 3 discrete moments — nothing resets the firmware watchdog during a long stretch of tool calls in between, so the light can fall back to the stale/disconnected pulse mid-turn. `PreToolUse` fires on every tool invocation (reads, edits, bash commands) and sends `working`, so any tool-heavy turn keeps kicking the watchdog continuously. It doesn't cover a turn that's pure extended thinking with zero tool calls — there's no hook event for "still generating text" — so that gap is instead covered by a much longer firmware watchdog timeout (30 minutes); see [`../device/firmware/README.md`](../device/firmware/README.md).

### `PermissionRequest` vs. `Notification`

`PermissionRequest` is more precise than `Notification` alone for the specific "waiting on a permission approval" moment (e.g. approving a `Bash(npm install)` call). Both map to the same yellow action, so there's no harm in the overlap when `Notification` also fires for the same event.

### `PreCompact` Gets Its Own Color

Without a distinct color, a compaction pass would either stay on whatever color was last set (misleading if it was red/idle) or require another hook just to flip back afterward. Flashing green reads as "still alive, doing upkeep" at a glance, and naturally reverts to solid green (or whatever's next) once the following hook fires — no extra "compaction done" hook needed.

### `SessionStart` Makes the Default Deterministic

Without it, a new session inherits whatever color the previous session left behind — usually fine, since `Stop` already leaves it on idle/red, but not guaranteed if a prior session crashed mid-turn without a clean `Stop`. Setting idle explicitly on `SessionStart` removes that dependency on history.

### `SessionEnd` Catches Interrupts `Stop` Doesn't

Killing an active `claude` process with Ctrl+C (not just interrupting a turn) leaves the light stuck on whatever color was last set if only `Stop` is configured — `Stop` doesn't fire on user interrupts. `SessionEnd` fires on any termination reason (no matcher needed) and resets to idle (red). `Stop` stays alongside it so normal turn/session ends still resolve as fast as possible, without waiting on session teardown.

## Why Not `async`

Every command was originally `async: true`, to guarantee zero latency on real tool calls. `async` gives no ordering guarantee between hook invocations — only that each one is *launched* in order, not that it *finishes* in order. Each `andon-light set ...` call is a fresh Python process (spawn + import + open/close the serial port), measured at ~40-50ms — cheap, but not zero, and under load (e.g. a busy tool-heavy turn) that's enough jitter for a later-launched command to finish before an earlier one. Concretely: a session ends correctly on red (`Stop`), but a `Notification`/`PermissionRequest` command that fired earlier in the session had been delayed, and completes only after `Stop`'s `idle` command already landed — silently overwriting it with stale yellow.

Removing `async` makes Claude Code wait for each hook to finish before continuing, guaranteeing true event order. At ~40-50ms per call this isn't perceptible against real tool-call durations, so the latency `async` was meant to buy wasn't worth the ordering risk.

## Why Every Command Ends in `|| true`

If the board is ever unplugged or the CLI is run on a machine without it, every hook invocation would otherwise fail loudly in Claude Code's hook output on every single prompt — noisy and disruptive for something meant to be a passive status indicator. Revisit removing it once the host CLI has auto-reconnect / graceful missing-device handling, and a genuinely broken connection becomes worth surfacing instead of silently swallowing.
