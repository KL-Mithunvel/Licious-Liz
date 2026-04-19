#!/usr/bin/env python3
"""
f1_gui.py — All PyQt6 widgets and the F1Dashboard main window.

Visual constants (colours, stylesheets, team colours) live here.
Data workers are imported from f1_data; events are logged via f1_logger.
"""

import numpy as np
from datetime import datetime, timezone
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QStatusBar, QSplitter, QDialog, QDialogButtonBox, QComboBox, QPushButton,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QBrush

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from f1_data import (
    SESSION_TYPE_MAP, fmt_gap,
    DataFetcher, CircuitLoader, ScheduleWorker, ScheduleFetchWorker,
    HistoricalLoader, ReplayController,
    active_session, next_race,
)
import f1_logger


# ─── Visual constants ─────────────────────────────────────────────────────────

TEAM_COLORS: dict[str, str] = {
    "Red Bull Racing": "#3671C6",
    "Ferrari":         "#E8002D",
    "Mercedes":        "#27F4D2",
    "McLaren":         "#FF8000",
    "Aston Martin":    "#229971",
    "Alpine":          "#FF87BC",
    "Williams":        "#64C4FF",
    "Haas F1 Team":    "#B6BABD",
    "Kick Sauber":     "#52E252",
    "Racing Bulls":    "#6692FF",
}
DEFAULT_COLOR = "#AAAAAA"

C_BG     = "#0f0f1a"
C_PANEL  = "#1a1a2e"
C_HEADER = "#16213e"
C_ACCENT = "#e10600"
C_DIM    = "#888888"
C_TEXT   = "#dddddd"
MONO     = "Consolas, Courier New, monospace"

_COMBO_SS = f"""
    QComboBox {{
        background: {C_BG}; color: {C_TEXT};
        border: 1px solid #333; padding: 3px 8px;
        font-family: {MONO}; font-size: 12px;
    }}
    QComboBox::drop-down {{ border: none; width: 18px; }}
    QComboBox QAbstractItemView {{
        background: {C_BG}; color: {C_TEXT};
        selection-background-color: {C_HEADER};
    }}
"""
_BTN_SS = f"""
    QPushButton {{
        background: {C_HEADER}; color: {C_TEXT};
        border: 1px solid #333; padding: 4px 12px;
        font-family: {MONO}; font-size: 12px;
    }}
    QPushButton:hover  {{ border-color: {C_ACCENT}; }}
    QPushButton:pressed {{ background: {C_ACCENT}; color: white; }}
    QPushButton:disabled {{ color: #444; }}
"""
_BTN_RED_SS = f"""
    QPushButton {{
        background: {C_ACCENT}; color: white; border: none;
        padding: 4px 12px; font-family: {MONO}; font-size: 12px; font-weight: bold;
    }}
    QPushButton:hover {{ background: #ff2200; }}
"""
_BTN_SELECT_SS = f"""
    QPushButton {{
        background: {C_HEADER}; color: white;
        border: 2px solid {C_ACCENT}; padding: 4px 14px;
        font-family: {MONO}; font-size: 12px; font-weight: bold;
    }}
    QPushButton:hover  {{ background: {C_ACCENT}; }}
    QPushButton:pressed {{ background: #ff2200; }}
"""


# ─── Track Map ────────────────────────────────────────────────────────────────

