"""Tema claro do app (paleta Fusion + folha de estilo Qt).

Centraliza as cores para que widgets pintados à mão (ex.: ``SectionCanvas``)
e o texto do resultado usem os mesmos tons da folha de estilo.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, QTimer
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QComboBox, QStyleOptionViewItem, QStyledItemDelegate

BG = "#f5f7fa"
SURFACE = "#ffffff"
FIELD = "#ffffff"
BORDER = "#d0d7de"
TEXT = "#1f2328"
TEXT_MUTED = "#1f2328"
TEXT_SECTION = "#1f2328"
ACCENT = "#2563eb"
SUCCESS = "#138a3d"
DANGER = "#d32f2f"


class _ComboItemDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index) -> None:
        item_option = QStyleOptionViewItem(option)
        item_option.features &= ~QStyleOptionViewItem.HasCheckIndicator
        item_option.checkState = Qt.Unchecked
        super().paint(painter, item_option, index)


class _ComboPopupController(QObject):
    def __init__(self, combo: QComboBox, constrain_height: bool) -> None:
        super().__init__(combo.view())
        self._combo = combo
        self._constrain_height = constrain_height

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Show:
            for delay in (0, 50, 150):
                QTimer.singleShot(delay, lambda view=watched: self._fix_position(view))
        return super().eventFilter(watched, event)

    def _fix_position(self, view) -> None:
        if view.isVisible():
            view.verticalScrollBar().setValue(0)
            popup = view.window()
            screen = self._combo.screen()
            if screen is None:
                return

            combo_top_left = self._combo.mapToGlobal(QPoint(0, 0))
            combo_bottom = combo_top_left.y() + self._combo.height()
            if not self._constrain_height:
                popup.move(combo_top_left.x(), combo_bottom)
                return

            screen_geometry = screen.availableGeometry()
            space_below = screen_geometry.bottom() - combo_bottom + 1
            space_above = combo_top_left.y() - screen_geometry.top()
            popup.setMaximumHeight(16777215)
            row_height = view.sizeHintForRow(0)
            if row_height <= 0:
                row_height = self._combo.fontMetrics().height() + 8
            item_count = max(view.model().rowCount(), 1)
            natural_height = max(
                popup.sizeHint().height(),
                row_height * item_count + 2,
            )
            popup_height = min(natural_height, max(space_below, space_above))
            popup.setMaximumHeight(popup_height)
            popup.resize(popup.width(), popup_height)

            if space_below >= popup_height or space_below >= space_above:
                popup.move(combo_top_left.x(), combo_bottom)
            else:
                popup.move(
                    combo_top_left.x(),
                    combo_top_left.y() - popup_height,
                )


def configure_combo(combo: QComboBox, allow_scroll: bool = False) -> None:
    view = combo.view()
    view.setItemDelegate(_ComboItemDelegate(view))
    if not allow_scroll:
        view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    view.installEventFilter(_ComboPopupController(combo, allow_scroll))


_STYLESHEET = f"""
QWidget {{ font-size: 10pt; }}
QMainWindow, QDialog {{ background: {BG}; }}

QTabWidget::pane {{ border: none; border-top: 1px solid {BORDER}; }}
QTabBar::tab {{
    background: transparent; color: {TEXT_MUTED};
    padding: 7px 16px; border: none; border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{ color: {TEXT}; border-bottom: 2px solid {ACCENT}; }}
QTabBar::tab:hover:!selected {{ color: {TEXT}; }}

QGroupBox {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 8px;
    margin-top: 14px; padding: 14px 10px 10px 10px;
}}
QGroupBox::title {{
    subcontrol-origin: margin; subcontrol-position: top left;
    left: 10px; padding: 0 6px; color: {TEXT}; font-weight: 600;
}}

QLineEdit, QComboBox, QDoubleSpinBox, QPlainTextEdit {{
    background: {FIELD}; border: 1px solid {BORDER}; border-radius: 5px;
    padding: 4px 6px;     color: {TEXT};
        selection-background-color: #c4d9eb; selection-color: {TEXT};
    }}
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QPlainTextEdit:focus {{
    border: 1px solid {ACCENT};
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background: {FIELD}; border: 1px solid {BORDER};
    selection-background-color: #c4d9eb; selection-color: {TEXT};
    show-decoration-selected: 0;
}}
QComboBox::item:selected, QComboBox QAbstractItemView::item:selected,
QComboBox QAbstractItemView::item:selected:active,
QComboBox QAbstractItemView::item:selected:!active {{
    background: #c4d9eb; color: {TEXT};
}}
QComboBox QAbstractItemView::indicator {{
    image: none; width: 0px; height: 0px;
}}
QComboBox QAbstractItemView::indicator:checked,
QComboBox QAbstractItemView::indicator:unchecked {{
    image: none; width: 0px; height: 0px;
}}

