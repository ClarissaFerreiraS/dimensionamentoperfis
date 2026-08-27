"""Aba "Catálogo de Perfis": tabela editável sobre profiles_laminados/soldados.

Cada edição de célula chama diretamente ``ProfileRepository.upsert`` — não há
botão "Salvar" separado, o catálogo é gravado imediatamente, coerente com o
pedido do usuário de "ir atualizando" os dados ao longo do tempo.
"""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.domain.models import Profile, ProfileFamily
from app.importers.excel_importer import import_from_excel
from app.repositories import ProfileRepository

# (cabeçalho exibido, nome do campo em Profile). "Bitola" fica de fora da
# edição inline (é a chave primária da tabela; renomear via edição de célula
# criaria uma linha nova órfã em vez de renomear — ver botão "Novo Perfil").
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
        return base | Qt.ItemIsEditable if index.column() > 0 else base

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if role not in (Qt.DisplayRole, Qt.EditRole):
            return None
        profile = self._rows[index.row()]
        if index.column() == 0:
            return profile.bitola
        _, campo = self._colunas[index.column() - 1]
        return getattr(profile, campo)

    def setData(self, index: QModelIndex, value, role=Qt.EditRole) -> bool:  # noqa: N802
        if role != Qt.EditRole or index.column() == 0:
            return False
        _, campo = self._colunas[index.column() - 1]
        try:
            numero = float(value)
        except (TypeError, ValueError):
            return False
        profile = self._rows[index.row()]
        novo = replace(profile, **{campo: numero})
        self._repo.upsert(novo)
        self._rows[index.row()] = novo
        self.dataChanged.emit(index, index)
        return True

    def profile_at(self, row: int) -> Profile:
        return self._rows[row]


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

        btn_novo = QPushButton("Novo Perfil...")
        btn_novo.clicked.connect(self._on_novo)
        btn_remover = QPushButton("Remover Perfil")
        btn_remover.clicked.connect(self._on_remover)

        botoes = QHBoxLayout()
        botoes.addWidget(btn_novo)
        botoes.addWidget(btn_remover)
        botoes.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(botoes)
        layout.addWidget(table)

    def reload(self) -> None:
        self._model.reload()

    def _on_novo(self) -> None:
        bitola, ok = QInputDialog.getText(self, "Novo Perfil", "Bitola (ex.: W 150 x 13.0):")
        if not ok or not bitola.strip():
            return
        bitola = bitola.strip()
        if self._repo.get(bitola, self._family) is not None:
            QMessageBox.warning(self, "Perfil já existe", f"Já existe um perfil '{bitola}' nesta família.")
            return
        novo = Profile(
            bitola=bitola,
            family=self._family,
            d_mm=0.0,
            bf_mm=0.0,
            tw_mm=0.0,
            tf_mm=0.0,
            h_mm=0.0,
            d_linha_mm=0.0,
            ag_cm2=0.0,
            ix_cm4=0.0,
            rx_cm=0.0,
            iy_cm4=0.0,
            ry_cm=0.0,
            j_cm4=0.0,
            cw_cm6=0.0,
        )
        self._repo.upsert(novo)
        self.reload()

    def _on_remover(self) -> None:
        index = self._table.currentIndex()
        if not index.isValid():
            return
        profile = self._model.profile_at(index.row())
        resposta = QMessageBox.question(
            self, "Remover Perfil", f"Remover o perfil '{profile.bitola}' do catálogo?"
        )
        if resposta == QMessageBox.Yes:
            self._repo.delete(profile.bitola, self._family)
            self.reload()


class CatalogEditor(QWidget):
    """Sub-abas Laminados/Soldados, cada uma com sua tabela + botão de importar Excel."""

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

        btn_importar = QPushButton("Importar do Excel...")
        btn_importar.clicked.connect(self._on_importar)

        layout = QVBoxLayout(self)
        layout.addWidget(btn_importar)
        layout.addWidget(sub_abas)

    def _on_importar(self) -> None:
        caminho, _ = QFileDialog.getOpenFileName(self, "Importar planilha Excel", "", "Planilhas (*.xlsx)")
        if not caminho:
            return
        try:
            counts = import_from_excel(caminho, self._db_path)
        except Exception as exc:  # noqa: BLE001 — reportado ao usuário, não é fatal para o app
            QMessageBox.critical(self, "Erro ao importar", str(exc))
            return
        self._painel_laminados.reload()
        self._painel_soldados.reload()
        resumo = "\n".join(f"{tabela}: {n} linha(s)" for tabela, n in counts.items())
        QMessageBox.information(self, "Importação concluída", resumo)
