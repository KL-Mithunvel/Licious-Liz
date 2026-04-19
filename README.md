# F1 Live Dashboard

A native desktop app for watching Formula 1 races — live or historical — with a real-time track map and leaderboard.

Built with PyQt6, FastF1, and the OpenF1 API.

---

## Features

- **Live mode** — polls the OpenF1 API every 2 seconds for driver positions, race gaps, and pit stop counts during an active session
- **Historical replay** — load any race, qualifying, sprint, or practice session from 2023 onwards; replay at 1×, 2×, 5×, 10×, or 30× speed
- **Track map** — animated driver dots with team colours plotted on the circuit outline
- **Leaderboard** — position, driver, team, gap to leader, interval, and pit count updated every frame
- **Next race countdown** — live countdown to the next race weekend shown in the header bar
- **Session logger** — every load, play, pause, and error is appended to `session_log.jsonl`

---

## Screenshots

> Track map (left) and leaderboard (right) during a historical replay.

---

## Requirements

- Python 3.11+
- Windows, macOS, or Linux

All Python dependencies are pinned in `requirements.txt`.

Key packages:

| Package | Purpose |
|---------|---------|
| `PyQt6` | Desktop GUI framework |
| `fastf1` | Historical session data and circuit telemetry |
| `matplotlib` | Track map rendering (embedded in Qt) |
| `requests` | OpenF1 API polling |
| `pandas`, `numpy` | Telemetry data processing |

---

## Installation

```bash
# 1. Clone the repo
git clone <repo-url>
cd <repo-dir>

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Running

```bash
# Always activate the venv first
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux

python main.py
```

---

## Usage

### Watching a historical race

1. Click **▼ Select Race** in the toolbar
2. Choose a **Year**, **Race**, and **Session** (Race, Qualifying, Practice, Sprint)
3. Click **Load Session** — data downloads from FastF1 (cached after first load)
4. Press **▶** to start the replay
5. Use the **Speed** dropdown to change playback speed (1× – 30×)
6. Press **● Go Live** to switch back to live mode at any time

### Live mode

The app checks for an active OpenF1 session on startup. If a session is live it connects automatically. If not, it prompts you to load a historical session instead.

---

## Project Structure

```
main.py              Entry point — creates QApplication and opens the window
f1_data.py           Data layer: OpenF1 API helpers, FastF1 workers, ReplayController
f1_gui.py            GUI layer: all PyQt6 widgets, visual constants, F1Dashboard window
f1_logger.py         Event logger — appends JSON lines to session_log.jsonl
plot_driver_styling.py  Standalone FastF1 example: driver lap-time plots
fastf1_cache/        FastF1 session cache (auto-created, not committed)
session_log.jsonl    Runtime event log (auto-created, not committed)
requirements.txt     Pinned Python dependencies
```

---

## Data Sources

| Source | What it provides |
|--------|-----------------|
| [OpenF1 API](https://openf1.org) | Live driver positions, race gaps, pit stops (free, no key required) |
| [FastF1](https://docs.fastf1.dev) | Historical session telemetry, circuit layouts, event schedules |

FastF1 caches downloaded data in `fastf1_cache/`. The first load of a session can take 30–60 seconds; subsequent loads are instant.

---

## Session Log

Every event is appended to `session_log.jsonl` as a single JSON line:

```jsonl
{"ts": "2026-04-19T14:32:01.123", "event": "session_loaded", "label": "2024 Bahrain Grand Prix — Race"}
{"ts": "2026-04-19T14:32:05.456", "event": "replay_started", "label": "2024 Bahrain Grand Prix — Race", "speed": 1.0}
{"ts": "2026-04-19T14:45:12.789", "event": "replay_paused", "elapsed_s": 742}
{"ts": "2026-04-19T14:45:20.001", "event": "replay_finished", "label": "2024 Bahrain Grand Prix — Race"}
```

---

## Known Limitations

- Replay intervals (gap to leader) are not available from FastF1 — the GAP and INTERVAL columns show `—` during historical replay
- Live mode requires an active F1 session; outside of race weekends it will find no data
- Session data goes back to 2023 (FastF1 / OpenF1 coverage)

---

## License

See [LICENSE](LICENSE).
