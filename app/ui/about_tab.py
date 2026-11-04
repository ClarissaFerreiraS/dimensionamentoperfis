"""Apresentação educacional e guia inicial do StructDim."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


_PROFILE_IMAGE = Path(__file__).resolve().parent / "assets" / "structdim_perfis_aco.png"


class _HeroPanel(QFrame):
    def __init__(self, image: QPixmap) -> None:
        super().__init__()
        self.setObjectName("aboutHero")
        self.setMinimumHeight(373)
        self._image = image

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        scaled_image = self._image.scaled(
            self.size(),
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
        x = (self.width() - scaled_image.width()) // 2
        y = (self.height() - scaled_image.height()) // 2
        painter.drawPixmap(x, y, scaled_image)

        overlay = QLinearGradient(0, 0, self.width(), 0)
        overlay.setColorAt(0, QColor(255, 255, 255, 220))
        overlay.setColorAt(0.38, QColor(255, 255, 255, 175))
        overlay.setColorAt(0.68, QColor(255, 255, 255, 50))
        overlay.setColorAt(1, QColor(255, 255, 255, 0))
        painter.fillRect(self.rect(), overlay)


class _StepCard(QFrame):
    def __init__(self, number: str, title: str, description: str) -> None:
        super().__init__()
        self.setObjectName("aboutStep")
        self.setMinimumHeight(204)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        marker = QLabel(number)
        marker.setObjectName("aboutStepNumber")
        marker.setAlignment(Qt.AlignCenter)
        marker.setFixedSize(40, 40)
        layout.addWidget(marker, alignment=Qt.AlignLeft)

        heading = QLabel(title)
        heading.setObjectName("aboutStepTitle")
        heading.setWordWrap(True)
        layout.addWidget(heading)

        detail = QLabel(description)
        detail.setObjectName("aboutStepDescription")
        detail.setWordWrap(True)
        layout.addWidget(detail)
        layout.addStretch(1)


class AboutTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("aboutScroll")

        content = QWidget()
        content.setObjectName("aboutContent")
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(38, 30, 38, 28)
        layout.setSpacing(20)

        image = QPixmap(str(_PROFILE_IMAGE))
        if image.isNull():
            raise FileNotFoundError(f"Imagem dos perfis de aço não encontrada: {_PROFILE_IMAGE}")
        hero = _HeroPanel(image)
        hero.setProperty("backgroundImage", str(_PROFILE_IMAGE))
        hero.setToolTip("Estrutura formada por perfis de aço")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(34, 28, 34, 28)
        introduction = QVBoxLayout()
        introduction.setSpacing(12)

        eyebrow = QLabel("APRESENTAÇÃO")
        eyebrow.setObjectName("aboutEyebrow")
        introduction.addWidget(eyebrow)

        title = QLabel("Conheça o StructDim")
        title.setObjectName("aboutTitle")
        title.setWordWrap(True)
        title.setMaximumWidth(590)
        introduction.addWidget(title)

        intro = QLabel(
            "O StructDim é uma ferramenta computacional desenvolvida em Python "
            "para auxiliar no dimensionamento e na verificação de perfis de aço, "
            "conforme os critérios estabelecidos pela ABNT NBR 8800:2024.\n\n"
            "Por meio de uma interface simples, permite inserir os dados do "
            "projeto, selecionar perfis metálicos e acompanhar os resultados "
            "das verificações de dimensionamento, além de gerar um memorial "
            "de cálculo em PDF."
        )
        intro.setObjectName("aboutIntro")
        intro.setWordWrap(True)
        intro.setMaximumWidth(590)
        introduction.addWidget(intro)
        introduction.addStretch(1)
        hero_layout.addLayout(introduction)
        hero_layout.addStretch(1)
        layout.addWidget(hero)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setObjectName("aboutDivider")
        layout.addWidget(divider)

        section_title = QLabel("Como começar")
        section_title.setObjectName("aboutSectionTitle")
        layout.addWidget(section_title)

        steps = QHBoxLayout()
        steps.setSpacing(14)
        for number, title, description in (
            (
                "1",
                "Crie um projeto",
                "Inicie um novo projeto ou abra um dimensionamento salvo "
                "anteriormente.",
            ),
            (
                "2",
                "Informe os parâmetros",
                "Selecione o perfil e o tipo de aço. Informe as solicitações "
                "e os comprimentos de flambagem.",
            ),
            (
                "3",
                "Realize o dimensionamento",
                "Confira os resultados das verificações e, se desejar, gere "
                "o memorial de cálculo em PDF.",
            ),
        ):
            steps.addWidget(_StepCard(number, title, description), 1)
        layout.addLayout(steps)

        footer_panel = QFrame()
        footer_panel.setObjectName("aboutFooter")
        footer = QVBoxLayout(footer_panel)
        footer.setContentsMargins(20, 14, 20, 14)

        note = QLabel(
            "<b>Atenção:</b> ferramenta de finalidade educacional. Os "
            "resultados auxiliam no estudo e não substituem a avaliação de "
            "um profissional habilitado."
        )
        note.setObjectName("aboutNote")
        note.setWordWrap(True)
        footer.addWidget(note)
        layout.addWidget(footer_panel)

        scroll.setWidget(content)
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)