class TrackMap(FigureCanvas):
    def __init__(self):
        self.fig = Figure(facecolor=C_BG)
        super().__init__(self.fig)
        self.ax = self.fig.add_subplot(111, facecolor=C_BG)
        self.fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
        self.ax.axis("off")

        self._y_range: float       = 1.0
        self._loaded:  bool        = False
        self._driver_artists: list = []

        self.ax.text(0.5, 0.5, "Loading circuit…",
                     transform=self.ax.transAxes,
                     ha="center", va="center", color=C_DIM, fontsize=14)
        self.draw()

    def load_circuit(self, x: np.ndarray, y: np.ndarray):
        self.ax.clear()
        self.ax.set_facecolor(C_BG)
        self.ax.axis("off")
        self.ax.set_aspect("equal")
        self._y_range = float(y.max() - y.min()) if len(y) else 1.0
        self._loaded  = True
        for lw, col in [(10, "#1e1e1e"), (6, "#3a3a3a"), (2, "#666666")]:
            self.ax.plot(x, y, color=col, linewidth=lw,
                         solid_capstyle="round", solid_joinstyle="round")
        self.draw()

    def update_drivers(self, locations: dict, drivers: dict):
        for art in self._driver_artists:
            try:
                art.remove()
            except Exception:
                pass
        self._driver_artists.clear()
        if not self._loaded:
            return

        dy = self._y_range * 0.022
        for dn, loc in locations.items():
            px, py = loc.get("x"), loc.get("y")
            if px is None or py is None:
                continue
            driver = drivers.get(dn, {})
            color  = TEAM_COLORS.get(driver.get("team_name", ""), DEFAULT_COLOR)
            abbr   = driver.get("name_acronym", str(dn))
            dot = self.ax.scatter(px, py, c=color, s=200, zorder=6,
                                  edgecolors="white", linewidths=0.8)
            lbl = self.ax.text(px, py + dy, abbr,
                               color="white", fontsize=6.5, fontweight="bold",
                               ha="center", va="bottom", zorder=7)
            self._driver_artists += [dot, lbl]
        self.draw_idle()


# ─── Leaderboard ─────────────────────────────────────────────────────────────

_COLS = ["POS", "DRIVER", "TEAM", "GAP", "INTERVAL", "PITS"]


class Leaderboard(QTableWidget):
    def __init__(self):
        super().__init__(0, len(_COLS))
        self.setHorizontalHeaderLabels(_COLS)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.setShowGrid(False)
        self.setStyleSheet(f"""
            QTableWidget {{
                background: {C_PANEL}; color: {C_TEXT};
                border: none; font-size: 13px; font-family: {MONO};
            }}
            QHeaderView::section {{
                background: {C_HEADER}; color: {C_DIM};
                border: none; border-bottom: 2px solid {C_ACCENT};
                padding: 5px 8px; font-size: 11px;
                font-weight: bold; letter-spacing: 1px;
            }}
            QTableWidget::item {{
                padding: 5px 8px; border-bottom: 1px solid #1e1e30;
            }}
        """)

    def refresh(self, data: dict):
        positions  = data["positions"]
        intervals  = data["intervals"]
        pit_counts = data["pit_counts"]
        drivers    = data["drivers"]

        sorted_rows = sorted(positions.items(),
                             key=lambda kv: kv[1].get("position", 99))
        self.setRowCount(len(sorted_rows))

        for row, (dn, pos_data) in enumerate(sorted_rows):
            driver   = drivers.get(dn, {})
            pos      = pos_data.get("position", "—")
            abbr     = driver.get("name_acronym", str(dn))
            team     = driver.get("team_name", "")
            color    = TEAM_COLORS.get(team, DEFAULT_COLOR)
            iv       = intervals.get(dn, {})
            gap_str  = "LEADER" if pos == 1 else fmt_gap(iv.get("gap_to_leader"))
            intv_str = "—"      if pos == 1 else fmt_gap(iv.get("interval"))
            cells    = [str(pos), abbr, team[:14], gap_str, intv_str,
                        str(pit_counts.get(dn, 0))]

            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 0:
                    item.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
                    item.setForeground(QBrush(QColor("#ffffff")))
                elif col == 1:
                    item.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
                    item.setForeground(QBrush(QColor(color)))
                else:
                    item.setForeground(QBrush(QColor(C_TEXT)))
                if pos == 1:
                    item.setBackground(QBrush(QColor("#1e1e38")))
                self.setItem(row, col, item)


# ─── Countdown Bar ────────────────────────────────────────────────────────────

