#!/usr/bin/env python3
"""
f1_data.py — Data layer: OpenF1 API helpers and FastF1 background workers.

No GUI code here. All visual constants live in f1_gui.py.
"""

import os
import requests
import fastf1
import numpy as np
from bisect import bisect_right
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Optional

from PyQt6.QtCore import QThread, QObject, pyqtSignal, QTimer


# ─── Constants ────────────────────────────────────────────────────────────────

OPENF1_BASE = "https://api.openf1.org/v1"
REFRESH_MS  = 2000
CACHE_DIR   = "fastf1_cache"

SESSION_TYPE_MAP: dict[str, str] = {
    "Race":              "R",
    "Qualifying":        "Q",
    "Sprint":            "S",
    "Sprint Qualifying": "SQ",
    "Practice 1":        "FP1",
    "Practice 2":        "FP2",
    "Practice 3":        "FP3",
}


# ─── Pure utilities ───────────────────────────────────────────────────────────

def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _get(endpoint: str, params: dict | None = None) -> list:
    try:
        r = requests.get(f"{OPENF1_BASE}/{endpoint}", params=params, timeout=6)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


def _latest_per_driver(records: list) -> dict:
    result: dict = {}
    for rec in records:
        dn = rec.get("driver_number")
        if dn is None:
            continue
        if dn not in result or rec.get("date", "") > result[dn].get("date", ""):
            result[dn] = rec
    return result


def fmt_gap(val) -> str:
    if val is None:
        return "—"
    if isinstance(val, (int, float)):
        return f"+{val:.3f}"
    return str(val)


def active_session() -> Optional[dict]:
    rows = _get("sessions", {"year": datetime.now().year})
    if not rows:
        return None
    rows.sort(key=lambda s: s.get("date_start", ""), reverse=True)
    return rows[0]


def next_race() -> Optional[dict]:
    try:
        schedule = fastf1.get_event_schedule(datetime.now().year, include_testing=False)
        now = datetime.now(tz=timezone.utc)
        for _, ev in schedule.iterrows():
            race_dt = ev["Session5Date"]
            if race_dt.tzinfo is None:
                race_dt = race_dt.replace(tzinfo=timezone.utc)
            if race_dt > now:
                return {
                    "name":    ev["EventName"],
                    "circuit": ev["Location"],
                    "round":   int(ev["RoundNumber"]),
                    "date":    race_dt,
                }
    except Exception:
        pass
    return None


# ─── Live data polling ────────────────────────────────────────────────────────

class DataFetcher(QThread):
    data_ready = pyqtSignal(dict)
    status     = pyqtSignal(str)

    def __init__(self, session_key: int):
        super().__init__()
        self._sk     = session_key
        self._active = True

    def stop(self):
        self._active = False

    def run(self):
        while self._active:
            try:
                sk     = self._sk
                cutoff = (
                    datetime.now(tz=timezone.utc) - timedelta(seconds=5)
                ).strftime("%Y-%m-%dT%H:%M:%S")

                raw_loc   = _get("location",  {"session_key": sk, "date>": cutoff})
                positions = _latest_per_driver(_get("position",  {"session_key": sk}))
                intervals = _latest_per_driver(_get("intervals", {"session_key": sk}))
                pits      = _get("pit",        {"session_key": sk})
                drivers   = _get("drivers",    {"session_key": sk})
                locations = _latest_per_driver(raw_loc)

                pit_counts: dict = defaultdict(int)
                for p in pits:
                    pit_counts[p["driver_number"]] += 1

                self.data_ready.emit({
                    "drivers":    {d["driver_number"]: d for d in drivers},
                    "positions":  positions,
                    "intervals":  intervals,
                    "pit_counts": dict(pit_counts),
                    "locations":  locations,
                })
                self.status.emit(f"Live  ·  {datetime.now().strftime('%H:%M:%S')}")
            except Exception as exc:
                self.status.emit(f"Fetch error: {exc}")
            self.msleep(REFRESH_MS)


# ─── Circuit outline loader ───────────────────────────────────────────────────

class CircuitLoader(QThread):
    ready  = pyqtSignal(object, object)
    failed = pyqtSignal(str)

    def __init__(self, year: int, circuit: str, session_key: int):
        super().__init__()
        self.year        = year
        self.circuit     = circuit
        self.session_key = session_key

    def run(self):
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            fastf1.Cache.enable_cache(CACHE_DIR)
            sess = fastf1.get_session(self.year, self.circuit, "Q")
            sess.load(laps=True, telemetry=True, weather=False, messages=False)
            lap  = sess.laps.pick_fastest()
            tel  = lap.get_telemetry()
            self.ready.emit(tel["X"].values.astype(float), tel["Y"].values.astype(float))
            return
        except Exception:
            pass
        try:
            data = _get("location", {"session_key": self.session_key, "driver_number": 1})
            if not data:
                all_loc = _get("location", {"session_key": self.session_key})
                if all_loc:
                    dn0  = all_loc[0]["driver_number"]
                    data = [d for d in all_loc if d["driver_number"] == dn0]
            if data:
                xs = np.array([d["x"] for d in data if d.get("x") is not None], dtype=float)
                ys = np.array([d["y"] for d in data if d.get("y") is not None], dtype=float)
                self.ready.emit(xs, ys)
                return
        except Exception:
            pass
        self.failed.emit("Circuit data unavailable.")


