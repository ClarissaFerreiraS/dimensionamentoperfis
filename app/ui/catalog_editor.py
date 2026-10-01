"""Aba "Catálogo de Perfis": tabelas somente para consulta."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import (
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.domain.models import Profile, ProfileFamily
from app.repositories import ProfileRepository

# (cabeçalho exibido, nome do campo em Profile). "Bitola" é a identificação
# do perfil e permanece apenas como a primeira coluna da tabela.
_COLUNAS_LAMINADO = [
    ("d (mm)", "d_mm"),
    ("bf (mm)", "bf_mm"),
    ("tw (mm)", "tw_mm"),
    ("tf (mm)", "tf_mm"),
    ("h (mm)", "h_mm"),
    ("d' (mm)", "d_linha_mm"),
    ("Ag (cm2)", "ag_cm2"),
    ("Ix (cm4)", "ix_cm4"),
    ("rx (cm)", "rx_cm"),
    ("Iy (cm4)", "iy_cm4"),
    ("ry (cm)", "ry_cm"),
    ("J (cm4)", "j_cm4"),
    ("Cw (cm6)", "cw_cm6"),
]

# Soldados não têm coluna própria de d': é sintetizado como d'=h (sem raio de
# concordância, ver Profile.raio_concordancia_mm), então não faz sentido
# editar um "d'" separado aqui.
_COLUNAS_SOLDADO = [c for c in _COLUNAS_LAMINADO if c[1] != "d_linha_mm"]


class _ProfileTableModel(QAbstractTableModel):
    def __init__(self, repo: ProfileRepository, family: ProfileFamily) -> None:
        super().__init__()
        self._repo = repo
        self._family = family
        self._colunas = _COLUNAS_LAMINADO if family == ProfileFamily.LAMINADO else _COLUNAS_SOLDADO
        self._rows: list[Profile] = []
        self.reload()

    def reload(self) -> None:
        self.beginResetModel()
        self._rows = self._repo.list_all(self._family)
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 1 + len(self._colunas)

    def headerData(self, section, orientation, role=Qt.DisplayRole):  # noqa: N802
        if role != Qt.DisplayRole or orientation != Qt.Horizontal:
            return None
        return "Bitola" if section == 0 else self._colunas[section - 1][0]

    def flags(self, index: QModelIndex):
        base = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        return base

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if role not in (Qt.DisplayRole, Qt.EditRole):
            return None
        profile = self._rows[index.row()]
        if index.column() == 0:
            return profile.bitola
        _, campo = self._colunas[index.column() - 1]
        return getattr(profile, campo)

class _ProfileFamilyPanel(QWidget):
    def __init__(self, repo: ProfileRepository, family: ProfileFamily) -> None:
        super().__init__()
        self._repo = repo
        self._family = family
        self._model = _ProfileTableModel(repo, family)

        table = QTableView()
        table.setModel(self._model)
        table.horizontalHeader().setStretchLastSection(True)
        self._table = table

        layout = QVBoxLayout(self)
        layout.addWidget(table)

    def reload(self) -> None:
        self._model.reload()

class CatalogEditor(QWidget):
    """Sub-abas Laminados/Soldados, com dados fixos para consulta."""

    def __init__(self, conn: sqlite3.Connection, db_path: str | Path) -> None:
        super().__init__()
        self._conn = conn
        self._db_path = db_path
        repo = ProfileRepository(conn)

        self._painel_laminados = _ProfileFamilyPanel(repo, ProfileFamily.LAMINADO)
        self._painel_soldados = _ProfileFamilyPanel(repo, ProfileFamily.SOLDADO)

        sub_abas = QTabWidget()
        sub_abas.addTab(self._painel_laminados, "Laminados (W / HP)")
        sub_abas.addTab(self._painel_soldados, "Soldados (CS)")

        layout = QVBoxLayout(self)
        layout.addWidget(sub_abas)
