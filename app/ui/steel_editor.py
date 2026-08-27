"""Aba "Tipos de Aço": tabela editável sobre steel_types.

Mesmo padrão de `catalog_editor.py`: edição de célula grava imediatamente via
`SteelTypeRepository.upsert`, sem botão "Salvar" separado.
"""

from __future__ import annotations

import sqlite3
from dataclasses import replace

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.domain.models import SteelType
from app.repositories import SteelTypeRepository

_COLUNAS = [("fy (MPa)", "fy_mpa"), ("fu (MPa)", "fu_mpa")]


class _SteelTableModel(QAbstractTableModel):
    def __init__(self, repo: SteelTypeRepository) -> None:
        super().__init__()
        self._repo = repo
        self._rows: list[SteelType] = []
        self.reload()

    def reload(self) -> None:
        self.beginResetModel()
        self._rows = self._repo.list_all()
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 1 + len(_COLUNAS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):  # noqa: N802
        if role != Qt.DisplayRole or orientation != Qt.Horizontal:
            return None
        return "Designação" if section == 0 else _COLUNAS[section - 1][0]

    def flags(self, index: QModelIndex):
        base = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        return base | Qt.ItemIsEditable if index.column() > 0 else base

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if role not in (Qt.DisplayRole, Qt.EditRole):
            return None
        steel = self._rows[index.row()]
        if index.column() == 0:
            return steel.designacao
        _, campo = _COLUNAS[index.column() - 1]
        return getattr(steel, campo)

    def setData(self, index: QModelIndex, value, role=Qt.EditRole) -> bool:  # noqa: N802
        if role != Qt.EditRole or index.column() == 0:
            return False
        _, campo = _COLUNAS[index.column() - 1]
        try:
            numero = float(value)
        except (TypeError, ValueError):
            return False
        steel = self._rows[index.row()]
        novo = replace(steel, **{campo: numero})
        self._repo.upsert(novo)
        self._rows[index.row()] = novo
        self.dataChanged.emit(index, index)
        return True

    def steel_at(self, row: int) -> SteelType:
        return self._rows[row]


class SteelEditor(QWidget):
    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__()
        self._repo = SteelTypeRepository(conn)
        self._model = _SteelTableModel(self._repo)

        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.horizontalHeader().setStretchLastSection(True)

        btn_novo = QPushButton("Novo Tipo de Aço...")
        btn_novo.clicked.connect(self._on_novo)
        btn_remover = QPushButton("Remover")
        btn_remover.clicked.connect(self._on_remover)

        botoes = QHBoxLayout()
        botoes.addWidget(btn_novo)
        botoes.addWidget(btn_remover)
        botoes.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(botoes)
        layout.addWidget(self._table)

    def _on_novo(self) -> None:
        designacao, ok = QInputDialog.getText(self, "Novo Tipo de Aço", "Designação (ex.: ASTM A572 Grau 50):")
        if not ok or not designacao.strip():
            return
        designacao = designacao.strip()
        if self._repo.get(designacao) is not None:
            QMessageBox.warning(self, "Já existe", f"Já existe um aço '{designacao}'.")
            return
        self._repo.upsert(SteelType(designacao=designacao, fy_mpa=0.0, fu_mpa=0.0))
        self._model.reload()

    def _on_remover(self) -> None:
        index = self._table.currentIndex()
        if not index.isValid():
            return
        steel = self._model.steel_at(index.row())
        resposta = QMessageBox.question(self, "Remover", f"Remover o aço '{steel.designacao}'?")
        if resposta == QMessageBox.Yes:
            self._repo.delete(steel.designacao)
            self._model.reload()