# ─── Schedule workers ─────────────────────────────────────────────────────────

class ScheduleWorker(QThread):
    done = pyqtSignal(object)

    def run(self):
        self.done.emit(next_race())


class ScheduleFetchWorker(QThread):
    done = pyqtSignal(list)

    def __init__(self, year: int):
        super().__init__()
        self.year = year

    def run(self):
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            fastf1.Cache.enable_cache(CACHE_DIR)
            schedule = fastf1.get_event_schedule(self.year, include_testing=False)
            events = [
                {
                    "name":    ev["EventName"],
                    "country": ev["Country"],
                    "round":   int(ev["RoundNumber"]),
                }
                for _, ev in schedule.iterrows()
            ]
            self.done.emit(events)
        except Exception:
            self.done.emit([])


# ─── Historical session loader ────────────────────────────────────────────────

class HistoricalLoader(QThread):
    """
    Loads a FastF1 session and emits a replay-ready data dict.

    Timing: all timestamps (loc_times, pos_times, pit_times) are seconds from
    sess.t0_date.  t0_offset is the session-relative second of the first
    telemetry sample.  The ReplayController cursor starts at t0_offset so
    driver dots appear as soon as playback begins.
    """
    loaded   = pyqtSignal(dict)
    progress = pyqtSignal(str)
    failed   = pyqtSignal(str)

    def __init__(self, year: int, event_name: str, session_type: str):
        super().__init__()
        self.year         = year
        self.event_name   = event_name
        self.session_type = session_type

    def run(self):
        try:
            ff1_type = SESSION_TYPE_MAP.get(self.session_type, "R")
            self.progress.emit(
                f"Downloading {self.year} {self.event_name} — {self.session_type}…"
                "  (first load may take a minute)"
            )
            os.makedirs(CACHE_DIR, exist_ok=True)
            fastf1.Cache.enable_cache(CACHE_DIR)
            sess = fastf1.get_session(self.year, self.event_name, ff1_type)
            sess.load(laps=True, telemetry=True, weather=False, messages=False)

            t0 = _ensure_utc(sess.t0_date)

            # ── Driver info ───────────────────────────────────────────────────
            self.progress.emit("Processing driver info…")
            drivers: dict = {}
            for abbr in sess.drivers:
                try:
                    info = sess.get_driver(abbr)
                    dn   = int(info["DriverNumber"])
                    drivers[dn] = {
                        "driver_number": dn,
                        "name_acronym":  info.get("Abbreviation", abbr),
                        "team_name":     info.get("TeamName", ""),
                    }
                except Exception:
                    pass

            # ── Location stream (X/Y per driver) ─────────────────────────────
            self.progress.emit("Processing telemetry…")
            loc_times: dict[int, list] = defaultdict(list)
            loc_recs:  dict[int, list] = defaultdict(list)
            all_dts:   list            = []

            for abbr in sess.drivers:
                try:
                    laps = sess.laps.pick_drivers(abbr)
                    if laps.empty:
                        continue
                    info = sess.get_driver(abbr)
                    dn   = int(info["DriverNumber"])
                    tel  = laps.get_telemetry()[["X", "Y", "Date"]].dropna()
                    for _, row in tel.iterrows():
                        dt  = _ensure_utc(row["Date"].to_pydatetime())
                        sec = (dt - t0).total_seconds()
                        loc_times[dn].append(sec)
                        loc_recs[dn].append({"x": float(row["X"]), "y": float(row["Y"])})
                        all_dts.append(dt)
                except Exception:
                    pass

            if not all_dts:
                self.failed.emit("No telemetry data found for this session.")
                return

            start_dt  = min(all_dts)
            end_dt    = max(all_dts)
            # Offset so the cursor starts exactly where the first sample lives
            t0_offset = (start_dt - t0).total_seconds()

            # ── Race positions (lap-by-lap) ───────────────────────────────────
            self.progress.emit("Processing positions…")
            pos_times: dict[int, list] = defaultdict(list)
            pos_recs:  dict[int, list] = defaultdict(list)

            valid_laps = sess.laps.dropna(subset=["Position", "LapStartTime"])
            for _, lap in valid_laps.iterrows():
                try:
                    dn  = int(lap["DriverNumber"])
                    dt  = _ensure_utc((t0 + lap["LapStartTime"]).to_pydatetime())
                    sec = (dt - t0).total_seconds()
                    pos_times[dn].append(sec)
                    pos_recs[dn].append({"position": int(lap["Position"])})
                except Exception:
                    pass

            # ── Pit stop times ────────────────────────────────────────────────
            pit_times: dict[int, list] = defaultdict(list)
            pit_laps = sess.laps.dropna(subset=["PitInTime", "LapStartTime"])
            for _, lap in pit_laps.iterrows():
                try:
                    dn  = int(lap["DriverNumber"])
                    dt  = _ensure_utc((t0 + lap["LapStartTime"]).to_pydatetime())
                    sec = (dt - t0).total_seconds()
                    pit_times[dn].append(sec)
                except Exception:
                    pass

            # ── Circuit outline ───────────────────────────────────────────────
            # Preferred: fastest lap telemetry. Fallback: first driver's loc data.
            circuit_x = circuit_y = None
            try:
                fastest   = sess.laps.pick_fastest()
                ctel      = fastest.get_telemetry()[["X", "Y"]].dropna()
                circuit_x = ctel["X"].values.astype(float)
                circuit_y = ctel["Y"].values.astype(float)
            except Exception:
                for recs in loc_recs.values():
                    if recs:
                        circuit_x = np.array([r["x"] for r in recs])
                        circuit_y = np.array([r["y"] for r in recs])
                        break

            self.loaded.emit({
                "drivers":   drivers,
                "loc_times": dict(loc_times),
                "loc_recs":  dict(loc_recs),
                "pos_times": dict(pos_times),
                "pos_recs":  dict(pos_recs),
                "pit_times": dict(pit_times),
                "circuit_x": circuit_x,
                "circuit_y": circuit_y,
                "start_dt":  start_dt,
                "end_dt":    end_dt,
                "t0_offset": t0_offset,
                "duration":  (end_dt - t0).total_seconds(),
                "label":     f"{self.year} {self.event_name} — {self.session_type}",
            })

        except Exception as exc:
            self.failed.emit(str(exc))


