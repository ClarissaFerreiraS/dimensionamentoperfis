"""Janela principal: abas Projetos / Catálogo de Perfis / Tipos de Aço."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.domain.models import ProfileFamily
from app.repositories import ProjectRepository
from app.ui.catalog_editor import CatalogEditor
from app.ui.project_editor import ProjectEditor
from app.ui.steel_editor import SteelEditor


class _ProjectsTab(QWidget):
    """Lista de projetos (novo/abrir/duplicar/excluir) + `ProjectEditor` embutido."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__()
        self._repo = ProjectRepository(conn)

        self._lista = QListWidget()
        self._lista.currentItemChanged.connect(self._on_selecao_mudou)

        btn_novo = QPushButton("Novo Projeto")
        btn_novo.clicked.connect(self._on_novo)
        btn_duplicar = QPushButton("Duplicar")
        btn_duplicar.clicked.connect(self._on_duplicar)
        btn_excluir = QPushButton("Excluir")
        btn_excluir.clicked.connect(self._on_excluir)

        botoes = QHBoxLayout()
        botoes.addWidget(btn_novo)
        botoes.addWidget(btn_duplicar)
        botoes.addWidget(btn_excluir)

        esquerda = QWidget()
        esquerda_layout = QVBoxLayout(esquerda)
        esquerda_layout.addLayout(botoes)
        esquerda_layout.addWidget(self._lista)

        self._editor = ProjectEditor(conn)
        self._editor.project_saved.connect(self._reload_lista)

        splitter = QSplitter()
        splitter.addWidget(esquerda)
        splitter.addWidget(self._editor)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        layout = QVBoxLayout(self)
        layout.addWidget(splitter)

        self._reload_lista()

    def _reload_lista(self) -> None:
        projeto_atual = self._current_project_id()
        self._lista.blockSignals(True)
        self._lista.clear()
        for row in self._repo.list_all():
            item = QListWidgetItem(row["nome"])
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
            self._editor.load_new()
            return
        self._editor.load_project(atual.data(Qt.UserRole))

    def _on_novo(self) -> None:
        self._lista.setCurrentItem(None)
        self._editor.load_new()

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
            self._reload_lista()


class MainWindow(QMainWindow):
    def __init__(self, conn: sqlite3.Connection, db_path: str | Path) -> None:
        super().__init__()
        self.setWindowTitle("Dimensionamento de Pilares — NBR 8800:2024")
        self.resize(1200, 800)

        abas = QTabWidget()
        abas.addTab(_ProjectsTab(conn), "Projetos")
        catalog_editor = CatalogEditor(conn, db_path)
        abas.addTab(catalog_editor, "Catálogo de Perfis")
        abas.addTab(SteelEditor(conn), "Tipos de Aço")

        self.setCentralWidget(abas)
