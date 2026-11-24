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

import math
from dataclasses import dataclass

from app.domain.models import Profile, ProfileFamily

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
    """Uma cota linear: dois pontos de referência, linha de cota deslocada e rótulo.

    ``label_t`` é a posição paramétrica (0..1, de ``p1`` a ``p2``) onde o
    rótulo é ancorado ao longo da linha de cota — o padrão (``0.5``) é o meio
    da linha. Cotas paralelas "empilhadas" (mesmo par de extremos, offsets
    diferentes, como ``d'``/``y``, ``h`` e ``d``) usam valores diferentes de
    ``label_t`` para espalhar os rótulos ao longo da altura em vez de
    concentrá-los todos na mesma posição — evita que, em escalas pequenas
    (ex.: caixa de desenho fixa do PDF), os textos se sobreponham mesmo que
    as linhas de cota estejam em offsets distintos.

    O sinal de ``offset`` define de que lado da peça a cota fica, e os
    renderizadores põem o rótulo do lado de fora: ``offset < 0`` coloca uma
    cota vertical à esquerda (rótulo à esquerda da linha) e uma horizontal
    abaixo (rótulo abaixo da linha).
    """

    p1: tuple[float, float]
    p2: tuple[float, float]
    offset: float
    label: str
    horizontal: bool
    label_t: float = 0.5
    label_offset: float = 0.0
    label_inside: bool = False