# ─── Replay controller ────────────────────────────────────────────────────────

class ReplayController(QObject):
    frame_ready  = pyqtSignal(dict)
    time_updated = pyqtSignal(int)   # elapsed seconds from first telemetry sample
    finished     = pyqtSignal()

    TICK_MS = 100

    def __init__(self, data: dict):
        super().__init__()
        self._data      = data
        self._speed     = 1.0
        self._t0_offset = data.get("t0_offset", 0.0)
        self._cursor    = self._t0_offset   # start exactly at first telemetry sample
        self._end       = data["duration"]

        self._timer = QTimer()
        self._timer.setInterval(self.TICK_MS)
        self._timer.timeout.connect(self._tick)

    # ── Public interface ──────────────────────────────────────────────────────

    @property
    def speed(self) -> float:
        return self._speed

    @property
    def elapsed(self) -> int:
        return int(self._cursor - self._t0_offset)

    def set_speed(self, speed: float):
        self._speed = speed

    def play(self):
        self._timer.start()

    def pause(self):
        self._timer.stop()

    def stop(self):
        self._timer.stop()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _tick(self):
        self._cursor = min(self._cursor + self.TICK_MS / 1000.0 * self._speed, self._end)
        self.time_updated.emit(self.elapsed)
        self.frame_ready.emit(self._build_frame())
        if self._cursor >= self._end:
            self._timer.stop()
            self.finished.emit()

    def _build_frame(self) -> dict:
        t = self._cursor
        d = self._data

        locations: dict = {}
        for dn in d["loc_times"]:
            rec = self._at(d["loc_times"][dn], d["loc_recs"][dn], t)
            if rec:
                locations[dn] = rec

        positions: dict = {}
        for dn in d["pos_times"]:
            rec = self._at(d["pos_times"][dn], d["pos_recs"][dn], t)
            if rec:
                positions[dn] = rec

        pit_counts: dict = defaultdict(int)
        for dn, times in d["pit_times"].items():
            pit_counts[dn] = bisect_right(times, t)

        return {
            "drivers":    d["drivers"],
            "positions":  positions,
            "intervals":  {},
            "pit_counts": dict(pit_counts),
            "locations":  locations,
        }

    @staticmethod
    def _at(times: list, recs: list, t: float) -> Optional[dict]:
        """Binary search: latest record at or before t."""
        idx = bisect_right(times, t) - 1
        return recs[idx] if idx >= 0 else None
