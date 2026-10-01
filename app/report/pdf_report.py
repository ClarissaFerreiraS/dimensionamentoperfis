"""Memorial de cálculo em PDF, evoluído de ``CodigocomPDF.py``.

Mantém os títulos de seção e a redação em português do script original
("1. ESTABILIDADE GLOBAL", "2. VERIFICAÇÃO DO LIMITE DE ESBELTEZ", etc.) e a
convenção de nome de arquivo ``Memorial_Compressao_<bitola>.pdf``, mas:

- Lê os valores de :class:`~app.domain.models.DesignResult` em vez de
  variáveis soltas calculadas inline no script.
- Desenha a seção transversal cotada a partir da mesma
  :func:`~app.domain.drawing.build_section_scene` usada pela UI
  (``app/ui/section_canvas.py``), em vez do retângulo simplificado ad-hoc que
  ``CodigocomPDF.py`` desenhava com ``pdf.rect``.
- Corrige a tabela de geometria: o script original rotulava ``d_mm`` como
  ``'b'`` (resíduo do acesso posicional ``v[2]``/``v[3]``); aqui a tabela usa
  os nomes de campo reais do perfil (``bf``, ``tw``, ``tf``, ``h``, ``d``,
  ``d'``).
"""

from __future__ import annotations

import math
import os
import re
from pathlib import Path

from fpdf import FPDF

from app.domain.drawing import Dimension, Polyline, SectionScene, build_section_scene
from app.domain.models import DesignResult, LoadCase, Profile, ProfileFamily, SteelType

_NORMA_BASE = "ABNT NBR 8800:2024"
_AUTOR_PADRAO = "Autor(a) Responsável"
_FONTE_SIMBOLOS = "ArialSimbolos"
_CAMINHO_FONTE_SIMBOLOS = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "arial.ttf"
_CAMINHO_FONTE_SIMBOLOS_NEGRITO = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "arialbd.ttf"

# Fontes core do fpdf2 (Helvetica/Times/Courier) só codificam latin-1. Texto
# livre digitado pelo usuário (campo "Autor") pode conter pontuação "smart"
# do autocorretor do Windows/Word (traço-en/em, aspas curvas, reticências) ou
# outros caracteres fora desse conjunto, o que fazia `pdf.cell` levantar
# `FPDFUnicodeEncodingException` e o botão "Gerar PDF" falhar com esse erro.
_SUBSTITUICOES_LATIN1 = {
    "–": "-",  # en dash
    "—": "-",  # em dash
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "…": "...",
    " ": " ",  # espaço não separável
}


def _sanitizar_latin1(texto: str) -> str:
    """Normaliza ``texto`` para o conjunto latin-1 aceito pelas fontes core do PDF."""

    for original, substituto in _SUBSTITUICOES_LATIN1.items():
        texto = texto.replace(original, substituto)
    return texto.encode("latin-1", errors="replace").decode("latin-1")


class _RelatorioPDF(FPDF):
    """Página do memorial: cabeçalho com autor/norma, rodapé com nº de página."""

    def __init__(self, autor: str) -> None:
        super().__init__(format="A4")
        self._autor = autor
        self._fonte_simbolos_disponivel = _CAMINHO_FONTE_SIMBOLOS.exists()
        if self._fonte_simbolos_disponivel:
            self.add_font(_FONTE_SIMBOLOS, "", str(_CAMINHO_FONTE_SIMBOLOS), uni=True)
            if _CAMINHO_FONTE_SIMBOLOS_NEGRITO.exists():
                self.add_font(_FONTE_SIMBOLOS, "B", str(_CAMINHO_FONTE_SIMBOLOS_NEGRITO), uni=True)

    def header(self) -> None:
        self.set_font("Helvetica", "B", 11)
        self.set_fill_color(240, 243, 246)
        self.cell(0, 8, "MEMORIAL DE CÁLCULO ESTRUTURAL - COMPRESSÃO PURA", border=1, ln=1, align="C", fill=True)
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, f"Autor(a) responsável: {self._autor}", border="LR", ln=1)
        self.cell(0, 5, f"Norma de referência: {_NORMA_BASE}", border="LRB", ln=1)
        self.ln(3)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Pagina {self.page_no()}", 0, 0, "C")


def _add_secao(pdf: FPDF, titulo: str) -> None:
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(20, 40, 100)
    pdf.cell(0, 5, titulo, border="B", ln=1)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(1)


