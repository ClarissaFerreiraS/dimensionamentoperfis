"""Formulário de um projeto de dimensionamento: entrada, cálculo, preview e PDF.

Um único :class:`ProjectEditor` é reaproveitado pela janela principal tanto
para "Novo Projeto" (``load_new``) quanto para abrir um projeto existente
(``load_project``) — ver `app/ui/main_window.py`.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.domain.calculations import calcular_pilar
from app.domain.models import DesignResult, LoadCase, Profile, ProfileFamily, SteelType
from app.report.pdf_report import gerar_memorial_pdf
from app.repositories import ProfileRepository, ProjectRepository, SteelTypeRepository
from app.ui.section_canvas import SectionCanvas


def _spinbox(minimum: float, maximum: float, decimals: int, valor: float) -> QDoubleSpinBox:
    box = QDoubleSpinBox()
    box.setRange(minimum, maximum)
    box.setDecimals(decimals)
    box.setValue(valor)
    return box


class ProjectEditor(QWidget):
    """Formulário completo de um projeto: dados de entrada + cálculo + PDF.

    Emite ``project_saved`` após salvar com sucesso, para a janela principal
    atualizar a lista de projetos.
    """

    project_saved = Signal()

    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__()
        self._conn = conn
        self._steel_repo = SteelTypeRepository(conn)
        self._profile_repo = ProfileRepository(conn)
        self._project_repo = ProjectRepository(conn)
        self._current_project_id: int | None = None
        self._current_result: DesignResult | None = None

        self._build_ui()
        self.reload_catalogs()
        self.load_new()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        self.nome_edit = QLineEdit()
        self.autor_edit = QLineEdit()
        self.familia_combo = QComboBox()
        self.familia_combo.addItem("Laminado (W / HP)", ProfileFamily.LAMINADO)
        self.familia_combo.addItem("Soldado (CS)", ProfileFamily.SOLDADO)
        self.familia_combo.currentIndexChanged.connect(self._on_familia_changed)
        self.bitola_combo = QComboBox()
        self.bitola_combo.currentIndexChanged.connect(self._on_bitola_changed)
        self.aco_combo = QComboBox()

        dados_form = QFormLayout()
        dados_form.addRow("Nome do projeto:", self.nome_edit)
        dados_form.addRow("Autor:", self.autor_edit)
        dados_form.addRow("Família:", self.familia_combo)
        dados_form.addRow("Bitola:", self.bitola_combo)
        dados_form.addRow("Tipo de aço:", self.aco_combo)

        self.ncsd_spin = _spinbox(0.0, 1e7, 2, 0.0)
        self.kx_spin = _spinbox(0.0, 10.0, 2, 1.0)
        self.lx_spin = _spinbox(0.0, 1000.0, 3, 1.0)
        self.ky_spin = _spinbox(0.0, 10.0, 2, 1.0)
        self.ly_spin = _spinbox(0.0, 1000.0, 3, 1.0)
        self.kz_spin = _spinbox(0.0, 10.0, 2, 1.0)
        self.lz_spin = _spinbox(0.0, 1000.0, 3, 1.0)
        self.ea_spin = _spinbox(0.0, 1000.0, 1, 200.0)
        self.ga_spin = _spinbox(0.0, 1000.0, 1, 77.0)

        cargas_form = QFormLayout()
        cargas_form.addRow("Nc,Sd (kN):", self.ncsd_spin)
        cargas_form.addRow("Kx / Lx (m):", self._pair(self.kx_spin, self.lx_spin))
        cargas_form.addRow("Ky / Ly (m):", self._pair(self.ky_spin, self.ly_spin))
        cargas_form.addRow("Kz / Lz (m):", self._pair(self.kz_spin, self.lz_spin))
        cargas_form.addRow("Ea (GPa):", self.ea_spin)
        cargas_form.addRow("Ga (GPa):", self.ga_spin)

        self.observacoes_edit = QPlainTextEdit()
        self.observacoes_edit.setPlaceholderText("Observações (opcional)")
        self.observacoes_edit.setMaximumHeight(60)

        botoes = QHBoxLayout()
        btn_calcular = QPushButton("Calcular")
        btn_calcular.clicked.connect(self._on_calcular)
        btn_salvar = QPushButton("Salvar Projeto")
        btn_salvar.clicked.connect(self._on_salvar)
        btn_pdf = QPushButton("Gerar PDF")
        btn_pdf.clicked.connect(self._on_gerar_pdf)
        botoes.addWidget(btn_calcular)
        botoes.addWidget(btn_salvar)
        botoes.addWidget(btn_pdf)
        botoes.addStretch(1)

        entrada_box = QGroupBox("Dados do projeto")
        entrada_layout = QVBoxLayout(entrada_box)
        entrada_layout.addLayout(dados_form)
        entrada_layout.addLayout(cargas_form)
        entrada_layout.addWidget(self.observacoes_edit)
        entrada_layout.addLayout(botoes)

        self.canvas = SectionCanvas()
        preview_box = QGroupBox("Seção transversal")
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.addWidget(self.canvas)

        self.resultado_label = QLabel("Preencha os dados e clique em Calcular.")
        self.resultado_label.setWordWrap(True)
        resultado_box = QGroupBox("Resultado")
        resultado_layout = QVBoxLayout(resultado_box)
        resultado_layout.addWidget(self.resultado_label)

        direita = QSplitter()
        direita.setOrientation(Qt.Vertical)
        direita.addWidget(preview_box)
        direita.addWidget(resultado_box)

        splitter = QSplitter()
        splitter.addWidget(entrada_box)
        splitter.addWidget(direita)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout = QVBoxLayout(self)
        layout.addWidget(splitter)

    @staticmethod
    def _pair(a: QWidget, b: QWidget) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.addWidget(a)
        layout.addWidget(b)
        return layout

    # ------------------------------------------------------------- estado
    def reload_catalogs(self) -> None:
        self.aco_combo.clear()
        for steel in self._steel_repo.list_all():
            self.aco_combo.addItem(steel.designacao, steel.designacao)
        self._reload_bitolas()

    def _reload_bitolas(self, bitola_selecionada: str | None = None) -> None:
        family = self.familia_combo.currentData()
        self.bitola_combo.blockSignals(True)
        self.bitola_combo.clear()
        for profile in self._profile_repo.list_all(family):
            self.bitola_combo.addItem(profile.bitola, profile.bitola)
        self.bitola_combo.blockSignals(False)
        if bitola_selecionada is not None:
            idx = self.bitola_combo.findData(bitola_selecionada)
            if idx >= 0:
                self.bitola_combo.setCurrentIndex(idx)
        self._on_bitola_changed()

    def _on_familia_changed(self) -> None:
        self._reload_bitolas()

    def _on_bitola_changed(self) -> None:
        self.canvas.set_profile(self._current_profile())

    def _current_profile(self) -> Profile | None:
        bitola = self.bitola_combo.currentData()
        family = self.familia_combo.currentData()
        if bitola is None or family is None:
            return None
        return self._profile_repo.get(bitola, family)

    def _current_steel(self) -> SteelType | None:
        designacao = self.aco_combo.currentData()
        if designacao is None:
            return None
        return self._steel_repo.get(designacao)

    def _build_load_case(self) -> LoadCase:
        return LoadCase(
            ncsd_kn=self.ncsd_spin.value(),
            kx=self.kx_spin.value(),
            lx_m=self.lx_spin.value(),
            ky=self.ky_spin.value(),
            ly_m=self.ly_spin.value(),
            kz=self.kz_spin.value(),
            lz_m=self.lz_spin.value(),
            ea_gpa=self.ea_spin.value(),
            ga_gpa=self.ga_spin.value(),
        )

    # ---------------------------------------------------------- carregar
    def load_new(self) -> None:
        self._current_project_id = None
        self._current_result = None
        self.nome_edit.setText("")
        self.autor_edit.setText("")
        self.observacoes_edit.setPlainText("")
        self.familia_combo.setCurrentIndex(0)
        self.ncsd_spin.setValue(0.0)
        for spin, valor in (
            (self.kx_spin, 1.0),
            (self.lx_spin, 1.0),
            (self.ky_spin, 1.0),
            (self.ly_spin, 1.0),
            (self.kz_spin, 1.0),
            (self.lz_spin, 1.0),
            (self.ea_spin, 200.0),
            (self.ga_spin, 77.0),
        ):
            spin.setValue(valor)
        self.resultado_label.setText("Preencha os dados e clique em Calcular.")
        self._reload_bitolas()

    def load_project(self, project_id: int) -> None:
        row = self._project_repo.get(project_id)
        if row is None:
            QMessageBox.warning(self, "Projeto não encontrado", "Este projeto pode ter sido excluído.")
            self.load_new()
            return

        self._current_project_id = project_id
        self.nome_edit.setText(row["nome"])
        self.autor_edit.setText(row["autor"] or "")
        self.observacoes_edit.setPlainText(row["observacoes"] or "")

        family = ProfileFamily(row["family"])
        idx = self.familia_combo.findData(family)
        self.familia_combo.setCurrentIndex(max(idx, 0))
        self._reload_bitolas(bitola_selecionada=row["bitola"])

        idx_aco = self.aco_combo.findData(row["steel_designacao"])
        if idx_aco >= 0:
            self.aco_combo.setCurrentIndex(idx_aco)

        loads = ProjectRepository.load_case_from_row(row)
        self.ncsd_spin.setValue(loads.ncsd_kn)
        self.kx_spin.setValue(loads.kx)
        self.lx_spin.setValue(loads.lx_m)
        self.ky_spin.setValue(loads.ky)
        self.ly_spin.setValue(loads.ly_m)
        self.kz_spin.setValue(loads.kz)
        self.lz_spin.setValue(loads.lz_m)
        self.ea_spin.setValue(loads.ea_gpa)
        self.ga_spin.setValue(loads.ga_gpa)

        self._on_calcular()

    # ------------------------------------------------------------ ações
    def _on_calcular(self) -> bool:
        profile = self._current_profile()
        steel = self._current_steel()
        if profile is None or steel is None:
            QMessageBox.warning(self, "Dados incompletos", "Selecione uma bitola e um tipo de aço válidos.")
            return False

        loads = self._build_load_case()
        self._current_result = calcular_pilar(profile, steel, loads)
        self.canvas.set_profile(profile)
        self._atualizar_resultado(profile, steel, self._current_result)
        return True

    def _atualizar_resultado(self, profile: Profile, steel: SteelType, r: DesignResult) -> None:
        veredito = "APROVADO" if r.aprovado else "REPROVADO"
        cor = "green" if r.aprovado else "red"
        texto = (
            f"<b>Perfil:</b> {profile.bitola} ({profile.family.value}) — <b>Aço:</b> {steel.designacao}<br>"
            f"<b>Nc,Rd</b> = {r.nc_rd_kn:.2f} kN &nbsp;&nbsp; <b>Nc,Sd</b> = {r.ncsd_kn:.2f} kN<br>"
            f"Taxa de utilização: {r.taxa_utilizacao * 100:.1f}%<br>"
            f"Esbeltez máxima: {r.esbeltez_max:.2f} (limite {r.limite_esbeltez:.0f})<br>"
            f"χ = {r.chi:.4f} &nbsp;&nbsp; λ0 = {r.lambda0:.4f}<br>"
            f"Flambagem local — mesa: {'sim' if r.ocorre_flamb_mesa else 'não'}, "
            f"alma: {'sim' if r.ocorre_flamb_alma else 'não'}<br>"
            f"Aef = {r.aef_cm2:.2f} cm²<br>"
            f"<span style='color:{cor}; font-size: 14pt;'><b>VEREDITO: {veredito}</b></span>"
        )
        self.resultado_label.setText(texto)

    def _on_salvar(self) -> None:
        nome = self.nome_edit.text().strip()
        if not nome:
            QMessageBox.warning(self, "Nome obrigatório", "Informe um nome para o projeto.")
            return

        profile = self._current_profile()
        steel = self._current_steel()
        if profile is None or steel is None:
            QMessageBox.warning(self, "Dados incompletos", "Selecione uma bitola e um tipo de aço válidos.")
            return

        loads = self._build_load_case()
        autor = self.autor_edit.text().strip() or None
        observacoes = self.observacoes_edit.toPlainText().strip() or None

        if self._current_project_id is None:
            self._current_project_id = self._project_repo.create(
                nome=nome,
                autor=autor,
                family=profile.family,
                bitola=profile.bitola,
                steel_designacao=steel.designacao,
                loads=loads,
                observacoes=observacoes,
            )
        else:
            self._project_repo.update(
                project_id=self._current_project_id,
                nome=nome,
                autor=autor,
                family=profile.family,
                bitola=profile.bitola,
                steel_designacao=steel.designacao,
                loads=loads,
                observacoes=observacoes,
            )

        self.project_saved.emit()
        QMessageBox.information(self, "Projeto salvo", f"Projeto '{nome}' salvo com sucesso.")

    def _on_gerar_pdf(self) -> None:
        if not self._on_calcular():
            return

        profile = self._current_profile()
        steel = self._current_steel()
        loads = self._build_load_case()
        assert profile is not None and steel is not None and self._current_result is not None

        pasta = QFileDialog.getExistingDirectory(self, "Escolha a pasta para salvar o PDF")
        if not pasta:
            return

        autor = self.autor_edit.text().strip() or None
        try:
            caminho: Path = gerar_memorial_pdf(
                profile=profile,
                steel=steel,
                loads=loads,
                result=self._current_result,
                autor=autor,
                output_dir=pasta,
            )
        except Exception as exc:  # noqa: BLE001 — reportado ao usuário, não é fatal para o app
            QMessageBox.critical(self, "Erro ao gerar PDF", str(exc))
            return

        QMessageBox.information(self, "PDF gerado", f"Memorial salvo em:\n{caminho}")
