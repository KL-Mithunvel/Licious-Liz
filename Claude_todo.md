# Claude TODO

## In Progress

## Done
- [x] F1 Live Dashboard — `f1_dashboard.py` (live + historical replay mode)
- [x] Initial project setup — `plot_driver_styling.py` FastF1 example
- [x] Refactor monolith into f1_data.py / f1_gui.py / f1_logger.py / main.py
- [x] Fix ReplayToolbar invisible bug (Speed: label, select-btn style, height)
- [x] Fix replay timing offset (cursor now starts at t0_offset, not 0)
- [x] Fix circuit guard blocking all driver dots when pick_fastest() fails

## Not Started
- [ ] Add lap count display (current lap / total laps) to the session label
- [ ] Add tyre compound indicators to leaderboard (requires OpenF1 stints endpoint)
- [ ] Add fastest lap highlight (purple row) in leaderboard
- [ ] Add DRS zone overlay on track map
- [ ] Persist last-known data so the app shows something useful when API is unreachable
- [ ] Write tests for `_latest_per_driver` and `_fmt_gap` helpers