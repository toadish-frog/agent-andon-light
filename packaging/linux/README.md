# Linux Install & Verify

No installer to build — Linux is docs-only by design, published straight to PyPI. Linux users are assumed comfortable with a terminal.

## 1. Install

```txt
sudo apt install -y pipx   # if you don't have pipx yet
pipx install andon-light
```

No repo clone needed.

## 2. Verify

```txt
andon-light doctor
```

Confirms the CLI can find the board. If it reports a permission error, your user needs `dialout` group membership — see [`../../device/docs/TROUBLESHOOTING.md`](../../device/docs/TROUBLESHOOTING.md) Linux-Specific section.

## 3. Wire Up Hooks

```txt
andon-light install-hooks                 # Claude Code (default)
andon-light install-hooks --agent codex   # Codex CLI
```

Prints the exact `hooks` block before touching anything, asks for confirmation, and lets you pick global vs. project scope — see [`../../hooks/claude/README.md`](../../hooks/claude/README.md) (Claude Code) or [`../../hooks/codex/README.md`](../../hooks/codex/README.md) (Codex CLI).