class CountdownBar(QWidget):
    def __init__(self):
        super().__init__()
        self._race: Optional[dict] = None
        self.setFixedHeight(46)
        self.setStyleSheet(f"background: {C_HEADER};")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)

        self._title = QLabel("F1 LIVE DASHBOARD")
        self._title.setStyleSheet(
            f"color: {C_ACCENT}; font-size: 18px; font-weight: bold; font-family: {MONO};"
        )
        self._race_lbl = QLabel("Fetching schedule…")
        self._race_lbl.setStyleSheet(
            f"color: {C_TEXT}; font-size: 12px; font-family: {MONO};"
        )
        self._countdown = QLabel("")
        self._countdown.setStyleSheet(
            f"color: {C_ACCENT}; font-size: 13px; font-weight: bold; font-family: {MONO};"
        )
        layout.addWidget(self._title)
        layout.addStretch()
        layout.addWidget(self._race_lbl)
        layout.addSpacing(24)
        layout.addWidget(self._countdown)

        tick = QTimer(self)
        tick.timeout.connect(self._tick)
        tick.start(1000)

    def set_race(self, race: Optional[dict]):
        self._race = race
        if race:
            self._race_lbl.setText(
                f"NEXT:  Round {race['round']} — {race['name']}  |  {race['circuit']}"
            )
        else:
            self._race_lbl.setText("Schedule unavailable")

    def _tick(self):
        if not self._race:
            return
        delta = self._race["date"] - datetime.now(tz=timezone.utc)
        secs  = int(delta.total_seconds())
        if secs <= 0:
            self._countdown.setText("RACE UNDERWAY")
            return
        d = secs // 86400
        h = (secs % 86400) // 3600
        m = (secs % 3600) // 60
        s = secs % 60
        self._countdown.setText(
            f"  {d}d  {h:02d}h  {m:02d}m  {s:02d}s" if d
            else f"  {h:02d}h  {m:02d}m  {s:02d}s"
        )


# ─── Session Picker Dialog ────────────────────────────────────────────────────

class SessionPickerDialog(QDialog):
    session_chosen = pyqtSignal(int, str, str)   # year, event_name, session_type

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Session")
        self.setModal(True)
        self.setFixedSize(460, 210)
        self.setStyleSheet(f"background: {C_PANEL}; color: {C_TEXT};")

        self._fetch_worker: Optional[ScheduleFetchWorker] = None
        self._build_ui()
        self._fetch_year(datetime.now().year)

    def _build_ui(self):
        lbl_style = (
            f"color: {C_TEXT}; font-family: {MONO}; font-size: 12px; min-width: 70px;"
        )
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(20, 16, 20, 16)

        row1 = QHBoxLayout()
        lbl1 = QLabel("Year")
        lbl1.setStyleSheet(lbl_style)
        self._year_cb = QComboBox()
        self._year_cb.addItems([str(y) for y in range(datetime.now().year, 2022, -1)])
        self._year_cb.setStyleSheet(_COMBO_SS)
        self._year_cb.currentTextChanged.connect(lambda y: self._fetch_year(int(y)))
        row1.addWidget(lbl1)
        row1.addWidget(self._year_cb, 1)
        root.addLayout(row1)

        row2 = QHBoxLayout()
        lbl2 = QLabel("Race")
        lbl2.setStyleSheet(lbl_style)
        self._race_cb = QComboBox()
        self._race_cb.setStyleSheet(_COMBO_SS)
        self._race_cb.addItem("Loading…")
        row2.addWidget(lbl2)
        row2.addWidget(self._race_cb, 1)
        root.addLayout(row2)

        row3 = QHBoxLayout()
        lbl3 = QLabel("Session")
        lbl3.setStyleSheet(lbl_style)
        self._sess_cb = QComboBox()
        self._sess_cb.addItems(list(SESSION_TYPE_MAP.keys()))
        self._sess_cb.setStyleSheet(_COMBO_SS)
        row3.addWidget(lbl3)
        row3.addWidget(self._sess_cb, 1)
        root.addLayout(row3)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("Load Session")
        btns.button(QDialogButtonBox.StandardButton.Ok).setStyleSheet(_BTN_RED_SS)
        btns.button(QDialogButtonBox.StandardButton.Cancel).setStyleSheet(_BTN_SS)
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _fetch_year(self, year: int):
        self._race_cb.clear()
        self._race_cb.addItem("Loading…")
        self._fetch_worker = ScheduleFetchWorker(year)
        self._fetch_worker.done.connect(self._on_schedule)
        self._fetch_worker.start()

    def _on_schedule(self, events: list):
        self._race_cb.clear()
        if not events:
            self._race_cb.addItem("No events found")
            return
        for ev in events:
            self._race_cb.addItem(f"Round {ev['round']:02d}  —  {ev['name']}", ev["name"])

    def _on_ok(self):
        year       = int(self._year_cb.currentText())
        event_name = self._race_cb.currentData()
        sess_type  = self._sess_cb.currentText()
        if not event_name:
            return
        self.session_chosen.emit(year, event_name, sess_type)
        self.accept()


