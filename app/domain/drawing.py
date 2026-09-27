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
class AxisLine:
    """Uma linha de eixo/centro de simetria (mm), rotulada nas duas pontas.

    Usada para o eixo ``X-X`` do desenho: uma linha de centro (tipicamente
    traço-ponto) que atravessa a seção, com o rótulo repetido em cada
    extremidade (notação usual de eixo, ex.: "X ... X").
    """

    p1: tuple[float, float]
    p2: tuple[float, float]
    label: str = "X"


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
    axes: tuple[AxisLine, ...] = ()


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

    dimensions = (
        # Largura da mesa (bf) — cota horizontal acima da seção.
        Dimension(
            p1=(-half_bf, half_d),
            p2=(half_bf, half_d),
            offset=margin_d,
            label=f"bf = {bf:g} mm",
            horizontal=True,
        ),
        # As cotas são distribuídas ao redor da seção (bf em cima, tw embaixo,
        # d/tf à esquerda, h/d'/y à direita) em vez de empilhadas de um lado
        # só, para que os rótulos não disputem o mesmo espaço.
        #
        # Altura total (d) — cota vertical à esquerda da seção.
        Dimension(
            p1=(-half_bf, half_d),
            p2=(-half_bf, -half_d),
            offset=-margin_bf,
            label=f"d = {d:g} mm",
            horizontal=False,
        ),
        # Espessura da mesa (tf) — cota vertical curta, canto superior esquerdo.
        Dimension(
            p1=(-half_bf, half_d),
            p2=(-half_bf, y_mesa_interna),
            offset=-margin_bf * 0.5,
            label=f"tf = {tf:g} mm",
            horizontal=False,
        ),
        # Espessura da alma (tw) — cota horizontal curta, abaixo da seção: as
        # linhas de extensão descem da alma, atravessando a mesa inferior.
        Dimension(
            p1=(-half_tw, -y_mesa_interna),
            p2=(half_tw, -y_mesa_interna),
            offset=-(tf + margin_d * 0.6),
            label=f"tw = {tw:g} mm",
            horizontal=True,
        ),
        # Altura útil da alma (h) — cota vertical, entre as faces internas das
        # mesas. Existe para as duas famílias (para soldados, h = d').
        # Com raio (laminados), label_t=0.15 afasta o rótulo do de "d'", linha
        # paralela empilhada no mesmo lado. Sem raio (soldados), o topo desse
        # lado é ocupado pelo círculo de zoom da solda, então o rótulo desce.
        Dimension(
            p1=(half_bf, y_mesa_interna),
            p2=(half_bf, -y_mesa_interna),
            offset=margin_bf * 0.8,
            label=f"h = {profile.h_mm:g} mm",
            horizontal=False,
            label_t=0.15 if r > 0 else 0.8,
        ),
    )

    if r > 0:
        # d' — distância entre os pontos de tangência dos raios de
        # concordância (só existe para laminados; em soldados d' = h, já
        # coberto pela cota "h" acima).
        dimensions = dimensions + (
            Dimension(
                p1=(half_bf, y_mesa_interna - r),
                p2=(half_bf, -(y_mesa_interna - r)),
                offset=margin_bf * 0.65,
                label=f"d' = {profile.d_linha_mm:g} mm",
                horizontal=False,
                label_t=0.65,
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
            Dimension(
                p1=(half_tw + r, y_mesa_interna),
                p2=(half_tw + r, y_mesa_interna - r),
                offset=(half_bf - (half_tw + r)) / 2,
                label=f"r = {r:g} mm",
                horizontal=False,
            ),
        )

    circles: tuple[Circle, ...] = ()

    if profile.family == ProfileFamily.SOLDADO:
        # y — distância do centro (eixo X-X) até a face externa da mesa
        # (y = d/2), cota típica de perfis soldados. Fica à esquerda, entre
        # "tf" e "d", porque o lado direito já tem "h" e o círculo de zoom
        # do detalhe de solda (ec). label_t=0.6 mantém o rótulo acima do de
        # "d" (no meio da altura) e abaixo do de "tf" (no topo).
        dimensions = dimensions + (
            Dimension(
                p1=(-half_bf, 0.0),
                p2=(-half_bf, half_d),
                offset=-margin_bf * 0.65,
                label=f"y = {half_d:g} mm",
                horizontal=False,
                label_t=0.6,
            ),
        )

        if profile.ec_mm > 0:
            # Detalhe de solda mesa/alma (ec): um círculo tracejado marca o
            # canto real da seção, uma linha de chamada liga esse ponto a um
            # círculo de "zoom" ao lado, onde um esquema do canto (mesa +
            # alma) é redesenhado em escala maior com a cota ec.
            menor_lado = min(bf, d)
            small_r = menor_lado * 0.035
            zoom_r = menor_lado * 0.16
            corner = (half_tw, y_mesa_interna)
            # Multiplicador 1.75: folga horizontal entre a linha de cota "h"
            # (em half_bf + margin_bf*0.8) e a borda esquerda do círculo de
            # zoom — o texto do rótulo tem tamanho fixo em mm de página (não
            # encolhe com a escala de ajuste à caixa do PDF), então uma folga
            # geométrica pequena ainda causa sobreposição visual.
            zoom_center = (half_bf + margin_bf * 1.75, y_mesa_interna * 0.4)

            dx = zoom_center[0] - corner[0]
            dy = zoom_center[1] - corner[1]
            dist = math.hypot(dx, dy) or 1.0
            ux, uy = dx / dist, dy / dist
            leader_p1 = (corner[0] + ux * small_r, corner[1] + uy * small_r)
            leader_p2 = (zoom_center[0] - ux * zoom_r, zoom_center[1] - uy * zoom_r)

            leg = zoom_r * 0.9
            corner_zoom = (zoom_center[0] - leg * 0.35, zoom_center[1] + leg * 0.35)
            perna_alma = (corner_zoom[0], corner_zoom[1] + leg * 0.6)
            perna_mesa = (corner_zoom[0] + leg * 0.6, corner_zoom[1])

            outline = outline + (
                Polyline(points=(leader_p1, leader_p2)),
                Polyline(points=(perna_alma, corner_zoom, perna_mesa)),
            )
            circles = (
                Circle(center=corner, radius=small_r, dashed=True),
                Circle(center=zoom_center, radius=zoom_r, dashed=False),
            )
            dimensions = dimensions + (
                Dimension(
                    p1=corner_zoom,
                    p2=perna_mesa,
                    offset=-leg * 0.22,
                    label=f"ec = {profile.ec_mm:g} mm",
                    horizontal=True,
                ),
            )

    width_mm = bf + 2 * margin_bf
    height_mm = d + 2 * margin_d

    for circle in circles:
        meia_largura_necessaria = abs(circle.center[0]) + circle.radius + margin_bf * 0.15
        meia_altura_necessaria = abs(circle.center[1]) + circle.radius + margin_d * 0.15
        width_mm = max(width_mm, 2 * meia_largura_necessaria)
        height_mm = max(height_mm, 2 * meia_altura_necessaria)

    # Eixo de simetria X-X — atravessa a seção na meia-altura, com o rótulo
    # repetido em cada extremidade (notação usual de eixo). Comum às duas
    # famílias.
    axis_extensao = margin_bf * 0.15
    axes = (
        AxisLine(
            p1=(-half_bf - axis_extensao, 0.0),
            p2=(half_bf + axis_extensao, 0.0),
            label="X",
        ),
    )

    return SectionScene(
        profile_bitola=profile.bitola,
        outline=outline,
        dimensions=dimensions,
        width_mm=width_mm,
        height_mm=height_mm,
        circles=circles,
        axes=axes,
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
