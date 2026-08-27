"""Geometria paramétrica da seção transversal de um perfil I (W/HP/CS).

Este módulo é a única fonte da geometria: uma função pura,
``build_section_scene``, monta primitivas em milímetros a partir de um
:class:`~app.domain.models.Profile`. Dois renderizadores consomem a mesma
``SectionScene`` sem duplicar nenhuma conta geométrica:

- ``app/ui/section_canvas.py`` — desenha via ``QPainter`` na UI.
- ``app/report/pdf_report.py`` — desenha via ``fpdf2`` no memorial PDF.

A referência visual é o bloco dinâmico do AutoCAD anexado pelo usuário: seção
I com cotas travadas para altura total, espessura da alma ("Wt"), raio de
concordância ("R"), espessura da mesa ("Ft") e largura da mesa ("W"). Optamos
por rotular as cotas com a nomenclatura da NBR 8800 (``d``, ``bf``, ``tf``,
``tw``, ``r``) em vez dos nomes de parâmetro do bloco do AutoCAD, por serem os
símbolos usados no memorial de cálculo — ver README para revisar/ajustar essa
escolha se o objetivo for bater 1:1 com os rótulos do bloco.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import Profile

# Número de segmentos usados para aproximar cada quarto de círculo do raio de
# concordância por uma polyline (renderizadores 2D simples, sem suporte nativo
# a arco em ambos QPainter e fpdf2, então tratamos tudo como polylines/linhas).
_ARC_SEGMENTS = 8


@dataclass(frozen=True)
class Rect:
    """Retângulo em mm, canto inferior-esquerdo (x, y) + largura/altura."""

    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class Polyline:
    """Sequência de pontos (mm) conectados por segmentos de reta."""

    points: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class Dimension:
    """Uma cota linear: dois pontos de referência, linha de cota deslocada e rótulo."""

    p1: tuple[float, float]
    p2: tuple[float, float]
    offset: float
    label: str
    horizontal: bool


@dataclass(frozen=True)
class SectionScene:
    """Toda a geometria (mm) necessária para desenhar a seção cotada.

    ``width_mm``/``height_mm`` descrevem a caixa envolvente (incluindo cotas),
    útil para os renderizadores calcularem a escala de ajuste à área
    disponível (fit-to-widget / fit-to-page).
    """

    profile_bitola: str
    outline: tuple[Polyline, ...]
    dimensions: tuple[Dimension, ...]
    width_mm: float
    height_mm: float


def build_section_scene(profile: Profile) -> SectionScene:
    """Monta a geometria cotada da seção I de ``profile``, em milímetros.

    A seção é centrada na origem (``x=0`` no eixo de simetria vertical,
    ``y=0`` na meia-altura), com ``+y`` apontando para cima.
    """

    d = profile.d_mm
    bf = profile.bf_mm
    tw = profile.tw_mm
    tf = profile.tf_mm
    r = profile.raio_concordancia_mm

    half_d = d / 2
    half_bf = bf / 2
    half_tw = tw / 2
    y_mesa_interna = half_d - tf  # topo da alma / base da mesa superior

    outline_points: list[tuple[float, float]] = []

    # Percorre o contorno em sentido horário a partir do canto superior
    # esquerdo da mesa superior, incluindo os 4 raios de concordância quando
    # r > 0 (perfis laminados). Perfis soldados (r = 0) resultam em cantos
    # vivos, coerente com os scripts originais.
    outline_points.append((-half_bf, half_d))
    outline_points.append((half_bf, half_d))
    outline_points.append((half_bf, y_mesa_interna))
    outline_points.extend(_quarter_arc((half_tw + r, y_mesa_interna - r), r, start_deg=90, end_deg=0))
    outline_points.append((half_tw, y_mesa_interna - r))
    outline_points.append((half_tw, -(y_mesa_interna - r)))
    outline_points.extend(_quarter_arc((half_tw + r, -(y_mesa_interna - r)), r, start_deg=180, end_deg=90))
    outline_points.append((half_bf, -y_mesa_interna))
    outline_points.append((half_bf, -half_d))
    outline_points.append((-half_bf, -half_d))
    outline_points.append((-half_bf, -y_mesa_interna))
    outline_points.extend(_quarter_arc((-(half_tw + r), -(y_mesa_interna - r)), r, start_deg=270, end_deg=180))
    outline_points.append((-half_tw, -(y_mesa_interna - r)))
    outline_points.append((-half_tw, y_mesa_interna - r))
    outline_points.extend(_quarter_arc((-(half_tw + r), y_mesa_interna - r), r, start_deg=0, end_deg=-90))
    outline_points.append((-half_bf, y_mesa_interna))
    outline_points.append((-half_bf, half_d))

    outline = (Polyline(points=tuple(outline_points)),)

    margin_bf = bf * 0.35
    margin_d = d * 0.15

    dimensions = (
        # Largura da mesa (bf) — cota horizontal acima da seção.
        Dimension(
            p1=(-half_bf, half_d),
            p2=(half_bf, half_d),
            offset=margin_d,
            label=f"bf = {bf:g} mm",
            horizontal=True,
        ),
        # Altura total (d) — cota vertical à direita da seção.
        Dimension(
            p1=(half_bf, half_d),
            p2=(half_bf, -half_d),
            offset=margin_bf,
            label=f"d = {d:g} mm",
            horizontal=False,
        ),
        # Espessura da mesa (tf) — cota vertical curta, canto superior direito.
        Dimension(
            p1=(half_bf, half_d),
            p2=(half_bf, y_mesa_interna),
            offset=margin_bf * 0.5,
            label=f"tf = {tf:g} mm",
            horizontal=False,
        ),
        # Espessura da alma (tw) — cota horizontal curta, logo abaixo da mesa superior.
        Dimension(
            p1=(-half_tw, y_mesa_interna),
            p2=(half_tw, y_mesa_interna),
            offset=margin_d * 0.6,
            label=f"tw = {tw:g} mm",
            horizontal=True,
        ),
    )

    if r > 0:
        dimensions = dimensions + (
            Dimension(
                p1=(half_tw, y_mesa_interna - r),
                p2=(half_tw + r, y_mesa_interna - r),
                offset=margin_bf * 0.25,
                label=f"r = {r:g} mm",
                horizontal=True,
            ),
        )

    width_mm = bf + 2 * margin_bf
    height_mm = d + 2 * margin_d

    return SectionScene(
        profile_bitola=profile.bitola,
        outline=outline,
        dimensions=dimensions,
        width_mm=width_mm,
        height_mm=height_mm,
    )


def _quarter_arc(
    center: tuple[float, float], radius: float, start_deg: float, end_deg: float
) -> list[tuple[float, float]]:
    """Aproxima um arco de 90° por uma polyline de ``_ARC_SEGMENTS`` trechos.

    Quando ``radius == 0`` (perfis soldados, sem raio de concordância),
    retorna uma lista vazia: o contorno usa o canto vivo (ponto único), sem
    nenhum segmento de arco.
    """

    if radius <= 0:
        return []

    import math

    cx, cy = center
    points: list[tuple[float, float]] = []
    for i in range(1, _ARC_SEGMENTS):
        t = start_deg + (end_deg - start_deg) * (i / _ARC_SEGMENTS)
        angle = math.radians(t)
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return points