def _add_linha(pdf: FPDF, texto: str) -> None:
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, texto, ln=1)


def _add_linha_rotulada(pdf: FPDF, rotulo: str, valor: str) -> None:
    fonte = _FONTE_SIMBOLOS if getattr(pdf, "_fonte_simbolos_disponivel", False) else "Helvetica"
    pdf.set_font(fonte, "", 9)
    pdf.cell(0, 5, f"{rotulo} {valor}", ln=1)


def _draw_dashed_line(pdf: FPDF, x1: float, y1: float, x2: float, y2: float, dash: float, gap: float) -> None:
    """Traço tracejado manual (independe de ``FPDF.set_dash_pattern``)."""

    length = math.hypot(x2 - x1, y2 - y1)
    if length <= 0:
        return
    ux = (x2 - x1) / length
    uy = (y2 - y1) / length
    period = dash + gap
    pos = 0.0
    while pos < length:
        fim = min(pos + dash, length)
        pdf.line(x1 + ux * pos, y1 + uy * pos, x1 + ux * fim, y1 + uy * fim)
        pos += period


def _draw_dashed_circle(pdf: FPDF, cx: float, cy: float, radius: float, dash: float, gap: float) -> None:
    """Círculo tracejado manual, aproximado por cordas curtas."""

    if radius <= 0:
        return
    dash_ang = dash / radius
    gap_ang = gap / radius
    period_ang = dash_ang + gap_ang
    if period_ang <= 0:
        return
    two_pi = 2 * math.pi
    ang = 0.0
    while ang < two_pi:
        fim = min(ang + dash_ang, two_pi)
        n = max(int((fim - ang) / 0.2), 1)
        prev_x = cx + radius * math.cos(ang)
        prev_y = cy + radius * math.sin(ang)
        for i in range(1, n + 1):
            a = ang + (fim - ang) * i / n
            x = cx + radius * math.cos(a)
            y = cy + radius * math.sin(a)
            pdf.line(prev_x, prev_y, x, y)
            prev_x, prev_y = x, y
        ang += period_ang


def _draw_section_scene(
    pdf: FPDF,
    scene: SectionScene,
    x0: float,
    y0: float,
    max_w: float,
    max_h: float,
    scale_override: float | None = None,
    align_top: bool = False,
) -> None:
    """Desenha ``scene`` (mm, origem no centro, +y para cima) na página do PDF.

    A caixa de destino é ``(x0, y0)`` até ``(x0+max_w, y0+max_h)`` em mm de
    página. A cena é ajustada (fit) mantendo proporção e centralizada nessa
    caixa; o eixo Y é invertido (PDF cresce para baixo).
    """

    scale_fit = min(max_w / scene.width_mm, max_h / scene.height_mm)
    scale = min(scale_override, scale_fit) if scale_override is not None else scale_fit
    cx = x0 + max_w / 2
    cy = y0 + scene.height_mm * scale / 2 if align_top else y0 + max_h / 2

    def to_page(point: tuple[float, float]) -> tuple[float, float]:
        return (cx + point[0] * scale, cy - point[1] * scale)

    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.3)
    for outline in scene.outline:
        if isinstance(outline, Polyline):
            pts = [to_page(p) for p in outline.points]
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                pdf.line(x1, y1, x2, y2)

    pdf.set_draw_color(90, 90, 90)
    pdf.set_line_width(0.15)
    pdf.set_font("Helvetica", "", 6.5)
    for dim in scene.dimensions:
        _draw_dimension(pdf, dim, to_page, scale)

    for circle in scene.circles:
        cx_page, cy_page = to_page(circle.center)
        radius_page = circle.radius * scale
        if circle.dashed:
            _draw_dashed_circle(pdf, cx_page, cy_page, radius_page, dash=1, gap=0.8)
        else:
            pdf.ellipse(cx_page - radius_page, cy_page - radius_page, 2 * radius_page, 2 * radius_page, style="D")

