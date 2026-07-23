#!/usr/bin/env bash
# Dummy end-to-end test: cycles the Andon Light through every state so you
# can film one continuous clip of the full workflow.
set -e

echo "1) idle (red) -- simulates SessionStart / Stop"
andon-light set idle
sleep 3

echo "2) working (green) -- simulates UserPromptSubmit / PreToolUse"
andon-light set working
sleep 3

echo "3) waiting (yellow) -- simulates Notification / PermissionRequest"
andon-light set waiting
sleep 3

echo "4) compacting (flashing green) -- simulates PostCompact"
andon-light set compacting
sleep 3

echo "5) back to working (green)"
andon-light set working
sleep 3

echo "6) heartbeat only (no color change) -- keeps watchdog alive"
andon-light heartbeat
sleep 2

echo "7) back to idle (red) -- simulates Stop"
andon-light set idle

echo "Done."
