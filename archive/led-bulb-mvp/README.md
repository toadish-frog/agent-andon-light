# Archived: 3-Discrete-Bulb MVP

**Frozen history, not a maintained deliverable.** The original breadboard MVP hardware/firmware — a custom PCBA with 3 discrete LED bulbs (Red/Yellow/Green) on a 4-pin connector — used to validate the firmware/host-CLI/Claude-Code-hooks pipeline end-to-end before the addressable WS2812 strip (this project's sole ongoing hardware line) existed as a custom PCB.

## Why It's Here Instead of Deleted

The firmware and docs in this folder are real, working, confirmed-on-hardware artifacts — the actual history of how the wire protocol, watchdog, and hook mapping were designed and validated.

## Not Maintained Going Forward

- Not rebuilt or retested against the current `host/`/`hooks/` — those are unchanged and still protocol-compatible in principle (same `G`/`Y`/`R`/`C`/`H` bytes), but this firmware hasn't been re-flashed or re-verified since the pivot.
- Docs reflect the state and understanding at the time this hardware was active — later corrections made to the live docs (e.g. hook naming, driver confirmations) aren't backported here.
