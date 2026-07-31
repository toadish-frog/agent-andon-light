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

## 3. Wire Up Claude Code Hooks

```txt
andon-light install-hooks
```

Prints the exact `hooks` block before touching anything, asks for confirmation, and lets you pick global (`~/.claude/settings.json`) vs. project (`./.claude/settings.json`) scope — see [`../../hooks/README.md`](../../hooks/README.md).
