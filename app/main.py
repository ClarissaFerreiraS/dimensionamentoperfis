"""Ponto de entrada do app desktop: ``python -m app.main``."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.db.database import DEFAULT_DB_PATH, open_database
from app.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)

    conn = open_database(DEFAULT_DB_PATH)
    window = MainWindow(conn, DEFAULT_DB_PATH)
    window.show()

    exit_code = app.exec()
    conn.close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
