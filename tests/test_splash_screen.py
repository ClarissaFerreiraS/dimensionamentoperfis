from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QApplication

from app.ui.splash_screen import SplashScreen


def test_splash_screen_displays_structdim_branding():
    app = QApplication.instance() or QApplication([])
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    assert splash.windowTitle() == "StructDim"
    assert splash.size() == QSize(800, 620)
    assert splash.windowType() == Qt.Window
    assert splash._logo.width() >= 300
    assert splash._profile.width() >= 1500
    assert splash._timer.isActive()

    splash.close()
    assert not splash._timer.isActive()