# ─── Replay Toolbar ───────────────────────────────────────────────────────────

class ReplayToolbar(QWidget):
    select_clicked = pyqtSignal()
    live_clicked   = pyqtSignal()
    play_pause     = pyqtSignal(bool)    # True = play
    speed_changed  = pyqtSignal(float)

    _SPEEDS = [("1×", 1.0), ("2×", 2.0), ("5×", 5.0), ("10×", 10.0), ("30×", 30.0)]

    def __init__(self):
        super().__init__()
        self.setFixedHeight(46)
        self.setStyleSheet(f"background: {C_HEADER};")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(8)

        self._select_btn = QPushButton("▼  Select Race")
        self._select_btn.setStyleSheet(_BTN_SELECT_SS)
        self._select_btn.clicked.connect(self.select_clicked)

        self._live_btn = QPushButton("● Go Live")
        self._live_btn.setStyleSheet(_BTN_SS)
        self._live_btn.setEnabled(False)
        self._live_btn.clicked.connect(self.live_clicked)

        self._mode_lbl = QLabel("● LIVE")
        self._mode_lbl.setStyleSheet(
            f"color: {C_ACCENT}; font-weight: bold; font-family: {MONO}; font-size: 12px;"
        )

        self._play_btn = QPushButton("▶")
        self._play_btn.setStyleSheet(_BTN_SS)
        self._play_btn.setEnabled(False)
        self._play_btn.setFixedWidth(36)
        self._play_btn.clicked.connect(self._toggle_play)

        self._speed_cb = QComboBox()
        for label, _ in self._SPEEDS:
            self._speed_cb.addItem(label)
        self._speed_cb.setStyleSheet(_COMBO_SS)
        self._speed_cb.setEnabled(False)
        self._speed_cb.setFixedWidth(64)
        self._speed_cb.currentIndexChanged.connect(
            lambda i: self.speed_changed.emit(self._SPEEDS[i][1])
        )

        self._time_lbl = QLabel("T+00:00:00")
        self._time_lbl.setStyleSheet(
            f"color: {C_DIM}; font-family: {MONO}; font-size: 12px;"
        )

        _spd_lbl = QLabel("Speed:")
        _spd_lbl.setStyleSheet(f"color: {C_DIM}; font-family: {MONO}; font-size: 12px;")

        layout.addWidget(self._select_btn)
        layout.addWidget(self._live_btn)
        layout.addWidget(self._mode_lbl)
        layout.addStretch()
        layout.addWidget(self._play_btn)
        layout.addWidget(_spd_lbl)
        layout.addWidget(self._speed_cb)
        layout.addWidget(self._time_lbl)

        self._playing = False

    def set_live_mode(self):
        self._mode_lbl.setText("● LIVE")
        self._mode_lbl.setStyleSheet(
            f"color: {C_ACCENT}; font-weight: bold; font-family: {MONO}; font-size: 12px;"
        )
        self._play_btn.setEnabled(False)
        self._speed_cb.setEnabled(False)
        self._live_btn.setEnabled(False)
        self._time_lbl.setText("T+00:00:00")
        self._playing = False
        self._play_btn.setText("▶")

    def set_replay_mode(self, label: str):
        self._mode_lbl.setText(f"REPLAY  {label}")
        self._mode_lbl.setStyleSheet(
            f"color: #ffaa00; font-weight: bold; font-family: {MONO}; font-size: 12px;"
        )
        self._play_btn.setEnabled(True)
        self._speed_cb.setEnabled(True)
        self._live_btn.setEnabled(True)
        self._playing = False
        self._play_btn.setText("▶")

    def set_elapsed(self, secs: int):
        h = secs // 3600
        m = (secs % 3600) // 60
        s = secs % 60
        self._time_lbl.setText(f"T+{h:02d}:{m:02d}:{s:02d}")

    def _toggle_play(self):
        self._playing = not self._playing
        self._play_btn.setText("⏸" if self._playing else "▶")
        self.play_pause.emit(self._playing)


