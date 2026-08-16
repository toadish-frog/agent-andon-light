# Codex CLI Hook Integration: Agent Andon Light

`hooks.json` maps Codex CLI lifecycle-hook events to `andon-light` CLI calls. Same wire protocol, same firmware, same `andon-light` binary as [`../claude/README.md`](../claude/README.md) (Claude Code) — this is a host-only integration, no firmware update needed. See `device/docs/Implementation-Summary.md` for why the two are decoupled.

## Hook → Color Mapping

| Hook event | Color | Meaning |
| --- | --- | --- |
| `SessionStart` | idle (red) | Default state — a new session starts "not working yet" |
| `UserPromptSubmit` | working (green) | You just gave it something to do |
| `PreToolUse` | working (green) | Fires on every tool call — keeps the light green through tool-heavy stretches |
| `PermissionRequest` | waiting (yellow) | Codex is about to ask for approval (e.g. a shell escalation) |
| `PreCompact` | flashing green (compacting) | Internal context compaction — still "alive," distinct from ordinary working |
| `Stop` | idle (red) | Turn ended normally |
| `SessionEnd` | idle (red) | Session terminated for any reason |

Unlike `hooks/claude/settings.snippet.json`, this file doesn't get merged into a broader settings file — Codex reads a dedicated `hooks.json`, so `andon-light install-hooks --agent codex` writes (or merges into) that file directly. Restart Codex CLI (or start a new session) to pick up a config change.

## Trust the Hooks Before They Run

Codex won't execute a new or changed non-managed `hooks.json` until you explicitly review and trust it — there's no way to pre-trust it from outside the CLI. After running `andon-light install-hooks --agent codex`, start Codex CLI, run `/hooks`, and confirm the new definitions. If the light doesn't react, check this first — an untrusted hook silently doesn't run, it doesn't error.

### The ChatGPT App's Codex Tab (Windows)

On Windows, "Codex app" usually means the ChatGPT desktop app's Codex tab (Microsoft Store) — a GUI chat surface, not the terminal `codex` CLI this doc otherwise assumes. The distinction matters because **`/hooks` (trust, above) only exists in an interactive terminal Codex CLI session** — the ChatGPT app has no equivalent UI, so trust can't be granted from inside it.

Trust is stored on disk and shared across front-ends, though — both read the same `~/.codex` config. So even if you only ever use the ChatGPT app day to day, open a terminal Codex CLI session **once**, run `/hooks`, and grant trust there; the ChatGPT app picks it up from then on. Until that happens, the light just stays silent in the ChatGPT app with no error shown — the same untrusted-hook behavior described above.

If plain `codex` isn't a recognized command in your terminal, the ChatGPT app likely bundles its own private CLI binary instead of adding one to `PATH`. Find and launch it, in PowerShell:

1. Look at the config file directly, so you can see the value yourself instead of trusting a script blindly:

   ```powershell
   Get-Content "$env:USERPROFILE\.codex\config.toml" | Select-String CODEX_CLI_PATH
   ```

   This prints a line like `CODEX_CLI_PATH = "C:\Users\you\AppData\...\codex.exe"`.
2. Run that exact path, quoted, with `&` in front (PowerShell's "run this program" operator):

   ```powershell
   & "C:\Users\you\AppData\...\codex.exe"
   ```

   — paste the path from step 1 in place of the example above.
3. That opens a real terminal Codex CLI session. Run `/hooks` there, review, and trust the new definitions.
4. Close that window. The ChatGPT app's Codex tab will now pick up the trusted hooks — that trust is stored on disk, not tied to the window you approved it in.

Steps 1–2 are the same idea as the one-liner Codex may hand you (reading `CODEX_CLI_PATH` out of `config.toml` and launching it) — just split out so you can see the actual path before running anything, rather than piping it straight into `&` unseen.

## Design Notes

### No `Notification` Equivalent

Claude Code fires a general-purpose `Notification` event for "needs your attention" (mapped to waiting/yellow in `../claude/README.md`). Codex has no equivalent lifecycle-hook event — the closest thing, `notify`, is a separate top-level config option that only fires on `agent-turn-complete`, which the `Stop` hook below already covers. `PermissionRequest` is the only remaining "waiting on you" moment Codex exposes as a hook, so it carries that mapping alone here.

### `PreToolUse` Keeps the Watchdog Fed

Same reasoning as Claude Code: `UserPromptSubmit`/`PermissionRequest`/`Stop` only fire at discrete moments, so `PreToolUse` (fires on every tool invocation) is what keeps the firmware watchdog kicked during long tool-heavy stretches. A turn that's pure extended thinking with zero tool calls is covered by the firmware's own 30-minute watchdog timeout instead — see [`../../device/firmware/README.md`](../../device/firmware/README.md).

### `PreCompact` Gets Its Own Color

Same rationale as Claude Code — flashing green reads as "still alive, doing upkeep" without needing a matching `PostCompact` hook to flip the color back; the next `PreToolUse`/`UserPromptSubmit` naturally overwrites it.

### `SessionStart` / `SessionEnd` Make the Endpoints Deterministic

`SessionStart` resets to idle so a new session never inherits a stale color from a session that ended abnormally. `SessionEnd` fires for any termination reason Codex reports (currently just `other`) and also resets to idle — `Stop` alone wouldn't cover an interrupted or abruptly closed session.

## Why No `async`

Same tradeoff as Claude Code (see [`../claude/README.md`](../claude/README.md) § Why Not `async`): Codex's per-hook `async` flag gives no ordering guarantee between hook invocations, only launch order. Each `andon-light set ...` call is cheap (~40-50ms), so the ordering risk isn't worth the latency `async` would buy back. None of the handlers in `hooks.json` set `async`, so they run synchronously by default.

## Why Every Command Ends in `|| true`

Same reasoning as Claude Code: if the board is unplugged, or `andon-light` runs on a machine without one, `|| true` keeps a hook failure from surfacing as noisy error output on every event — see [`../claude/README.md`](../claude/README.md) § Why Every Command Ends in `|| true`.
