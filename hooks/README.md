# Claude Code Hook Integration — Agent Andon Light

`settings.snippet.json` maps agent events to `andon-light` CLI calls: `UserPromptSubmit` → working (green), `Notification` → waiting (yellow), `Stop` → idle (red).

This is **not merged into any real settings.json yet** — this is Phase 3 (Claude Code Hook Integration) staged early since it's pure config with no hardware dependency. When you're ready to wire it in:

1. Merge the `hooks` object into either `~/.claude/settings.json` (global, applies everywhere) or a project's `.claude/settings.json` (applies only there).
2. Make sure `andon-light` is installed and on `PATH` (see `../host/README.md`).

## Why every command ends in `|| true`

The device doesn't exist yet. Without `|| true`, every hook invocation would fail (no serial port found) and that failure surfaces in Claude Code's hook output — noisy and pointless before hardware exists. `|| true` makes each hook a silent no-op until you actually plug something in. Once Phase 4 (reliability pass) is done and you trust the device to always be there, you may want to remove it so a genuinely broken connection isn't silently swallowed.
