#!/usr/bin/env python3
"""main.py — Entry point for the F1 Live Dashboard.

Run:
    .venv\\Scripts\\python main.py     (Windows)
    .venv/bin/python main.py           (Linux / macOS)
"""

import sys
from PyQt6.QtWidgets import QApplication
from f1_gui import F1Dashboard


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("F1 Live Dashboard")
    window = F1Dashboard()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