def _draw_dimension(pdf: FPDF, dim: Dimension, to_page, scale: float) -> None:
    if dim.horizontal:
        y = dim.p1[1] + dim.offset
        p1_line = to_page((dim.p1[0], y))
        p2_line = to_page((dim.p2[0], y))
    else:
        x = dim.p1[0] + dim.offset
        p1_line = to_page((x, dim.p1[1]))
        p2_line = to_page((x, dim.p2[1]))

    pdf.line(p1_line[0], p1_line[1], p2_line[0], p2_line[1])
    tick_half = 1.0
    if dim.horizontal:
        pdf.line(p1_line[0], p1_line[1] - tick_half, p1_line[0], p1_line[1] + tick_half)
        pdf.line(p2_line[0], p2_line[1] - tick_half, p2_line[0], p2_line[1] + tick_half)
    else:
        pdf.line(p1_line[0] - tick_half, p1_line[1], p1_line[0] + tick_half, p1_line[1])
        pdf.line(p2_line[0] - tick_half, p2_line[1], p2_line[0] + tick_half, p2_line[1])

    t = dim.label_t
    anchor_x = p1_line[0] + (p2_line[0] - p1_line[0]) * t
    anchor_y = p1_line[1] + (p2_line[1] - p1_line[1]) * t
    text_w = pdf.get_string_width(dim.label) + 1
    # Rótulo do lado de fora da peça: offset negativo = abaixo / à esquerda.
    if dim.horizontal:
        pdf.set_xy(anchor_x - text_w / 2, anchor_y + 0.5 if dim.offset < 0 else anchor_y - 6.5)
    else:
        if dim.offset < 0:
            x_texto = anchor_x + 1 if dim.label_inside else anchor_x - text_w - 1.5
        else:
            x_texto = (
                anchor_x - text_w - 1.5
                if dim.label_inside
                else anchor_x + dim.label_offset * scale + 1
            )
        pdf.set_xy(x_texto, anchor_y - 2)
    pdf.cell(text_w, 4, dim.label, align="C")


def _add_geometria(pdf: FPDF, profile: Profile, r: DesignResult) -> None:
    _add_secao(pdf, "GEOMETRIA DA SEÇÃO TRANSVERSAL")
    y_tabela = pdf.get_y()

    pdf.set_draw_color(190, 195, 200)
    pdf.set_line_width(0.2)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(30, 7, "SÍMBOLO", border="B", align="L")
    pdf.cell(40, 7, "DIMENSÃO", border="B", align="C")
    pdf.cell(85, 7, "PROPRIEDADE GEOMÉTRICA", border="B", align="L")
    pdf.cell(35, 7, "VALORES", border="B", ln=1, align="R")

    linhas = [
        ("bf", f"{profile.bf_mm:.1f} mm", "Área bruta (Ag)", f"{profile.ag_cm2:.2f} cm²"),
        ("tw", f"{profile.tw_mm:.1f} mm", "Momento de inércia em X (Ix)", f"{profile.ix_cm4:.2f} cm4"),
        ("tf", f"{profile.tf_mm:.1f} mm", "Momento de inércia em Y (Iy)", f"{profile.iy_cm4:.2f} cm4"),
        ("h", f"{profile.h_mm:.1f} mm", "Raio de giração em X (rx)", f"{profile.rx_cm:.2f} cm"),
        ("d", f"{profile.d_mm:.1f} mm", "Raio de giração em Y (ry)", f"{profile.ry_cm:.2f} cm"),
        ("d'", f"{profile.d_linha_mm:.1f} mm", "Raio de giração polar (r0)", f"{r.r0_cm:.2f} cm"),
    ]
    pdf.set_font("Helvetica", "", 8)
    for dim_nome, dim_valor, prop_nome, prop_valor in linhas:
        pdf.cell(30, 7, dim_nome, border="B", align="L")
        pdf.cell(40, 7, dim_valor, border="B", align="C")
        pdf.cell(85, 7, prop_nome, border="B", align="L")
        pdf.cell(35, 7, prop_valor, border="B", ln=1, align="R")

    # O perfil ocupa uma área própria abaixo da tabela, centralizado na página.
    pdf.set_y(y_tabela + 55)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_x(10)
    pdf.cell(190, 6, "SEÇÃO TRANSVERSAL COTADA", ln=1, align="C")
    # Reserva espaço para a cota superior (tw) não invadir o título.
    y_desenho = pdf.get_y() + 4
    scene = build_section_scene(profile)
    _draw_section_scene(pdf, scene, x0=67, y0=y_desenho, max_w=76, max_h=50, align_top=True)
    pdf.set_y(max(pdf.get_y(), y_desenho + 58))
    pdf.ln(4)


