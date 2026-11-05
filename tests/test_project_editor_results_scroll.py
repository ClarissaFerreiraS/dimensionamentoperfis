from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QScrollArea, QTableView, QWidget

from app.db.database import open_database
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme


def test_project_results_can_scroll_on_short_windows():
    app = QApplication.instance() or QApplication([])
    apply_theme(app)
    conn = open_database(":memory:")
    window = MainWindow(conn, ":memory:")
    window.resize(900, 500)
    window.centralWidget().setCurrentIndex(1)
    window.show()
    app.processEvents()

    editor = window.findChild(QWidget, "projectsTab").editor
    tabs = window.centralWidget()
    assert tabs.tabBar().focusPolicy() == Qt.NoFocus
    result_scroll = editor.findChild(QScrollArea, "resultScroll")
    editor.resultado_label.setText(
        "<p>Resultado detalhado da verificação estrutural.</p>" * 80
        + f"<p>{'X' * 2000}</p>"
    )
    editor.resultado_label.adjustSize()
    app.processEvents()

    assert result_scroll is not None
    assert result_scroll.verticalScrollBar().maximum() > 0
    assert result_scroll.horizontalScrollBar().maximum() > 0
    catalog_table = window.findChild(QTableView)
    assert result_scroll.verticalScrollBar().style() == catalog_table.verticalScrollBar().style()
    assert result_scroll.horizontalScrollBar().style() == catalog_table.horizontalScrollBar().style()
    assert result_scroll.viewport().styleSheet() == "background-color: #ffffff;"

    window.close()
    conn.close()
    app.processEvents()
