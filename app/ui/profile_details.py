"""Aba "Detalhes do Perfil": desenho ampliado + dimensões e propriedades.

Mostra o perfil selecionado no projeto aberto (a janela principal repassa o
sinal ``ProjectEditor.profile_changed`` para :meth:`set_profile`).
"""

from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from app.domain.models import Profile, ProfileFamily
from app.ui.profile_properties import ProfilePropertiesPanel
from app.ui.section_canvas import SectionCanvas

_NOME_FAMILIA = {
    ProfileFamily.LAMINADO: "Perfil laminado (W / HP)",
    ProfileFamily.SOLDADO: "Perfil soldado (CS)",
}


class ProfileDetailsTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._titulo = QLabel()
        self._titulo.setObjectName("pageTitle")
        self._subtitulo = QLabel()
        self._subtitulo.setObjectName("muted")

        self._canvas = SectionCanvas(max_scale=2.1, fixed_size=False, target_height_px=500)
        desenho_box = QGroupBox("Seção transversal")
        desenho_layout = QVBoxLayout(desenho_box)
        desenho_layout.addWidget(self._canvas)

        self._painel = ProfilePropertiesPanel()
        self._painel.hovered.connect(self._canvas.set_highlight)
        dica = QLabel("Passe o mouse sobre uma dimensão para destacá-la no desenho.")
        dica.setObjectName("muted")
        dica.setWordWrap(True)

        dados = QWidget()
        dados_layout = QVBoxLayout(dados)
        dados_layout.addWidget(dica)
        dados_layout.addWidget(self._painel, 1)
        rolagem = QScrollArea()
        rolagem.setWidgetResizable(True)
        rolagem.setFrameShape(QScrollArea.NoFrame)
        rolagem.setWidget(dados)
        dados_box = QGroupBox("Dados do perfil")
        dados_box_layout = QVBoxLayout(dados_box)
        dados_box_layout.addWidget(rolagem)
        dados_box.setMinimumWidth(440)

        corpo = QHBoxLayout()
        corpo.setSpacing(12)
        corpo.addWidget(desenho_box, 3)
        corpo.addWidget(dados_box, 2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.addWidget(self._titulo)
        layout.addWidget(self._subtitulo)
        layout.addSpacing(6)
        layout.addLayout(corpo, 1)

        self.set_profile(None)

    def set_profile(self, profile: Profile | None) -> None:
        if profile is None:
            self._titulo.setText("Nenhum perfil selecionado")
            self._subtitulo.setText("Escolha uma família e uma bitola na aba Projetos.")
        else:
            self._titulo.setText(profile.bitola)
            self._subtitulo.setText(_NOME_FAMILIA[profile.family])
        self._canvas.set_profile(profile)
        self._canvas.set_highlight(None)
        self._painel.set_profile(profile)