# ─── Main Window ──────────────────────────────────────────────────────────────

class F1Dashboard(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("F1 Live Dashboard")
        self.resize(1440, 860)

        self._fetcher:       Optional[DataFetcher]      = None
        self._loader:        Optional[CircuitLoader]    = None
        self._sched_worker:  Optional[ScheduleWorker]   = None
        self._hist_loader:   Optional[HistoricalLoader] = None
        self._replay_ctrl:   Optional[ReplayController] = None
        self._current_label: str                        = ""

        self._build_ui()
        QTimer.singleShot(50, self._init_data)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        self.setStyleSheet(f"QMainWindow, QWidget {{ background: {C_BG}; }}")

        root_w = QWidget()
        self.setCentralWidget(root_w)
        root = QVBoxLayout(root_w)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.countdown_bar = CountdownBar()
        root.addWidget(self.countdown_bar)

        div = QFrame()
        div.setFixedHeight(2)
        div.setStyleSheet(f"background: {C_ACCENT};")
        root.addWidget(div)

        self.replay_toolbar = ReplayToolbar()
        self.replay_toolbar.select_clicked.connect(self._open_session_picker)
        self.replay_toolbar.live_clicked.connect(self._go_live)
        self.replay_toolbar.play_pause.connect(self._on_play_pause)
        self.replay_toolbar.speed_changed.connect(self._on_speed_changed)
        root.addWidget(self.replay_toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("QSplitter::handle { background: #333; }")

        self.track_map = TrackMap()
        splitter.addWidget(self.track_map)

        right_panel = QWidget()
        right_panel.setStyleSheet(f"background: {C_PANEL};")
        right_v = QVBoxLayout(right_panel)
        right_v.setContentsMargins(0, 0, 0, 0)
        right_v.setSpacing(0)

        self._session_label = QLabel("  Connecting…")
        self._session_label.setFixedHeight(28)
        self._session_label.setStyleSheet(
            f"color: {C_DIM}; background: {C_HEADER}; padding-left: 10px;"
            f" font-family: {MONO}; font-size: 11px;"
        )
        right_v.addWidget(self._session_label)
        self.leaderboard = Leaderboard()
        right_v.addWidget(self.leaderboard)

        splitter.addWidget(right_panel)
        splitter.setSizes([960, 480])
        root.addWidget(splitter)

        self._status = QStatusBar()
        self._status.setStyleSheet(
            f"background: {C_HEADER}; color: {C_DIM}; font-family: {MONO}; font-size: 11px;"
        )
        self.setStatusBar(self._status)
        self._status.showMessage("Initialising…")

    # ── Live mode ─────────────────────────────────────────────────────────────

    def _init_data(self):
        self._sched_worker = ScheduleWorker()
        self._sched_worker.done.connect(self.countdown_bar.set_race)
        self._sched_worker.start()

        sess = active_session()
        if not sess:
            self._status.showMessage(
                "No active session — click ▼ Select Race to load a historical session."
            )
            return

        sk      = sess["session_key"]
        circuit = sess.get("circuit_short_name", "Unknown")
        year    = sess.get("year", datetime.now().year)
        sname   = sess.get("session_name", "Session")

        self._session_label.setText(f"  {circuit}  —  {sname}  (session key: {sk})")
        self._status.showMessage(f"Session {sk} found. Loading circuit…")
        f1_logger.log_live_connected(sk)

        self._loader = CircuitLoader(year, circuit, sk)
        self._loader.ready.connect(self.track_map.load_circuit)
        self._loader.failed.connect(lambda m: self._status.showMessage(f"Circuit: {m}"))
        self._loader.start()

        self._fetcher = DataFetcher(sk)
        self._fetcher.data_ready.connect(self._on_data)
        self._fetcher.status.connect(self._status.showMessage)
        self._fetcher.start()

    # ── Session picker → historical load ─────────────────────────────────────

    def _open_session_picker(self):
        dlg = SessionPickerDialog(self)
        dlg.session_chosen.connect(self._load_historical)
        dlg.exec()

    def _load_historical(self, year: int, event_name: str, session_type: str):
        self._stop_live()
        if self._replay_ctrl:
            self._replay_ctrl.stop()
            self._replay_ctrl = None

        self._session_label.setText(
            f"  Loading: {year} {event_name} — {session_type}…"
        )
        self.replay_toolbar.set_live_mode()

        self._hist_loader = HistoricalLoader(year, event_name, session_type)
        self._hist_loader.progress.connect(self._status.showMessage)
        self._hist_loader.loaded.connect(self._start_replay)
        self._hist_loader.failed.connect(self._on_load_failed)
        self._hist_loader.start()

    def _start_replay(self, data: dict):
        # Always load a circuit — fall back to any driver's telemetry if pick_fastest failed
        if data.get("circuit_x") is not None:
            self.track_map.load_circuit(data["circuit_x"], data["circuit_y"])
        else:
            for recs in data["loc_recs"].values():
                if recs:
                    xs = np.array([r["x"] for r in recs])
                    ys = np.array([r["y"] for r in recs])
                    self.track_map.load_circuit(xs, ys)
                    break

        self._current_label = data["label"]
        self._session_label.setText(f"  {data['label']}")
        self.replay_toolbar.set_replay_mode(data["label"])
        f1_logger.log_session_loaded(data["label"])

        self._replay_ctrl = ReplayController(data)
        self._replay_ctrl.frame_ready.connect(self._on_data)
        self._replay_ctrl.time_updated.connect(self.replay_toolbar.set_elapsed)
        self._replay_ctrl.finished.connect(self._on_replay_finished)

        self._status.showMessage(f"Loaded — press ▶ to replay  ·  {data['label']}")

    # ── Replay controls ───────────────────────────────────────────────────────

    def _on_play_pause(self, play: bool):
        if not self._replay_ctrl:
            return
        if play:
            self._replay_ctrl.play()
            f1_logger.log_replay_started(self._current_label, self._replay_ctrl.speed)
        else:
            self._replay_ctrl.pause()
            f1_logger.log_replay_paused(self._replay_ctrl.elapsed)

    def _on_speed_changed(self, speed: float):
        if self._replay_ctrl:
            self._replay_ctrl.set_speed(speed)

    def _on_replay_finished(self):
        self._status.showMessage("Replay finished.")
        f1_logger.log_replay_finished(self._current_label)

    def _on_load_failed(self, message: str):
        self._status.showMessage(f"Load failed: {message}")
        f1_logger.log_error(message)

    # ── Go Live ───────────────────────────────────────────────────────────────

    def _go_live(self):
        if self._replay_ctrl:
            self._replay_ctrl.stop()
            self._replay_ctrl = None
        self.replay_toolbar.set_live_mode()
        self._session_label.setText("  Reconnecting to live session…")
        self._status.showMessage("Switching to live mode…")
        QTimer.singleShot(100, self._init_data)

    # ── Shared data callback ──────────────────────────────────────────────────

    def _on_data(self, data: dict):
        self.leaderboard.refresh(data)
        self.track_map.update_drivers(data["locations"], data["drivers"])

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def _stop_live(self):
        if self._fetcher:
            self._fetcher.stop()
            self._fetcher.wait(2000)
            self._fetcher = None

    def closeEvent(self, event):
        self._stop_live()
        if self._replay_ctrl:
            self._replay_ctrl.stop()
        for w in (self._loader, self._hist_loader, self._sched_worker):
            if w and w.isRunning():
                w.quit()
                w.wait(2000)
        event.accept()
