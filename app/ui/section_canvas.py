"""Widget Qt que desenha a seção transversal cotada de um perfil.

Consome a mesma :class:`~app.domain.drawing.SectionScene` usada pelo memorial
PDF (``app/report/pdf_report.py``) — nenhuma conta geométrica é duplicada
aqui, só o passo de renderização (``QPainter`` em vez de ``fpdf2``).
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from app.domain.drawing import Dimension, Polyline, SectionScene, build_section_scene
from app.domain.models import Profile
from app.ui import theme

_MARGIN_PX = 20
# Rótulos das cotas verticais são desenhados à direita da linha de cota, fora
# da caixa da cena: reserva espaço lateral para não serem cortados.
_LABEL_ROOM_PX = 60


class SectionCanvas(QWidget):
    """Desenha a seção cotada do perfil atual. Chame :meth:`set_profile` para atualizar."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scene: SectionScene | None = None
        self._destaque: str | None = None
        self.setMinimumSize(220, 220)

    def set_profile(self, profile: Profile | None) -> None:
        self._scene = build_section_scene(profile) if profile is not None else None
        self.update()

    def set_highlight(self, simbolo: str | None) -> None:
        """Destaca a cota cujo rótulo começa com ``simbolo`` (ex.: ``"bf"``)."""
        self._destaque = simbolo
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (nome exigido pelo Qt)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(theme.SURFACE))

        if self._scene is None:
            painter.end()
            return

        scene = self._scene
        avail_w = self.width() - 2 * (_MARGIN_PX + _LABEL_ROOM_PX)
        avail_h = self.height() - 2 * _MARGIN_PX
        scale = min(avail_w / scene.width_mm, avail_h / scene.height_mm)
        cx = self.width() / 2
        cy = self.height() / 2

        def to_widget(point: tuple[float, float]) -> QPointF:
            # +y da cena (para cima) vira -y em pixels (Qt cresce para baixo).
            return QPointF(cx + point[0] * scale, cy - point[1] * scale)

        pen_outline = QPen(QColor(theme.TEXT), 1.6)
        painter.setPen(pen_outline)
        for outline in scene.outline:
            if isinstance(outline, Polyline):
                pts = [to_widget(p) for p in outline.points]
                for p1, p2 in zip(pts, pts[1:]):
                    painter.drawLine(p1, p2)

        pen_dim = QPen(QColor(theme.TEXT_MUTED), 0.8)
        painter.setPen(pen_dim)
        font = QFont()
        font.setPointSizeF(8.0)
        painter.setFont(font)
        pen_destaque = QPen(QColor(theme.ACCENT), 1.6)
        font_destaque = QFont(font)
        font_destaque.setBold(True)
        destacada = None
        for dim in scene.dimensions:
            if self._destaque is not None and dim.label.startswith(f"{self._destaque} ="):
                destacada = dim
                continue
            self._draw_dimension(painter, dim, to_widget)
        if destacada is not None:
            # Desenhada por último para ficar por cima das demais cotas.
            painter.setPen(pen_destaque)
            painter.setFont(font_destaque)
            self._draw_dimension(painter, destacada, to_widget)
            painter.setFont(font)

        pen_circle_solido = QPen(QColor(theme.TEXT_MUTED), 0.8)
        pen_circle_tracejado = QPen(QColor(theme.TEXT_MUTED), 0.8, Qt.DashLine)
        for circle in scene.circles:
            painter.setPen(pen_circle_tracejado if circle.dashed else pen_circle_solido)
            center = to_widget(circle.center)
            radius_px = circle.radius * scale
            painter.drawEllipse(center, radius_px, radius_px)

        pen_axis = QPen(QColor(theme.TEXT_MUTED), 0.8, Qt.DashDotLine)
        painter.setPen(pen_axis)
        for axis in scene.axes:
            p1 = to_widget(axis.p1)
            p2 = to_widget(axis.p2)
            painter.drawLine(p1, p2)
            fm = painter.fontMetrics()
            text_w = fm.horizontalAdvance(axis.label)
            text_h = fm.height()
            painter.drawText(
                QRectF(p1.x() - text_w - 4, p1.y() - text_h / 2, text_w, text_h),
                Qt.AlignCenter,
                axis.label,
            )
            painter.drawText(
                QRectF(p2.x() + 4, p2.y() - text_h / 2, text_w, text_h),
                Qt.AlignCenter,
                axis.label,
            )

        painter.end()

    @staticmethod
    def _draw_dimension(painter: QPainter, dim: Dimension, to_widget) -> None:
        if dim.horizontal:
            y = dim.p1[1] + dim.offset
            p1_line = to_widget((dim.p1[0], y))
            p2_line = to_widget((dim.p2[0], y))
        else:
            x = dim.p1[0] + dim.offset
            p1_line = to_widget((x, dim.p1[1]))
            p2_line = to_widget((x, dim.p2[1]))

        p1_ref = to_widget(dim.p1)
        p2_ref = to_widget(dim.p2)

        painter.drawLine(p1_ref, p1_line)
        painter.drawLine(p2_ref, p2_line)
        painter.drawLine(p1_line, p2_line)

        t = dim.label_t
        anchor = QPointF(
            p1_line.x() + (p2_line.x() - p1_line.x()) * t,
            p1_line.y() + (p2_line.y() - p1_line.y()) * t,
        )
        fm = painter.fontMetrics()
        text_w = fm.horizontalAdvance(dim.label)
        text_h = fm.height()
        # Rótulo do lado de fora da peça: offset negativo = abaixo / à esquerda.
        if dim.horizontal:
            y_texto = anchor.y() + 2 if dim.offset < 0 else anchor.y() - text_h - 2
            rect = QRectF(anchor.x() - text_w / 2 - 2, y_texto, text_w + 4, text_h)
        else:
            x_texto = anchor.x() - text_w - 7 if dim.offset < 0 else anchor.x() + 3
            rect = QRectF(x_texto, anchor.y() - text_h / 2, text_w + 4, text_h)
        painter.drawText(rect, Qt.AlignCenter, dim.label)
