"""Ponto de entrada do app desktop: ``python -m app.main``."""

from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app.db.database import DEFAULT_DB_PATH, open_database
from app.ui.main_window import MainWindow, _app_icon
from app.ui.splash_screen import SplashScreen
from app.ui.theme import apply_theme


def main() -> int:
    app = QApplication(sys.argv)
    apply_theme(app)
    app.setWindowIcon(_app_icon())

    splash = SplashScreen()
    splash.show()
    app.processEvents()

    splash.set_progress(20, "Preparando o catálogo...")
    app.processEvents()
    conn = open_database(DEFAULT_DB_PATH)

    splash.set_progress(55, "Carregando a interface...")
    app.processEvents()
    window = MainWindow(conn, DEFAULT_DB_PATH)
    window.showMaximized()

    splash.set_progress(100, "Sistema pronto.")
    app.processEvents()
    QTimer.singleShot(250, splash.close)

    exit_code = app.exec()
    conn.close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
