"""Tela inicial da aplicação StructDim."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget


_ASSETS = Path(__file__).resolve().parent / "assets"
_LOGO_IMAGE = _ASSETS / "structdim_logo.png"
_PROFILE_IMAGE = _ASSETS / "structdim_perfis_aco.png"
_WIDTH = 800
_HEIGHT = 620


def _load_image(path: Path) -> QPixmap:
    image = QPixmap(str(path))
    if image.isNull():
        raise FileNotFoundError(f"Imagem da tela inicial não encontrada: {path}")
    return image


class SplashScreen(QWidget):
    def __init__(self) -> None:
        super().__init__(None, Qt.Window)
        self._logo = _load_image(_LOGO_IMAGE)
        self._profile = _load_image(_PROFILE_IMAGE)
        self._progress = 0
        self._status = "Preparando o sistema..."
        self.setFixedSize(_WIDTH, _HEIGHT)
        self.setWindowTitle("StructDim")

    def set_progress(self, value: int, status: str) -> None:
        self._progress = max(0, min(value, 100))
        self._status = status
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        background = self._profile.scaled(
            self.size(),
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
        painter.drawPixmap(
            (self.width() - background.width()) // 2,
            (self.height() - background.height()) // 2,
            background,
        )

        shade = QLinearGradient(0, 0, self.width(), 0)
        shade.setColorAt(0, QColor(4, 20, 39, 232))
        shade.setColorAt(0.55, QColor(5, 28, 51, 218))
        shade.setColorAt(1, QColor(4, 22, 42, 190))
        painter.fillRect(self.rect(), shade)

        badge = QRect(326, 35, 148, 136)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 245))
        painter.drawRoundedRect(badge, 20, 20)
        logo = self._logo.scaled(
            130,
            118,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        painter.drawPixmap(
            badge.center().x() - logo.width() // 2,
            badge.center().y() - logo.height() // 2,
            logo,
        )

        title_font = QFont("Segoe UI", 52, QFont.Bold)
        painter.setFont(title_font)
        metrics = QFontMetricsF(title_font)
        first = "Struct"
        second = "Dim"
        first_width = metrics.horizontalAdvance(first)
        second_width = metrics.horizontalAdvance(second)
        title_x = (self.width() - first_width - second_width) / 2
        title_y = 267
        painter.setPen(QColor("#ffffff"))
        painter.drawText(int(title_x), title_y, first)
        painter.setPen(QColor("#72b5e3"))
        painter.drawText(int(title_x + first_width), title_y, second)

        painter.setPen(QPen(QColor("#9bc8e8"), 1))
        painter.drawLine(130, 294, 670, 294)

        subtitle_font = QFont("Segoe UI", 12, QFont.DemiBold)
        subtitle_font.setLetterSpacing(QFont.AbsoluteSpacing, 3.2)
        painter.setFont(subtitle_font)
        painter.setPen(QColor("#e5eff8"))
        painter.drawText(
            QRect(65, 310, 670, 34),
            Qt.AlignCenter,
            "DIMENSIONAMENTO DE PERFIS DE AÇO",
        )

        standard_font = QFont("Segoe UI", 15, QFont.Medium)
        standard_font.setLetterSpacing(QFont.AbsoluteSpacing, 2.5)
        painter.setFont(standard_font)
        painter.setPen(QColor("#83bfe5"))
        painter.drawText(
            QRect(100, 362, 600, 34),
            Qt.AlignCenter,
            "ABNT NBR 8800:2024",
        )

        status_font = QFont("Segoe UI", 11)
        painter.setFont(status_font)
        painter.setPen(QColor("#e0eaf4"))
        painter.drawText(
            QRect(70, 482, 660, 30),
            Qt.AlignCenter,
            self._status,
        )

        track = QRect(100, 530, 600, 14)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(185, 210, 232, 48))
        painter.drawRoundedRect(track, 7, 7)
        fill_width = round(track.width() * self._progress / 100)
        if fill_width:
            fill = QRect(track.x(), track.y(), fill_width, track.height())
            progress = QLinearGradient(fill.topLeft(), fill.topRight())
            progress.setColorAt(0, QColor("#4c91c5"))
            progress.setColorAt(1, QColor("#80c6f0"))
            painter.setBrush(progress)
            painter.drawRoundedRect(fill, 7, 7)
