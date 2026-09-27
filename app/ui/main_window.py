"""Janela principal: abas Projetos / Catálogo de Perfis / Tipos de Aço."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from PySide6.QtCore import QSize, Qt
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
            ("Novo", QStyle.SP_FileIcon, "Ctrl+N", self._on_novo),
            ("Salvar", QStyle.SP_DialogSaveButton, "Ctrl+S", self.editor.salvar),
            ("Duplicar", QStyle.SP_FileDialogNewFolder, "Ctrl+D", self._on_duplicar),
            ("PDF", QStyle.SP_FileDialogDetailedView, "Ctrl+P", self.editor.gerar_pdf),
            ("Excluir", QStyle.SP_TrashIcon, "Delete", self._on_excluir),
        ):
            botao = QToolButton()
            botao.setText(texto)
            botao.setIcon(icones.standardIcon(icone))
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
        separador.setStyleSheet("color: #43464d;")

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
            observacoes=row["observacoes"],
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
        resposta = QMessageBox.question(self, "Excluir Projeto", "Excluir o projeto selecionado?")
        if resposta == QMessageBox.Yes:
            self._repo.delete(project_id)
            self.editor.load_new()
            self._reload_lista()


class MainWindow(QMainWindow):
    def __init__(self, conn: sqlite3.Connection, db_path: str | Path) -> None:
        super().__init__()
        self.setWindowTitle("Dimensionamento de Pilares — NBR 8800:2024")
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
