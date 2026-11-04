from __future__ import annotations

from PySide6.QtWidgets import QApplication, QFrame, QLabel, QPushButton, QTabWidget

from app import __version__
from app.db.database import open_database
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme


def test_about_tab_is_first_and_button_opens_projects():
    app = QApplication.instance() or QApplication([])
    apply_theme(app)
    conn = open_database(":memory:")
    window = MainWindow(conn, ":memory:")
    tabs = window.centralWidget()

    assert window.windowTitle() == (
        "StructDim - Dimensionamento de Perfis de Aço (ABNT NBR 8800:2024)"
    )
    assert __version__ not in window.windowTitle()
    assert not window.windowIcon().isNull()
    assert isinstance(tabs, QTabWidget)
    assert tabs.tabText(0) == "Conheça o StructDim"
    assert tabs.tabText(1) == "Projetos"
    assert tabs.currentIndex() == 0

    about_tab = tabs.widget(0)
    intro = about_tab.findChild(QLabel, "aboutIntro").text()
    assert "desenvolvida em Python" in intro
    assert "ABNT NBR 8800:2024" in intro
    assert "memorial de cálculo em PDF" in intro
    hero = about_tab.findChild(QFrame, "aboutHero")
    assert hero is not None
    assert hero.property("backgroundImage").endswith("structdim_perfis_aco.png")
    assert hero.minimumHeight() >= 350
    assert len(about_tab.findChildren(QFrame, "aboutStep")) == 3
    note = about_tab.findChild(QLabel, "aboutNote")
    assert "Atenção:" in note.text()
    assert "ferramenta de finalidade educacional" in note.text()
    start_button = about_tab.findChild(QPushButton, "primary")
    assert start_button is not None
    assert start_button.text() == "Começar agora →"
    start_button.click()
    assert tabs.currentWidget() is tabs.widget(1)

    window.close()
    conn.close()
