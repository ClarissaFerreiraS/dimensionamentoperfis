"""Janela principal: abas Projetos / Catálogo de Perfis / Tipos de Aço."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QStyle,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.domain.models import ProfileFamily
from app.repositories import ProjectRepository
from app.ui.catalog_editor import CatalogEditor
from app.ui.profile_details import ProfileDetailsTab
from app.ui.project_editor import ProjectEditor
from app.ui.steel_editor import SteelEditor
from app.ui import theme


def _app_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#2f6f9f"))
    painter.drawRoundedRect(QRectF(3, 3, 58, 58), 12, 12)

    painter.setBrush(QColor("#ffffff"))
    painter.drawRoundedRect(QRectF(12, 12, 40, 9), 2, 2)
    painter.drawRoundedRect(QRectF(27, 19, 10, 27), 2, 2)
    painter.drawRoundedRect(QRectF(12, 43, 40, 9), 2, 2)

    painter.setPen(QPen(QColor("#f0a04b"), 3))
    painter.drawLine(14, 56, 50, 56)
    painter.drawLine(14, 52, 14, 60)
    painter.drawLine(50, 52, 50, 60)
    painter.end()
    return QIcon(pixmap)


def _duplicate_icon() -> QIcon:
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(QColor(theme.TEXT), 2.6))
    painter.setBrush(QColor(theme.SURFACE))
    painter.drawRoundedRect(QRectF(8, 2, 20, 22), 4, 4)
    painter.drawRoundedRect(QRectF(2, 8, 20, 22), 4, 4)
    painter.end()
    return QIcon(pixmap)


def _delete_icon() -> QIcon:
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    dark_blue = QColor("#234c70")
    blue = QColor("#2f6f9f")
    painter.setPen(QPen(dark_blue, 2.1))
    painter.setBrush(QColor("#ffffff"))
    painter.drawRoundedRect(QRectF(8, 9, 16, 19), 2, 2)

    painter.setPen(Qt.NoPen)
    painter.setBrush(blue)
    painter.drawRoundedRect(QRectF(6, 6, 20, 4), 2, 2)
    painter.drawRoundedRect(QRectF(13, 3, 6, 4), 2, 2)

    painter.setPen(QPen(dark_blue, 1.7))
    painter.drawLine(13, 13, 13, 24)
    painter.drawLine(19, 13, 19, 24)
    painter.end()
    return QIcon(pixmap)


def _pdf_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    blue = QColor("#2f6f9f")
    dark_blue = QColor("#234c70")
    painter.setPen(QPen(dark_blue, 2.4))
    painter.setBrush(QColor("#ffffff"))
    painter.drawRoundedRect(QRectF(7, 2, 50, 60), 4, 4)
    painter.drawLine(40, 2, 57, 19)
    painter.drawLine(40, 2, 40, 19)
    painter.drawLine(40, 19, 57, 19)

    painter.setPen(Qt.NoPen)
    painter.setBrush(blue)
    painter.drawRoundedRect(QRectF(10, 23, 44, 18), 3, 3)
    painter.setPen(QColor("#ffffff"))
    painter.setFont(QFont("Arial", 15, QFont.Bold))
    painter.drawText(QRectF(10, 23, 44, 18), Qt.AlignCenter, "PDF")

    painter.setPen(QPen(dark_blue, 3.2))
    painter.setBrush(Qt.NoBrush)
    painter.drawLine(32, 46, 32, 55)
    painter.drawLine(27, 51, 32, 56)
    painter.drawLine(37, 51, 32, 56)
    painter.drawLine(23, 59, 41, 59)
    painter.end()
    return QIcon(pixmap)


class _ProjectsTab(QWidget):
    """Lista de projetos (novo/abrir/duplicar/excluir) + `ProjectEditor` embutido."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__()
        self._repo = ProjectRepository(conn)

        self._lista = QListWidget()
        self._lista.setObjectName("projectList")
        self._lista.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self._lista.currentItemChanged.connect(self._on_selecao_mudou)

        self.editor = ProjectEditor(conn)
        self.editor.project_saved.connect(self._reload_lista)

        icones = self.style()
        barra = QHBoxLayout()
        barra.setSpacing(0)
        for texto, icone, atalho, acao in (
            ("Novo", QStyle.SP_FileDialogNewFolder, "Ctrl+N", self._on_novo),
            ("Salvar", QStyle.SP_DialogSaveButton, "Ctrl+S", self.editor.salvar),
            ("Duplicar", _duplicate_icon(), "Ctrl+D", self._on_duplicar),
            ("PDF", _pdf_icon(), "Ctrl+P", self.editor.gerar_pdf),
            ("Excluir", _delete_icon(), "Delete", self._on_excluir),
        ):
            botao = QToolButton()
            botao.setText(texto)
            botao.setIcon(icone if isinstance(icone, QIcon) else icones.standardIcon(icone))
            botao.setIconSize(QSize(22, 22))
            botao.setMinimumWidth(botao.fontMetrics().horizontalAdvance(texto) + 14)
            botao.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            botao.setShortcut(atalho)
            botao.setToolTip(f"{texto} ({atalho})")
            botao.setCursor(Qt.PointingHandCursor)
            botao.clicked.connect(acao)
            barra.addWidget(botao)
        barra.addStretch(1)

        esquerda = QFrame()
        esquerda.setFixedWidth(300)
        esquerda_layout = QVBoxLayout(esquerda)
        esquerda_layout.setContentsMargins(0, 0, 8, 0)
        esquerda_layout.addLayout(barra)
        esquerda_layout.addWidget(self._lista, 1)

        separador = QFrame()
        separador.setFrameShape(QFrame.VLine)
        separador.setStyleSheet(f"color: {theme.BORDER};")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(esquerda)
        layout.addWidget(separador)
        layout.addWidget(self.editor, 1)

        self._reload_lista()

    def _reload_lista(self) -> None:
        projeto_atual = self.editor.project_id
        self._lista.blockSignals(True)
        self._lista.clear()
        for row in self._repo.list_all():
            subtitulo = row["autor"] or row["bitola"]
            item = QListWidgetItem(f"{row['nome']}\n{subtitulo}")
            item.setData(Qt.UserRole, row["id"])
            self._lista.addItem(item)
            if row["id"] == projeto_atual:
                self._lista.setCurrentItem(item)
        self._lista.blockSignals(False)

    def _current_project_id(self) -> int | None:
        item = self._lista.currentItem()
        return item.data(Qt.UserRole) if item is not None else None

    def _on_selecao_mudou(self, atual: QListWidgetItem | None, _anterior) -> None:
        if atual is None:
            self.editor.load_new()
            return
        self.editor.load_project(atual.data(Qt.UserRole))

    def _on_novo(self) -> None:
        self._lista.setCurrentItem(None)
        self.editor.load_new()

    def _on_duplicar(self) -> None:
        project_id = self._current_project_id()
        if project_id is None:
            return
        row = self._repo.get(project_id)
        if row is None:
            return
        loads = ProjectRepository.load_case_from_row(row)
        novo_id = self._repo.create(
            nome=f"{row['nome']} (cópia)",
            autor=row["autor"],
            family=ProfileFamily(row["family"]),
            bitola=row["bitola"],
            steel_designacao=row["steel_designacao"],
            loads=loads,
        )
        self._reload_lista()
        for i in range(self._lista.count()):
            item = self._lista.item(i)
            if item.data(Qt.UserRole) == novo_id:
                self._lista.setCurrentItem(item)
                break

    def _on_excluir(self) -> None:
        project_id = self._current_project_id()
        if project_id is None:
            return
        dialogo = QMessageBox(self)
        dialogo.setIcon(QMessageBox.Question)
        dialogo.setWindowTitle("Excluir Projeto")
        dialogo.setText("Excluir o projeto selecionado?")
        botao_sim = dialogo.addButton("Sim", QMessageBox.YesRole)
        botao_nao = dialogo.addButton("Não", QMessageBox.NoRole)
        dialogo.setDefaultButton(botao_nao)
        dialogo.exec()
        if dialogo.clickedButton() is botao_sim:
            self._repo.delete(project_id)
            self.editor.load_new()
            self._reload_lista()


class MainWindow(QMainWindow):
    def __init__(self, conn: sqlite3.Connection, db_path: str | Path) -> None:
        super().__init__()
        self.setWindowTitle("Dimensionamento de Perfis Metálicos - ABNT NBR 8800:2024")
        self.setWindowIcon(_app_icon())
        self.resize(1280, 820)

        abas = QTabWidget()
        abas.setDocumentMode(True)
        projetos = _ProjectsTab(conn)
        detalhes = ProfileDetailsTab()
        projetos.editor.profile_changed.connect(detalhes.set_profile)
        projetos.editor.details_requested.connect(lambda: abas.setCurrentWidget(detalhes))
        detalhes.set_profile(projetos.editor.profile)
        abas.addTab(projetos, "Projetos")
        abas.addTab(detalhes, "Detalhes do Perfil")
        catalog_editor = CatalogEditor(conn, db_path)
        abas.addTab(catalog_editor, "Catálogo de Perfis")
        abas.addTab(SteelEditor(conn), "Tipos de Aço")

        self.setCentralWidget(abas)
