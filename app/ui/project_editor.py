"""Formulário de um projeto de dimensionamento: entrada, cálculo, preview e PDF.

Um único :class:`ProjectEditor` é reaproveitado pela janela principal tanto
para "Novo Projeto" (``load_new``) quanto para abrir um projeto existente
(``load_project``) — ver `app/ui/main_window.py`.
"""

from __future__ import annotations

import sqlite3
import html
import re
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.domain.calculations import calcular_pilar
from app.domain.models import DesignResult, LoadCase, Profile, ProfileFamily, SteelType
from app.report.pdf_report import gerar_memorial_pdf
from app.repositories import ProfileRepository, ProjectRepository, SteelTypeRepository
from app.ui import theme
from app.ui.section_canvas import SectionCanvas

_MSG_INICIAL = "Preencha os dados e clique em <b>CALCULAR</b>."
_MSG_ALTERADO = "Dados alterados — clique em <b>CALCULAR</b> para atualizar o resultado."


def _chave_bitola(bitola: str) -> tuple[str, tuple[tuple[int, float | str], ...]]:
    """Ordena bitolas por família textual e dimensões numéricas."""
    partes: list[tuple[int, float | str]] = []
    for parte in re.split(r"(\d+(?:[.,]\d+)?)", bitola):
        if not parte:
            continue
        if re.fullmatch(r"\d+(?:[.,]\d+)?", parte):
            partes.append((0, float(parte.replace(",", "."))))
        else:
            partes.append((1, parte.lower()))
    familia = bitola.split(maxsplit=1)[0].lower()
    return familia, tuple(partes)


def _spinbox(minimum: float, maximum: float, decimals: int, valor: float, sufixo: str = "") -> QDoubleSpinBox:
    box = QDoubleSpinBox()
    box.setRange(minimum, maximum)
    box.setDecimals(decimals)
    box.setValue(valor)
    box.setSuffix(sufixo)
    box.setButtonSymbols(QDoubleSpinBox.NoButtons)
    box.setAlignment(Qt.AlignRight)
    box.setMinimumWidth(70)
    return box


def _label(texto: str, nome: str = "muted") -> QLabel:
    label = QLabel(texto)
    label.setObjectName(nome)
    return label