@dataclass(frozen=True)
class Circle:
    """Um círculo (mm): centro, raio e se deve ser desenhado tracejado.

    Usado para o detalhe de solda mesa/alma (``ec``) dos perfis soldados: um
    círculo tracejado marca a região de interesse na seção e um círculo
    sólido representa a vista ampliada ("zoom") ao lado.
    """

    center: tuple[float, float]
    radius: float
    dashed: bool = False


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
    circles: tuple[Circle, ...] = ()


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
    outline_points.extend(_quarter_arc((half_tw + r, y_mesa_interna - r), r, start_deg=90, end_deg=180))
    outline_points.append((half_tw, y_mesa_interna - r))
    outline_points.append((half_tw, -(y_mesa_interna - r)))
    outline_points.extend(_quarter_arc((half_tw + r, -(y_mesa_interna - r)), r, start_deg=180, end_deg=270))
    outline_points.append((half_bf, -y_mesa_interna))
    outline_points.append((half_bf, -half_d))
    outline_points.append((-half_bf, -half_d))
    outline_points.append((-half_bf, -y_mesa_interna))
    outline_points.extend(_quarter_arc((-(half_tw + r), -(y_mesa_interna - r)), r, start_deg=270, end_deg=360))
    outline_points.append((-half_tw, -(y_mesa_interna - r)))
    outline_points.append((-half_tw, y_mesa_interna - r))
    outline_points.extend(_quarter_arc((-(half_tw + r), y_mesa_interna - r), r, start_deg=0, end_deg=90))
    outline_points.append((-half_bf, y_mesa_interna))
    outline_points.append((-half_bf, half_d))

    outline = (Polyline(points=tuple(outline_points)),)

    margin_bf = bf * 0.35
    margin_d = d * 0.15
    offset_d = margin_bf * 1.8

    dimensions = (
        # Largura da mesa (bf) — cota horizontal abaixo da seção.
        Dimension(
            p1=(-half_bf, -half_d),
            p2=(half_bf, -half_d),
            offset=-margin_d,
            label=f"bf = {bf:g} mm",
            horizontal=True,
        ),
        # As cotas seguem a referência visual: bf embaixo, tw em cima,
        # h/tf à esquerda e d/d' à direita da seção.
        #
        # Altura total (d) — cota vertical à direita da seção.
        Dimension(
            p1=(half_bf, half_d),
            p2=(half_bf, -half_d),
            offset=offset_d,
            label=f"d = {d:g} mm",
            horizontal=False,
        ),
        # Espessura das mesas (tf) — cotas curtas alinhadas à cota h.
        Dimension(
            p1=(-half_bf, half_d),
            p2=(-half_bf, y_mesa_interna),
            offset=-margin_bf * 0.8,
            label=f"tf = {tf:g} mm",
            horizontal=False,
        ),
        Dimension(
            p1=(-half_bf, -half_d),
            p2=(-half_bf, -y_mesa_interna),
            offset=-margin_bf * 0.8,
            label=f"tf = {tf:g} mm",
            horizontal=False,
        ),
        # Espessura da alma (tw) — cota horizontal curta, acima da seção.
        Dimension(
            p1=(-half_tw, y_mesa_interna),
            p2=(half_tw, y_mesa_interna),
            offset=tf + margin_d * 0.6,
            label=f"tw = {tw:g} mm",
            horizontal=True,
        ),
        # Altura livre entre mesas (h) — cota vertical à esquerda.
        Dimension(
            p1=(-half_bf, y_mesa_interna),
            p2=(-half_bf, -y_mesa_interna),
            offset=-margin_bf * 0.8,
            label=f"h = {profile.h_mm:g} mm",
            horizontal=False,
        ),
    )

    if r > 0:
        # d' — distância entre os pontos de tangência dos raios de
        # concordância, paralela a d e mais próxima da seção.
        dimensions = dimensions + (
            Dimension(
                p1=(half_bf, y_mesa_interna - r),
                p2=(half_bf, -(y_mesa_interna - r)),
                offset=-margin_bf * 0.65,
                label=f"d' = {profile.d_linha_mm:g} mm",
                horizontal=False,
                label_t=0.65,
                label_inside=True,
            ),
            # Cota vertical (não horizontal): o vão livre entre o fim do
            # raio de concordância (half_tw + r) e a borda da mesa (half_bf)
            # não tem nenhuma outra cota nele — as de h e d' ficam à direita
            # de half_bf. Colocando a linha de cota do
            # "r" no meio desse vão, o rótulo fica em espaço livre, sem
            # disputar posição com a alma (à esquerda) nem com a pilha de
            # cotas verticais (à direita). Uma cota horizontal aqui não
            # funciona: o vão do raio (só 10 mm em escala de cena) é curto
            # demais para deslocar o rótulo para longe da alma central,
            # dado que o texto tem tamanho fixo e a escala de ajuste à
            # caixa do PDF é muito pequena para perfis altos e estreitos.
        )

    circles: tuple[Circle, ...] = ()

    if profile.family == ProfileFamily.SOLDADO:
        if profile.ec_mm > 0:
            weld = min(profile.ec_mm, tf, tw)
            topo = y_mesa_interna
            juntas = (
                ((-half_tw - weld, topo - weld), 0, 90),
                ((half_tw + weld, topo - weld), 180, 90),
                ((-half_tw - weld, -topo + weld), 0, -90),
                ((half_tw + weld, -topo + weld), 180, 270),
            )
            outline += tuple(
                Polyline(
                    points=(
                        (
                            center[0] + weld * math.cos(math.radians(start)),
                            center[1] + weld * math.sin(math.radians(start)),
                        ),
                        *_quarter_arc(center, weld, start, end),
                        (
                            center[0] + weld * math.cos(math.radians(end)),
                            center[1] + weld * math.sin(math.radians(end)),
                        ),
                    )
                )
                for center, start, end in juntas
            )

    width_mm = bf + 2 * max(margin_bf, offset_d)
    height_mm = d + 2 * margin_d

    for circle in circles:
        meia_largura_necessaria = abs(circle.center[0]) + circle.radius + margin_bf * 0.15
        meia_altura_necessaria = abs(circle.center[1]) + circle.radius + margin_d * 0.15
        width_mm = max(width_mm, 2 * meia_largura_necessaria)
        height_mm = max(height_mm, 2 * meia_altura_necessaria)

    return SectionScene(
        profile_bitola=profile.bitola,
        outline=outline,
        dimensions=dimensions,
        width_mm=width_mm,
        height_mm=height_mm,
        circles=circles,
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

    cx, cy = center
    points: list[tuple[float, float]] = []
    for i in range(1, _ARC_SEGMENTS):
        t = start_deg + (end_deg - start_deg) * (i / _ARC_SEGMENTS)
        angle = math.radians(t)
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return points
