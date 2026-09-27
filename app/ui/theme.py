"""Tema escuro do app (paleta Fusion + folha de estilo Qt).

Centraliza as cores para que widgets pintados à mão (ex.: ``SectionCanvas``)
e o texto do resultado usem os mesmos tons da folha de estilo.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

BG = "#1e1f22"
SURFACE = "#26282c"
FIELD = "#303338"
BORDER = "#43464d"
TEXT = "#e6e6e6"
TEXT_MUTED = "#9aa0a6"
ACCENT = "#4c8bf5"
SUCCESS = "#3fb950"
DANGER = "#f85149"

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
    padding: 4px 6px; color: {TEXT}; selection-background-color: {ACCENT};
}}
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QPlainTextEdit:focus {{
    border: 1px solid {ACCENT};
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background: {FIELD}; border: 1px solid {BORDER}; selection-background-color: {ACCENT};
}}

QPushButton {{
    background: {FIELD}; border: 1px solid {BORDER}; border-radius: 6px;
    padding: 7px 14px; color: {TEXT};
}}
QPushButton:hover {{ background: #3a3d44; }}
QPushButton:pressed {{ background: #2a2c31; }}
QPushButton#primary {{
    background: {ACCENT}; border: 1px solid {ACCENT}; color: white;
    font-weight: 600; letter-spacing: 1px; padding: 9px;
}}
QPushButton#primary:hover {{ background: #5d98f7; }}
QPushButton#success {{
    background: {SUCCESS}; border: 1px solid {SUCCESS}; color: #0d1117; font-weight: 600;
}}
QPushButton#success:hover {{ background: #56c965; }}

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
QListWidget#projectList::item:hover {{ border: 1px solid #5a5e66; }}
QListWidget#projectList::item:selected {{
    background: #2f3847; border: 1px solid {ACCENT}; color: {TEXT};
}}

QLabel#muted {{ color: {TEXT_MUTED}; }}
QLabel#pageTitle {{ color: {TEXT}; font-size: 18pt; font-weight: 700; }}
QPushButton#link {{
    background: transparent; border: none; color: {ACCENT}; padding: 2px 4px;
}}
QPushButton#link:hover {{ color: #7aa9f8; text-decoration: underline; }}
QScrollArea {{ background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QLabel#sectionTitle {{
    color: {TEXT_MUTED}; font-size: 8pt; font-weight: 600; letter-spacing: 1px;
    padding: 4px 6px; border-bottom: 1px solid {BORDER};
}}
QFrame#propRow {{ border-radius: 4px; }}
QFrame#propRow:hover {{ background: {FIELD}; }}
QLabel#value {{ color: {TEXT}; font-weight: 600; }}
QLabel#ncrd {{ color: {TEXT}; font-weight: 700; font-size: 11pt; }}

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
    palette.setColor(QPalette.Highlight, QColor(ACCENT))
    palette.setColor(QPalette.HighlightedText, QColor("white"))
    palette.setColor(QPalette.ToolTipBase, QColor(SURFACE))
    palette.setColor(QPalette.ToolTipText, QColor(TEXT))
    palette.setColor(QPalette.PlaceholderText, QColor(TEXT_MUTED))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(TEXT_MUTED))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(TEXT_MUTED))
    app.setPalette(palette)

    app.setStyleSheet(_STYLESHEET)