class ProjectEditor(QWidget):
    """Formulário completo de um projeto: dados de entrada + cálculo + PDF.

    Emite ``project_saved`` após salvar com sucesso, para a janela principal
    atualizar a lista de projetos. :meth:`salvar` e :meth:`gerar_pdf` são
    públicos porque a barra de ferramentas da janela principal os aciona.
    """

    project_saved = Signal()
    profile_changed = Signal(object)
    """Perfil selecionado (``Profile``) ou ``None``; alimenta a aba Detalhes do Perfil."""
    details_requested = Signal()

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
        coluna_entrada = QVBoxLayout()
        coluna_entrada.addWidget(self._build_projeto_box())
        coluna_entrada.addWidget(self._build_perfil_box(), 1)

        coluna_calculo = QVBoxLayout()
        coluna_calculo.addWidget(self._build_carga_box())
        coluna_calculo.addWidget(self._build_resultado_box(), 1)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 0, 0)
        layout.setSpacing(12)
        layout.addLayout(coluna_entrada, 1)
        layout.addLayout(coluna_calculo, 1)

    def _build_projeto_box(self) -> QGroupBox:
        self.nome_edit = QLineEdit()
        self.nome_edit.setPlaceholderText("Ex.: Pilar P1 — Térreo")
        self.autor_edit = QLineEdit()
        self.autor_edit.setPlaceholderText("Responsável técnico")
        self.aco_combo = QComboBox()
        theme.configure_combo(self.aco_combo)
        self.aco_combo.currentIndexChanged.connect(self._on_aco_changed)
        self.ea_spin = _spinbox(1.0, 1000.0, 1, 200.0, " GPa")
        self.ga_spin = _spinbox(1.0, 1000.0, 1, 77.0, " GPa")
        self.ea_spin.setMinimumWidth(85)
        self.ga_spin.setMinimumWidth(85)
        self.fy_label = _label("—", "value")
        label_ea = _label("Eₐ", "materialProperty")
        label_ga = _label("Gₐ", "materialProperty")

        props = QHBoxLayout()
        props.addWidget(label_ea)
        props.addWidget(self.ea_spin)
        props.addStretch(1)
        props.addWidget(label_ga)
        props.addWidget(self.ga_spin)
        props.addStretch(1)
        props.addWidget(_label("fy"))
        props.addWidget(self.fy_label)

        form = QFormLayout()
        form.addRow("Nome do projeto:", self.nome_edit)
        form.addRow("Autor:", self.autor_edit)
        form.addRow("Tipo de aço:", self.aco_combo)
        # Linha inteira (sem coluna de rótulo) para não somar a largura do form.
        form.addRow(props)

        box = QGroupBox("Projeto e Aço")
        box.setLayout(form)
        return box

    def _build_perfil_box(self) -> QGroupBox:
        self.familia_combo = QComboBox()
        theme.configure_combo(self.familia_combo)
        self.familia_combo.addItem("Laminado (W / HP)", ProfileFamily.LAMINADO)
        self.familia_combo.addItem("Soldado (CS)", ProfileFamily.SOLDADO)
        self.familia_combo.currentIndexChanged.connect(self._on_familia_changed)
        self.bitola_combo = QComboBox()
        theme.configure_combo(self.bitola_combo, allow_scroll=True)
        self.bitola_combo.currentIndexChanged.connect(self._on_bitola_changed)

        form = QFormLayout()
        form.addRow("Família:", self.familia_combo)
        form.addRow("Bitola:", self.bitola_combo)

        self.canvas = SectionCanvas(
            max_scale=1.05,
            fixed_size=False,
            vertical_shift=0,
            target_height_px=260,
        )

        btn_detalhes = QPushButton("Ver detalhes do perfil  ›")
        btn_detalhes.setObjectName("link")
        btn_detalhes.setCursor(Qt.PointingHandCursor)
        btn_detalhes.clicked.connect(self.details_requested)
        rodape = QHBoxLayout()
        rodape.addStretch(1)
        rodape.addWidget(btn_detalhes)

        box = QGroupBox("Perfil Selecionado")
        layout = QVBoxLayout(box)
        layout.addLayout(form)
        layout.addWidget(self.canvas, 1)
        layout.addLayout(rodape)
        return box

    def _build_carga_box(self) -> QGroupBox:
        self.ncrd_label = _label("—", "ncrd")
        self.ncsd_spin = _spinbox(0.0, 1e7, 2, 0.0)
        self.ncsd_spin.setMinimumWidth(100)

        # Legenda em cima e valor embaixo: mantém a coluna estreita mesmo
        # com os nomes completos das forças.
        header = QFrame()
        header.setObjectName("loadHeader")
        header_layout = QGridLayout(header)
        header_layout.setContentsMargins(10, 6, 10, 6)
        header_layout.setVerticalSpacing(2)
        header_layout.addWidget(_label("Força resistente, Nc,Rd (kN)"), 0, 0)
        header_layout.addWidget(self.ncrd_label, 1, 0, Qt.AlignLeft)
        header_layout.addWidget(_label("Solicitante, Nc,Sd (kN)"), 0, 1, Qt.AlignRight)
        header_layout.addWidget(self.ncsd_spin, 1, 1, Qt.AlignRight)

        # K e L nunca podem ser zero: entram no denominador da esbeltez e de Ne.
        self.lx_spin = _spinbox(0.01, 1000.0, 2, 1.0)
        self.kx_spin = _spinbox(0.01, 10.0, 2, 1.0)
        self.ly_spin = _spinbox(0.01, 1000.0, 2, 1.0)
        self.ky_spin = _spinbox(0.01, 10.0, 2, 1.0)
        self.lz_spin = _spinbox(0.01, 1000.0, 2, 1.0)
        self.kz_spin = _spinbox(0.01, 10.0, 2, 1.0)
        self.rx_label = _label("—", "value")
        self.ry_label = _label("—", "value")
        self.j_label = _label("—", "value")
        self.r0_label = _label("—", "value")

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        linhas = (
            ("Eixo x", "Lx (m):", self.lx_spin, "Kx:", self.kx_spin, "rx:", self.rx_label),
            ("Eixo y", "Ly (m):", self.ly_spin, "Ky:", self.ky_spin, "ry:", self.ry_label),
            ("Eixo z", "Lz (m):", self.lz_spin, "Kz:", self.kz_spin, "J:", self.j_label),
        )
        for i, (eixo, l_txt, l_spin, k_txt, k_spin, p_txt, p_label) in enumerate(linhas):
            grid.addWidget(QLabel(eixo), i, 0)
            grid.addWidget(_label(l_txt), i, 1, Qt.AlignRight)
            grid.addWidget(l_spin, i, 2)
            grid.addWidget(_label(k_txt), i, 3, Qt.AlignRight)
            grid.addWidget(k_spin, i, 4)
            grid.addWidget(_label(p_txt), i, 5, Qt.AlignRight)
            grid.addWidget(p_label, i, 6, Qt.AlignRight)
        # Nc,Rd e r₀ mostram "—" até calcular; reservam a largura de um valor
        # típico para que o cabeçalho não alargue a janela ao preenchê-los.
        for label, exemplo in ((self.ncrd_label, "99999.99"), (self.r0_label, "99.99 cm")):
            label.ensurePolished()
            label.setMinimumWidth(label.fontMetrics().horizontalAdvance(exemplo) + 4)

        grid.addWidget(_label("r₀:"), 3, 5, Qt.AlignRight)
        grid.addWidget(self.r0_label, 3, 6, Qt.AlignRight)
        grid.setColumnMinimumWidth(0, 52)

        btn_calcular = QPushButton("CALCULAR")
        btn_calcular.setObjectName("primary")
        btn_calcular.setCursor(Qt.PointingHandCursor)
        btn_calcular.setShortcut("Ctrl+Return")
        btn_calcular.setToolTip("Calcular (Ctrl+Enter)")
        btn_calcular.clicked.connect(self._on_calcular)

        box = QGroupBox("Dados de Carga e Flambagem Global")
        layout = QVBoxLayout(box)
        layout.setSpacing(10)
        layout.addWidget(header)
        layout.addLayout(grid)
        layout.addWidget(btn_calcular)

        for spin in (
            self.ncsd_spin, self.lx_spin, self.kx_spin, self.ly_spin, self.ky_spin,
            self.lz_spin, self.kz_spin, self.ea_spin, self.ga_spin,
        ):
            spin.valueChanged.connect(self._invalidar_resultado)
        return box

    def _build_resultado_box(self) -> QGroupBox:
        self.resultado_label = QLabel(_MSG_INICIAL)
        self.resultado_label.setObjectName("resultText")
        self.resultado_label.setWordWrap(True)
        self.resultado_label.setTextFormat(Qt.RichText)
        self.resultado_label.setMinimumWidth(0)
        self.resultado_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.resultado_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.resultado_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        btn_pdf = QPushButton("GERAR MEMORIAL PDF")
        btn_pdf.setObjectName("success")
        btn_pdf.setCursor(Qt.PointingHandCursor)
        btn_pdf.clicked.connect(self.gerar_pdf)
        rodape = QHBoxLayout()
        rodape.addStretch(1)
        rodape.addWidget(btn_pdf)

        box = QGroupBox("Resultado")
        box.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        layout = QVBoxLayout(box)
        layout.setSpacing(4)
        layout.addWidget(self.resultado_label, 1)
        layout.addSpacing(6)
        layout.addLayout(rodape)
        return box

    # ------------------------------------------------------------- estado
    @property
    def project_id(self) -> int | None:
        """Id do projeto aberto no editor (``None`` para um projeto ainda não salvo)."""
        return self._current_project_id

    def reload_catalogs(self) -> None:
        self.aco_combo.clear()
        for steel in self._steel_repo.list_all():
            self.aco_combo.addItem(steel.designacao, steel.designacao)
        self._reload_bitolas()

    def _reload_bitolas(self, bitola_selecionada: str | None = None) -> None:
        family = self.familia_combo.currentData()
        self.bitola_combo.blockSignals(True)
        self.bitola_combo.clear()
        profiles = sorted(self._profile_repo.list_all(family), key=lambda profile: _chave_bitola(profile.bitola))
        for profile in profiles:
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
        profile = self._current_profile()
        self.canvas.set_profile(profile)
        self.profile_changed.emit(profile)
        if profile is None:
            for label in (self.rx_label, self.ry_label, self.j_label):
                label.setText("—")
        else:
            self.rx_label.setText(f"{profile.rx_cm:.2f} cm")
            self.ry_label.setText(f"{profile.ry_cm:.2f} cm")
            self.j_label.setText(f"{profile.j_cm4:.2f} cm⁴")
        self._invalidar_resultado()

    def _on_aco_changed(self) -> None:
        steel = self._current_steel()
        self.fy_label.setText(f"{steel.fy_mpa:.0f} MPa" if steel is not None else "—")
        self._invalidar_resultado()

    def _invalidar_resultado(self) -> None:
        """Descarta um resultado já exibido quando qualquer entrada muda.

        Evita que a tela mostre um RESULTADO que não corresponde mais aos dados.
        """
        if self._current_result is None:
            return
        self._current_result = None
        self._limpar_resultado(_MSG_ALTERADO)

    def _limpar_resultado(self, mensagem: str) -> None:
        self.ncrd_label.setText("—")
        self.r0_label.setText("—")
        self.resultado_label.setText(mensagem)

    @property
    def profile(self) -> Profile | None:
        """Perfil atualmente selecionado nos combos de família/bitola."""
        return self._current_profile()

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
        self._reload_bitolas()
        self._current_result = None
        self._limpar_resultado(_MSG_INICIAL)

    def load_project(self, project_id: int) -> None:
        row = self._project_repo.get(project_id)
        if row is None:
            QMessageBox.warning(self, "Projeto não encontrado", "Este projeto pode ter sido excluído.")
            self.load_new()
            return

        self._current_project_id = project_id
        self.nome_edit.setText(row["nome"])
        self.autor_edit.setText(row["autor"] or "")

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
        muted = theme.TEXT_MUTED
        section_color = theme.TEXT_SECTION
        comparacao_resistencia = "Nc,Sd ≤ Nc,Rd" if r.atende_resistencia else "Nc,Sd > Nc,Rd"
        estado_resistencia = (
            "ATENDE AO DIMENSIONAMENTO"
            if r.atende_resistencia
            else "NÃO ATENDE AO DIMENSIONAMENTO"
        )
        estado_esbeltez = "ATENDE" if r.atende_esbeltez else "NÃO ATENDE"
        cor_resistencia = theme.SUCCESS if r.atende_resistencia else theme.DANGER
        cor_esbeltez = theme.SUCCESS if r.atende_esbeltez else theme.DANGER
        self.resultado_label.setText(
            "<div style='font-size: 12pt;'>"
            f"<div><b>Perfil:</b> {html.escape(profile.bitola)} ({profile.family.value})</div>"
            f"<div><b>Aço:</b> {html.escape(steel.designacao)}</div>"
            f"<p style='color:{section_color}; margin: 10px 0 3px 0; font-weight: 600;'>Cargas críticas de Instabilidade</p>"
            "<table width='100%' cellspacing='0' cellpadding='3'>"
            f"<tr><td width='50%'>Nex (flexão X): <b>{r.nex_kn:.2f} kN</b></td>"
            f"<td width='50%'>Ney (flexão Y): <b>{r.ney_kn:.2f} kN</b></td></tr>"
            f"<tr><td>Nez (torção): <b>{r.nez_kn:.2f} kN</b></td>"
            f"<td>Ne,min: <b>{r.ne_min_kn:.2f} kN</b></td></tr>"
            "</table>"
            f"<p style='color:{section_color}; margin: 10px 0 3px 0; font-weight: 600;'>Índice de Esbeltez e fator de redução</p>"
            f"<div>χ / λ₀: <b>{r.chi:.4f} / {r.lambda0:.4f}</b></div>"
            f"<p style='color:{section_color}; margin: 10px 0 3px 0; font-weight: 600;'>Flambagem Local</p>"
            f"<div>Mesa: {'ocorre flambagem' if r.ocorre_flamb_mesa else 'não ocorre flambagem'}</div>"
            f"<div>Alma: {'ocorre flambagem' if r.ocorre_flamb_alma else 'não ocorre flambagem'}</div>"
            f"<p style='color:{section_color}; margin: 10px 0 3px 0; font-weight: 600;'>Resistência à compressão</p>"
            "<table width='100%' cellspacing='0' cellpadding='3'>"
            f"<tr><td width='50%'>Nc,Rd: <b>{r.nc_rd_kn:.2f} kN</b></td>"
            f"<td width='50%'>Nc,Sd: <b>{r.ncsd_kn:.2f} kN</b></td></tr>"
            "</table>"
            f"<p style='margin: 10px 0 0 0; white-space: nowrap;'><nobr><b>Verificação:</b> "
            f"<span style='color:{cor_resistencia};'>{estado_resistencia}</span> "
            f"<span style='color:{muted};'>({comparacao_resistencia})</span></nobr></p>"
            f"<p style='margin: 5px 0 0 0; white-space: nowrap;'><nobr><b>Limite de esbeltez:</b> "
            f"<span style='color:{cor_esbeltez};'>{estado_esbeltez} AO LIMITE</span> "
            f"<span style='color:{muted};'>(esbeltez máxima: {r.esbeltez_max:.2f}; "
            f"limite: {r.limite_esbeltez:.0f})</span></nobr></p>"
            "</div>"
        )
        self.ncrd_label.setText(f"{r.nc_rd_kn:.2f}")
        self.r0_label.setText(f"{r.r0_cm:.2f} cm")

    def salvar(self) -> None:
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

        if self._current_project_id is None:
            self._current_project_id = self._project_repo.create(
                nome=nome,
                autor=autor,
                family=profile.family,
                bitola=profile.bitola,
                steel_designacao=steel.designacao,
                loads=loads,
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
            )

        self.project_saved.emit()
        QMessageBox.information(self, "Projeto salvo", f"Projeto '{nome}' salvo com sucesso.")

    def gerar_pdf(self) -> None:
        if not self._on_calcular():
            return

        profile = self._current_profile()
        steel = self._current_steel()
        loads = self._build_load_case()
        assert profile is not None and steel is not None and self._current_result is not None

        pasta_downloads = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
        if not pasta_downloads:
            QMessageBox.critical(self, "Erro ao gerar PDF", "Não foi possível localizar a pasta Downloads.")
            return

        autor = self.autor_edit.text().strip() or None
        try:
            caminho: Path = gerar_memorial_pdf(
                profile=profile,
                steel=steel,
                loads=loads,
                result=self._current_result,
                autor=autor,
                output_dir=pasta_downloads,
            )
        except Exception as exc:  # noqa: BLE001 — reportado ao usuário, não é fatal para o app
            QMessageBox.critical(self, "Erro ao gerar PDF", str(exc))
            return

        QMessageBox.information(self, "PDF gerado", f"Memorial salvo em:\n{caminho}")