def _add_estabilidade_global(pdf: FPDF, r: DesignResult) -> None:
    _add_secao(pdf, "1. ESTABILIDADE GLOBAL")
    _add_linha_rotulada(pdf, "Carga crítica de flexão em X (Nex):", f"{r.nex_kn:.2f} kN")
    _add_linha_rotulada(pdf, "Carga crítica de flexão em Y (Ney):", f"{r.ney_kn:.2f} kN")
    _add_linha_rotulada(pdf, "Carga crítica de torção (Nez):", f"{r.nez_kn:.2f} kN")
    _add_linha_rotulada(pdf, "Carga crítica mínima (Ne,min):", f"{r.ne_min_kn:.2f} kN")
    _add_linha_rotulada(pdf, "Índice de esbeltez (λ0):", f"{r.lambda0:.3f}")
    _add_linha_rotulada(pdf, "Fator de redução (χ):", f"{r.chi:.4f}")


def _add_limite_esbeltez(pdf: FPDF, r: DesignResult) -> None:
    _add_secao(pdf, "2. VERIFICAÇÃO DO LIMITE DE ESBELTEZ")
    _add_linha_rotulada(pdf, "Esbeltez em X (λx)", f": {r.esbeltez_x:.2f}")
    _add_linha_rotulada(pdf, "Esbeltez em Y (λy)", f": {r.esbeltez_y:.2f}")
    _add_linha_rotulada(pdf, "Esbeltez máxima (λmax)", f": {r.esbeltez_max:.2f}")
    _add_linha_rotulada(pdf, "Limite de esbeltez", f": {r.limite_esbeltez:.0f}")

    status = "ATENDE AO LIMITE DE ESBELTEZ" if r.atende_esbeltez else "NÃO ATENDE AO LIMITE DE ESBELTEZ"
    if r.atende_esbeltez:
        pdf.set_fill_color(220, 245, 225)
        pdf.set_text_color(25, 105, 50)
    else:
        pdf.set_fill_color(255, 225, 225)
        pdf.set_text_color(150, 35, 35)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 8, status, border=1, ln=1, align="C", fill=True)
    pdf.set_text_color(0, 0, 0)


def _add_flambagem_local(pdf: FPDF, profile: Profile, r: DesignResult) -> None:
    # Reserva espaço para as duas colunas e evita que Mesa e Alma sejam
    # separadas pelo page break automático do FPDF.
    if pdf.get_y() > pdf.h - pdf.b_margin - 85:
        pdf.add_page()
    _add_secao(pdf, "3. FLAMBAGEM LOCAL (ÁREA EFETIVA)")

    def adicionar_elemento(
        x: float,
        largura: float,
        titulo: str,
        ocorre: bool,
        relacao: str,
        bt: float,
        limite_norma: float,
        limite_efetivo: float,
        c1: float,
        c2: float,
        sigma_el: float,
        b: float,
        bef: float,
    ) -> float:
        fonte = _FONTE_SIMBOLOS if getattr(pdf, "_fonte_simbolos_disponivel", False) else "Helvetica"
        y = pdf.get_y()

        def linha(texto: str, negrito: bool = False) -> None:
            pdf.set_xy(x, y_atual[0])
            pdf.set_font(fonte if not negrito else "Helvetica", "B" if negrito else "", 9)
            pdf.cell(largura, 5, texto, ln=1)
            y_atual[0] += 5

        y_atual = [y]
        linha(titulo, negrito=True)
        linha(f"b/t → ({relacao}) = {bt:.2f}")
        linha(f"(b/t)_lim = {limite_norma:.2f}")
        linha(f"(b/t)_lim / √χ = {limite_efetivo:.2f}")
        y_atual[0] += 2
        if not ocorre:
            linha("Não ocorre flambagem local")
            linha(f"b = bef = {b:.2f} mm")
            return y_atual[0]

        raiz = math.sqrt(sigma_el / r.sigma_c_mpa) if r.sigma_c_mpa > 0 else 0.0
        linha("Ocorre flambagem local")
        linha(f"c1 = {c1:.2f}")
        linha(f"c2 = {c2:.2f}")
        linha(f"σel = {sigma_el:.2f} MPa")
        linha(f"√(σel/(χfy)) = {raiz:.2f}")
        linha(f"b = {b:.2f} mm")
        linha(f"bef = {bef:.2f} mm")
        return y_atual[0]

    y_inicio = pdf.get_y()
    y_mesa = adicionar_elemento(
        10,
        88,
        "Mesa (elemento AL)",
        r.ocorre_flamb_mesa,
        "bf/(2.tf)",
        r.bt_mesa,
        r.limite_norma_mesa,
        r.limite_efetivo_mesa,
        r.c1_mesa,
        r.c2_mesa,
        r.sigma_el_mesa_mpa,
        r.b_mesa_mm,
        r.bef_mesa_mm,
    )
    pdf.set_y(y_inicio)
    y_alma = adicionar_elemento(
        108,
        88,
        "Alma (elemento AA)",
        r.ocorre_flamb_alma,
        "d'/tw" if profile.family == ProfileFamily.LAMINADO else "h/tw",
        r.bt_alma,
        r.limite_norma_alma,
        r.limite_efetivo_alma,
        r.c1_alma,
        r.c2_alma,
        r.sigma_el_alma_mpa,
        r.b_alma_mm,
        r.bef_alma_mm,
    )

    pdf.set_y(max(y_inicio, y_mesa, y_alma) + 2)
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, f"Área bruta (Ag): {profile.ag_cm2:.2f} cm²", ln=1)
    pdf.cell(0, 5, f"Área efetiva (Aef): {r.aef_cm2:.2f} cm²", ln=1)


