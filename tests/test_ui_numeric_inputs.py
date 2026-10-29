"""Regression tests for visible numeric inputs in the project editor."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from app.db.database import open_database
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme


@pytest.fixture(scope="module")
def project_editor():
    app = QApplication.instance() or QApplication([])
    apply_theme(app)
    conn = open_database(":memory:")
    window = MainWindow(conn, ":memory:")
    window.resize(1228, 768)
    window.show()
    app.processEvents()
    editor = window.centralWidget().widget(0).editor

    yield editor

    window.close()
    conn.close()
    app.processEvents()


@pytest.mark.parametrize(
    ("field", "expected_value"),
    (
        ("ea_spin", 200.0),
        ("ga_spin", 77.0),
        ("ncsd_spin", 0.0),
        ("lx_spin", 1.0),
        ("kx_spin", 1.0),
        ("ly_spin", 1.0),
        ("ky_spin", 1.0),
        ("lz_spin", 1.0),
        ("kz_spin", 1.0),
    ),
)
def test_numeric_input_value_is_visible(project_editor, field, expected_value):
    spinbox = getattr(project_editor, field)
    line_edit = spinbox.lineEdit()

    assert spinbox.value() == expected_value
    assert spinbox.text()
    assert line_edit.width() >= spinbox.fontMetrics().horizontalAdvance(spinbox.text())
