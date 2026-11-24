"""Painel com as dimensões e propriedades geométricas do perfil selecionado.

Cada linha mostra símbolo, descrição e valor. Passar o mouse sobre uma linha
de dimensão emite ``hovered`` com o símbolo, que o ``SectionCanvas`` usa para
destacar a cota correspondente no desenho.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.domain.models import Profile, ProfileFamily

# (símbolo, descrição, unidade, extrator). Os símbolos coincidem com o início
# dos rótulos das cotas em `app/domain/drawing.py` ("bf = ...", "d' = ...").
_DIMENSOES = (
    ("d", "Altura total da seção", "mm", lambda p: p.d_mm),
    ("bf", "Largura da mesa", "mm", lambda p: p.bf_mm),
    ("tw", "Espessura da alma", "mm", lambda p: p.tw_mm),
    ("tf", "Espessura da mesa", "mm", lambda p: p.tf_mm),
    ("h", "Altura interna entre as faces das mesas", "mm", lambda p: p.h_mm),
    ("d'", "Altura da parte plana da alma (sem os raios)", "mm", lambda p: p.d_linha_mm),
)
_RAIO = ("r", "Raio de concordância mesa/alma", "mm", lambda p: p.raio_concordancia_mm)
_DESCRICAO_D_LINHA = _DIMENSOES[-1]
_SOLDA = ("ec", "Dimensão do detalhe da solda mesa/alma", "mm", lambda p: p.ec_mm)

_PROPRIEDADES = (
    ("Ag", "Área bruta da seção", "cm²", lambda p: p.ag_cm2),
    ("Ix", "Momento de inércia em relação ao eixo x", "cm⁴", lambda p: p.ix_cm4),
    ("Iy", "Momento de inércia em relação ao eixo y", "cm⁴", lambda p: p.iy_cm4),
    ("rx", "Raio de giração em relação ao eixo x", "cm", lambda p: p.rx_cm),
    ("ry", "Raio de giração em relação ao eixo y", "cm", lambda p: p.ry_cm),
    ("J", "Constante de torção", "cm⁴", lambda p: p.j_cm4),
    ("Cw", "Constante de empenamento", "cm⁶", lambda p: p.cw_cm6),
)


class _Linha(QFrame):
    """Uma linha símbolo/descrição/valor que avisa quando o mouse entra ou sai."""

    def __init__(self, simbolo: str, descricao: str, valor: str, on_hover) -> None:
        super().__init__()
        self.setObjectName("propRow")
        self.setAttribute(Qt.WA_Hover)
        self._simbolo = simbolo
        self._on_hover = on_hover

        rotulo = QLabel(f"<b>{simbolo}</b>")
        rotulo.setMinimumWidth(30)
        desc = QLabel(descricao)
        desc.setObjectName("muted")
        valor_label = QLabel(valor)
        valor_label.setObjectName("value")
        valor_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.addWidget(rotulo)
        layout.addWidget(desc, 1)
        layout.addWidget(valor_label)

    def enterEvent(self, event) -> None:  # noqa: N802 (nome exigido pelo Qt)
        self._on_hover(self._simbolo)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 (nome exigido pelo Qt)
        self._on_hover(None)
        super().leaveEvent(event)


class ProfilePropertiesPanel(QWidget):
    """Listas Dimensões e Propriedades do perfil. Atualize com :meth:`set_profile`."""

    hovered = Signal(object)
    """Símbolo da dimensão sob o mouse (``str``) ou ``None`` ao sair."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._secoes = QVBoxLayout(self)
        self._secoes.setContentsMargins(0, 0, 0, 0)
        self._secoes.setSpacing(16)
        self.set_profile(None)

    def set_profile(self, profile: Profile | None) -> None:
        while (item := self._secoes.takeAt(0)) is not None:
            if (widget := item.widget()) is not None:
                # setParent(None) tira o widget da tela já; deleteLater só age no próximo ciclo.
                widget.setParent(None)
                widget.deleteLater()

        if profile is None:
            vazio = QLabel("Selecione uma bitola para ver os dados do perfil.")
            vazio.setObjectName("muted")
            self._secoes.addWidget(vazio)
            return

        # Só entram em "Dimensões" as grandezas que têm cota no desenho; as demais
        # ficam em "Propriedades geométricas", sem destaque.
        if profile.family == ProfileFamily.LAMINADO:
            dimensoes = _DIMENSOES
            adicionais = (_RAIO,)
        else:
            dimensoes = tuple(d for d in _DIMENSOES if d[0] != "d'")
            adicionais = (_DESCRICAO_D_LINHA, _SOLDA)
        self._secoes.addWidget(self._secao("Dimensões", dimensoes, profile, destacavel=True))
        self._secoes.addWidget(
            self._secao("Propriedades geométricas", (*_PROPRIEDADES, *adicionais), profile, destacavel=False)
        )
        self._secoes.addStretch(1)

    def _secao(self, titulo: str, linhas, profile: Profile, destacavel: bool) -> QWidget:
        secao = QWidget()
        layout = QVBoxLayout(secao)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        cabecalho = QLabel(titulo.upper())
        cabecalho.setObjectName("sectionTitle")
        layout.addWidget(cabecalho)
        on_hover = self.hovered.emit if destacavel else (lambda _simbolo: None)
        for simbolo, descricao, unidade, extrair in linhas:
            layout.addWidget(_Linha(simbolo, descricao, f"{extrair(profile):g} {unidade}", on_hover))
        return secao