QPushButton {{
    background: {FIELD}; border: 1px solid {BORDER}; border-radius: 6px;
    padding: 7px 14px; color: {TEXT};
}}
QPushButton:hover {{ background: #f0f3f6; }}
QPushButton:pressed {{ background: #e6ebf0; }}
QPushButton#primary {{
    background: {ACCENT}; border: 1px solid {ACCENT}; color: white;
    font-weight: 600; letter-spacing: 1px; padding: 9px;
}}
QPushButton#primary:hover {{ background: #3b82f6; }}
QPushButton#success {{
    background: {SUCCESS}; border: 1px solid {SUCCESS}; color: white; font-weight: 600;
}}
QPushButton#success:hover {{ background: #2da44e; }}

QToolButton {{
    background: transparent; border: 1px solid transparent; border-radius: 6px;
    padding: 4px; color: {TEXT};
}}
QToolButton:hover {{ background: {FIELD}; border: 1px solid {BORDER}; }}

QListWidget#projectList {{ background: transparent; border: none; outline: none; }}
QListWidget#projectList::item {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 8px;
    padding: 10px 12px; margin: 3px 0; color: {TEXT};
}}
QListWidget#projectList::item:hover {{ border: 1px solid #afb8c1; }}
QListWidget#projectList::item:selected {{
    background: #dbeafe; border: 1px solid {ACCENT}; color: {TEXT};
}}

QLabel#muted {{ color: {TEXT_MUTED}; }}
QLabel#pageTitle {{ color: {TEXT}; font-size: 18pt; font-weight: 700; }}
QLabel#aboutEyebrow {{
    color: {ACCENT}; font-size: 9pt; font-weight: 700; letter-spacing: 1.5px;
}}
QLabel#aboutTitle {{ color: {TEXT}; font-size: 23pt; font-weight: 700; }}
QLabel#aboutIntro {{ color: {TEXT}; font-size: 11pt; }}
QFrame#aboutHero {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 8px;
}}
QFrame#aboutDivider {{ color: {BORDER}; }}
QLabel#aboutSectionTitle {{ color: {TEXT}; font-size: 15pt; font-weight: 700; }}
QFrame#aboutStep {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 8px;
}}
QLabel#aboutStepNumber {{
    background: #eaf2ff; border-radius: 20px; color: {ACCENT};
    font-weight: 700; font-size: 11pt;
}}
QLabel#aboutStepTitle {{ color: {TEXT}; font-size: 12pt; font-weight: 600; }}
QLabel#aboutStepDescription {{ color: {TEXT_MUTED}; font-size: 11pt; }}
QFrame#aboutFooter {{
    background: #eaf2ff; border: 1px solid #d5e4fa; border-radius: 8px;
}}
QLabel#aboutNote {{ color: #334e70; font-size: 11pt; }}
QPushButton#link {{
    background: transparent; border: none; color: {ACCENT}; padding: 2px 4px;
}}
QPushButton#link:hover {{ color: #1d4ed8; text-decoration: underline; }}
QScrollArea {{ background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QLabel#sectionTitle {{
    color: {TEXT_MUTED}; font-size: 8pt; font-weight: 600; letter-spacing: 1px;
    padding: 4px 6px; border-bottom: 1px solid {BORDER};
}}
QFrame#propRow {{ border-radius: 4px; }}
QFrame#propRow:hover {{ background: #eaf2ff; }}
QLabel#value {{ color: {TEXT}; font-weight: 600; }}
QLabel#ncrd {{ color: {TEXT}; font-weight: 700; font-size: 11pt; }}
QLabel#materialProperty {{ color: {TEXT}; font-size: 10pt; font-weight: 400; }}
QLabel#resultText {{ font-size: 12pt; }}

QFrame#loadHeader {{
    background: {FIELD}; border: 1px solid {BORDER}; border-radius: 6px;
}}

QProgressBar {{
    background: {FIELD}; border: 1px solid {BORDER}; border-radius: 5px;
    text-align: center; color: {TEXT}; height: 16px;
}}
QProgressBar::chunk {{ border-radius: 4px; }}

QSplitter::handle {{ background: {BG}; }}
QTableView {{ gridline-color: {BORDER}; background: {SURFACE}; }}
QHeaderView::section {{
    background: {FIELD}; color: {TEXT}; border: none;
    border-right: 1px solid {BORDER}; padding: 4px;
}}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(BG))
    palette.setColor(QPalette.WindowText, QColor(TEXT))
    palette.setColor(QPalette.Base, QColor(FIELD))
    palette.setColor(QPalette.AlternateBase, QColor(SURFACE))
    palette.setColor(QPalette.Text, QColor(TEXT))
    palette.setColor(QPalette.Button, QColor(FIELD))
    palette.setColor(QPalette.ButtonText, QColor(TEXT))
    palette.setColor(QPalette.Highlight, QColor("#c4d9eb"))
    palette.setColor(QPalette.HighlightedText, QColor(TEXT))
    palette.setColor(QPalette.ToolTipBase, QColor(SURFACE))
    palette.setColor(QPalette.ToolTipText, QColor(TEXT))
    palette.setColor(QPalette.PlaceholderText, QColor(TEXT_MUTED))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(TEXT_MUTED))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(TEXT_MUTED))
    app.setPalette(palette)

    app.setStyleSheet(_STYLESHEET)
