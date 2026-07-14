# Archived: 3-discrete-bulb MVP (Phases 0–4)

This directory is **frozen history, not a maintained deliverable.** It's the original breadboard MVP hardware/firmware — a custom PCBA with 3 discrete LED bulbs (Red/Yellow/Green) on a 4-pin connector — used to validate the firmware/host-CLI/Claude-Code-hooks pipeline end-to-end before the addressable WS2812 strip (this project's sole ongoing hardware line) existed as a custom PCB.

**Why it's here instead of deleted:** the firmware and docs in this folder are real, working, confirmed-on-hardware artifacts (see `docs/Implementation-Summary.md` §4.1/§5 Phases 0–4) — the actual history of how the wire protocol, watchdog, and hook mapping were designed and validated. Restructured 2026-07-14 from a top-level parallel `led-bulb/` directory (as if it were a second product variant) into this archive, once the WS2812 strip's custom PCB — the actual final deliverable — went to manufacturing. See `../../docs/Implementation-Summary.md` §5 "Phase 0–4 history" for the current project's framing of this phase.

**Not maintained going forward:**
- Not rebuilt or retested against current `host/`/`hooks/` — those are unchanged and still protocol-compatible in principle (same `G`/`Y`/`R`/`C`/`H` bytes), but this firmware hasn't been re-flashed or re-verified since the pivot.
- Internal relative links inside this folder's own docs (e.g. `../../hooks/README.md`, `../../led-strip/...`) were written when `led-bulb/` was a repo-root directory and **no longer resolve correctly** from this new location — read them for the historical reasoning, not as working navigation. Current docs/paths live under `../../` (i.e. `led-strip/docs/`, `led-strip/firmware/`) and the repo root (`host/`, `hooks/`).
