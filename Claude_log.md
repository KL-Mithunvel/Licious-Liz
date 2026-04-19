# Claude Log

## 2026-04-19 — Refactor + replay bug fixes

- Split `f1_dashboard.py` into four files: `f1_data.py` (API + workers), `f1_gui.py` (all widgets), `f1_logger.py` (JSONL event log), `main.py` (entry point). Old file deleted.
- Fixed timing offset bug: replay cursor was starting at 0 but telemetry timestamps started at `t0_offset` (~300 s into session); cursor now initialises to `t0_offset` and duration runs to `(end_dt - t0)`.
- Fixed circuit guard bug: `_loaded` was never set when `pick_fastest()` raised, so `update_drivers()` returned immediately and no dots appeared. Now falls back to first driver's loc_recs to draw the outline.
- Fixed `ReplayToolbar` invisible Speed label: `setParent()` returns None so the old one-liner always created a second unparented label. Now created explicitly with styling.
- Increased toolbar height 36 → 46 px; Select Race button now has red 2 px border to be visible.
- Added `ReplayController.speed` and `.elapsed` properties so `F1Dashboard` can log without touching private attributes.

## 2026-03-27 — Created F1 Live Dashboard (PyQt6 + OpenF1)

- Created `f1_dashboard.py`: full PyQt6 GUI application for live F1 race tracking.
- Architecture: `DataFetcher` (QThread, polls OpenF1 every 2 s) + `CircuitLoader` (QThread, loads track outline once via FastF1 with OpenF1 fallback) + `ScheduleWorker` (QThread, fetches next-race date from FastF1 schedule).
- UI layout: `CountdownBar` (top) → red divider → `QSplitter` [ `TrackMap` (matplotlib, left) | `Leaderboard` (QTableWidget, right) ] → `QStatusBar`.
- Data sources: OpenF1 API for positions/intervals/pits/locations; FastF1 for circuit telemetry (X/Y) and event schedule.
- Location endpoint filtered to last 5 seconds per poll to avoid downloading entire session history.
- Circuit layout falls back to OpenF1 location trace if FastF1 fails (e.g. circuit name mismatch or no cache).
- Created `Claude_todo.md` and `Claude_log.md` as required by project rules.
- PyQt6 not yet in requirements.txt — user must run: pip install PyQt6 && pip freeze > requirements.txt