def _add_resultado(pdf: FPDF, r: DesignResult) -> None:
    _add_secao(pdf, "4. VERIFICAÇÃO DO DIMENSIONAMENTO")
    _add_linha_rotulada(pdf, "Esforço resistente (Nc,Rd)", f": {r.nc_rd_kn:.2f} kN")
    _add_linha_rotulada(pdf, "Esforço solicitante (Nc,Sd)", f": {r.ncsd_kn:.2f} kN")

    resistencia_ok = r.nc_rd_kn >= r.ncsd_kn
    comparacao = "Nc,Sd <= Nc,Rd" if resistencia_ok else "Nc,Sd > Nc,Rd"
    status = "ATENDE AO DIMENSIONAMENTO" if r.aprovado else "NÃO ATENDE AO DIMENSIONAMENTO"
    if r.aprovado:
        pdf.set_fill_color(220, 245, 225)
        pdf.set_text_color(25, 105, 50)
    else:
        pdf.set_fill_color(255, 225, 225)
        pdf.set_text_color(150, 35, 35)
    fonte_status = _FONTE_SIMBOLOS if getattr(pdf, "_fonte_simbolos_disponivel", False) else "Helvetica"
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, f"Verificação: {comparacao}", border="LTR", ln=1, align="C", fill=True)
    pdf.set_font(fonte_status, "B", 11)
    pdf.cell(0, 9, status, border="LBR", ln=1, align="C", fill=True)
    pdf.set_text_color(0, 0, 0)


def gerar_memorial_pdf(
    profile: Profile,
    steel: SteelType,
    loads: LoadCase,
    result: DesignResult,
    autor: str | None = None,
    output_dir: str | Path = ".",
) -> Path:
    """Gera o memorial de cálculo e retorna o caminho do PDF salvo.

    Nome de arquivo: ``Memorial_Compressao_<bitola>.pdf`` (mesma convenção de
    ``CodigocomPDF.py``, com ``/`` trocado por ``_`` na bitola).
    """

    autor_sanitizado = _sanitizar_latin1(autor.strip()) if autor and autor.strip() else _AUTOR_PADRAO
    pdf = _RelatorioPDF(autor=autor_sanitizado)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    familia_label = "Laminado" if profile.family == ProfileFamily.LAMINADO else "Soldado"
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(
        0,
        7,
        f"Perfil: {profile.bitola} ({familia_label}) | Aço: {steel.designacao} (fy = {steel.fy_mpa:g} MPa)",
        ln=1,
    )

    _add_geometria(pdf, profile, result)
    _add_estabilidade_global(pdf, result)
    _add_limite_esbeltez(pdf, result)
    _add_flambagem_local(pdf, profile, result)
    _add_resultado(pdf, result)

    bitola_segura = re.sub(r'[<>:"/\\|?*]', "_", profile.bitola).strip(" .")
    nome_arquivo = f"Memorial_Compressao_{bitola_segura}.pdf"
    caminho = Path(output_dir) / nome_arquivo
    pdf.output(str(caminho))
    return caminho
