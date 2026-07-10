# Claude Code Hook Integration — Agent Andon Light

`settings.snippet.json` maps agent events to `andon-light` CLI calls:

| Hook event | Color | Meaning |
| --- | --- | --- |
| `SessionStart` | idle (red) | Default state — a new session starts "not working yet" |
| `UserPromptSubmit` | working (green) | You just gave it something to do |
| `PreToolUse` | working (green) | Fires on every tool call — keeps the light green through tool-heavy stretches |
| `Notification` | waiting (yellow) | General "needs your attention" |
| `PermissionRequest` | waiting (yellow) | Specifically waiting on a permission decision (e.g. approve a `Bash`/`npm install` call) |
| `PostCompact` | flashing green (compacting) | Internal context compaction — still "alive," distinct from ordinary working |
| `Stop` | idle (red) | Turn/session ended normally |
| `SessionEnd` | idle (red) | Session terminated for any reason, including abrupt ones `Stop` doesn't cover |

Commands run **synchronously** (not `async`) — see "Why not `async`" below.

**Status: merged and live (2026-07-07, fine-tuned same day after real-session testing).** The `hooks` object from `settings.snippet.json` is merged into `~/.claude/settings.json` (global — applies to every Claude Code session on this machine, not just this repo), and `andon-light` is installed globally via `pipx install --editable .` from `../host/`, confirmed on `PATH`. This config is hardware-variant-agnostic — the same hooks and CLI work against either `../led-bulb/firmware/` or `../led-strip/firmware/`, since both speak the identical wire protocol (`G`/`Y`/`R`/`C`/`H`). Requires restarting Claude Code (or starting a new session) to pick up — a session already running when the config changes won't see it.

**Why `PreToolUse` was added:** real-world testing showed the light falling back to the stale/disconnected pulse mid-turn, because `UserPromptSubmit`/`Notification`/`Stop` only fire at 3 discrete moments — nothing was resetting the firmware watchdog during a long stretch of tool calls in between. `PreToolUse` fires on every tool invocation (reads, edits, bash commands, etc.) and also sends `working`, so any tool-heavy turn keeps kicking the watchdog continuously. This does **not** cover a turn that's pure extended thinking with zero tool calls — there's no Claude Code hook event for "still generating text," so that gap is instead covered by a much longer firmware watchdog timeout, the same 30-minute value on both hardware variants (see `../led-bulb/firmware/README.md` or `../led-strip/firmware/README.md`).

**Why `PermissionRequest` was added:** more precise than `Notification` alone for the specific "waiting on a permission approval" moment the user described (e.g. approving a `Bash(npm install)` call) — both map to the same yellow action, so there's no harm in overlap if `Notification` also fires for the same event.

**Why `PostCompact` gets its own color:** without it, a compaction pass would either stay on whatever color was last set (misleading if it was red/idle) or require yet another hook just to flip back afterward. A distinct flashing-green state reads as "still alive, doing upkeep" at a glance, and naturally reverts to solid green (or whatever's next) once the following hook fires — no extra "compaction done" hook needed.

**Why `SessionStart` was added:** without it, a new session inherits whatever color the *previous* session left behind — usually fine (`Stop` already leaves it on idle/red), but not guaranteed if a prior session crashed mid-turn without a clean `Stop`. Explicitly setting idle on `SessionStart` makes the default deterministic regardless of history.

**Why `SessionEnd` was added:** bug report (2026-07-08) — pressing Ctrl+C to kill an active `claude` process outright (not just interrupting a turn) left the light stuck on green forever. Root cause: Claude Code's docs explicitly state `Stop` hooks "don't fire on user interrupts," and `SessionEnd` ("when a session terminates") isn't documented as covering abrupt SIGINT either — so this was unverified until tested against real hardware, per the standing rule of not trusting a timeout/protocol behavior picked by reasoning alone. Added `SessionEnd` → idle (red) with no matcher (covers all termination reasons) and confirmed empirically: Ctrl+C now correctly turns the light red. `Stop` is kept as well since normal turn/session ends should still resolve as fast as possible, without waiting on session teardown.

## Why not `async`

Every command was originally `async: true` to guarantee zero latency on real tool calls. **Removed on 2026-07-07** after a real bug: async gives no ordering guarantee between hook invocations, only that each one is *launched* in order. Each `andon-light set ...` call is a fresh Python process (spawn + import + open/close the serial port), measured at ~40-50ms — cheap, but not zero, and under load (e.g. a busy tool-heavy turn) that's enough jitter for a *later*-launched command to finish *before* an earlier one. Observed symptom: a session correctly ended on red (`Stop`), then some time later flipped to yellow and stuck there — a `Notification`/`PermissionRequest` command fired earlier in the session had been delayed and completed only after `Stop`'s `idle` command had already landed, silently overwriting it. Removing `async` makes Claude Code wait for each hook to finish before continuing, which guarantees hooks apply in true event order. At ~40-50ms per call this is not perceptible against real tool-call durations, so the latency tradeoff that motivated `async` in the first place wasn't actually buying much.

## Why every command ends in `|| true`

Even though the device is now confirmed working, `|| true` is being kept for now: if the board is ever unplugged or on a different machine, every hook invocation would otherwise fail loudly in Claude Code's hook output on every single prompt — noisy and disruptive for something that's meant to be a passive status indicator. Revisit removing it once Phase 4 (reliability pass — auto-reconnect, graceful handling of a missing device) is done and a genuinely broken connection is worth surfacing instead of silently swallowing.
