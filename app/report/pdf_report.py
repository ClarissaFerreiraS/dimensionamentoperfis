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
from pathlib import Path

from fpdf import FPDF

from app.domain.drawing import Dimension, Polyline, SectionScene, build_section_scene
from app.domain.models import DesignResult, LoadCase, Profile, ProfileFamily, SteelType

_NORMA_BASE = "ABNT NBR 8800:2024"
_AUTOR_PADRAO = "Autor(a) Responsável"

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
        super().__init__()
        self._autor = autor

    def header(self) -> None:
        self.set_font("Helvetica", "B", 11)
        self.set_fill_color(240, 243, 246)
        self.cell(0, 8, "MEMORIAL DE CALCULO ESTRUTURAL - COMPRESSAO PURA", border=1, ln=1, align="C", fill=True)
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, f"Autor (a) Responsável: {self._autor}", border="LR", ln=1)
        self.cell(0, 5, f"Norma Base: {_NORMA_BASE}", border="LRB", ln=1)
        self.ln(3)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Pagina {self.page_no()}", 0, 0, "C")


def _add_secao(pdf: FPDF, titulo: str) -> None:
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(20, 40, 100)
    pdf.cell(0, 6, titulo, border="B", ln=1)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)


def _add_linha(pdf: FPDF, texto: str) -> None:
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, texto, ln=1)


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


def _draw_section_scene(pdf: FPDF, scene: SectionScene, x0: float, y0: float, max_w: float, max_h: float) -> None:
    """Desenha ``scene`` (mm, origem no centro, +y para cima) na página do PDF.

    A caixa de destino é ``(x0, y0)`` até ``(x0+max_w, y0+max_h)`` em mm de
    página. A cena é ajustada (fit) mantendo proporção e centralizada nessa
    caixa; o eixo Y é invertido (PDF cresce para baixo).
    """

    scale = min(max_w / scene.width_mm, max_h / scene.height_mm)
    cx = x0 + max_w / 2
    cy = y0 + max_h / 2

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

    pdf.set_font("Helvetica", "", 7)
    for axis in scene.axes:
        p1 = to_page(axis.p1)
        p2 = to_page(axis.p2)
        _draw_dashed_line(pdf, p1[0], p1[1], p2[0], p2[1], dash=2.2, gap=1)
        text_w = pdf.get_string_width(axis.label) + 1
        pdf.set_xy(p1[0] - text_w - 1, p1[1] - 2.25)
        pdf.cell(text_w, 4.5, axis.label, align="C")
        pdf.set_xy(p2[0] + 1, p2[1] - 2.25)
        pdf.cell(text_w, 4.5, axis.label, align="C")


def _draw_dimension(pdf: FPDF, dim: Dimension, to_page, scale: float) -> None:
    if dim.horizontal:
        y = dim.p1[1] + dim.offset
        p1_line = to_page((dim.p1[0], y))
        p2_line = to_page((dim.p2[0], y))
    else:
        x = dim.p1[0] + dim.offset
        p1_line = to_page((x, dim.p1[1]))
        p2_line = to_page((x, dim.p2[1]))

    p1_ref = to_page(dim.p1)
    p2_ref = to_page(dim.p2)

    # Linhas de extensão: do ponto de referência na peça até a linha de cota.
    pdf.line(p1_ref[0], p1_ref[1], p1_line[0], p1_line[1])
    pdf.line(p2_ref[0], p2_ref[1], p2_line[0], p2_line[1])
    # Linha de cota.
    pdf.line(p1_line[0], p1_line[1], p2_line[0], p2_line[1])

    t = dim.label_t
    anchor_x = p1_line[0] + (p2_line[0] - p1_line[0]) * t
    anchor_y = p1_line[1] + (p2_line[1] - p1_line[1]) * t
    text_w = pdf.get_string_width(dim.label) + 1
    # Rótulo do lado de fora da peça: offset negativo = abaixo / à esquerda.
    if dim.horizontal:
        pdf.set_xy(anchor_x - text_w / 2, anchor_y + 0.5 if dim.offset < 0 else anchor_y - 4.5)
    else:
        pdf.set_xy(anchor_x - text_w - 1.5 if dim.offset < 0 else anchor_x + 1, anchor_y - 2)
    pdf.cell(text_w, 4, dim.label, align="C")


def _add_geometria(pdf: FPDF, profile: Profile, r: DesignResult) -> None:
    _add_secao(pdf, "GEOMETRIA DA SECAO TRANSVERSAL")
    y_tabela = pdf.get_y()

    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(22, 6, "Dimensões", border=1, align="C")
    pdf.cell(20, 6, "Valores", border=1, align="C")
    pdf.cell(45, 6, "Propriedades", border=1, align="C")
    pdf.cell(27, 6, "Valores", border=1, ln=1, align="C")

    linhas = [
        ("bf", f"{profile.bf_mm:.1f} mm", "Area Bruta (Ag)", f"{profile.ag_cm2:.2f} cm2"),
        ("tw", f"{profile.tw_mm:.1f} mm", "Inercia em X (Ix)", f"{profile.ix_cm4:.2f} cm4"),
        ("tf", f"{profile.tf_mm:.1f} mm", "Inercia em Y (Iy)", f"{profile.iy_cm4:.2f} cm4"),
        ("h", f"{profile.h_mm:.1f} mm", "Raio de Giracao (rx)", f"{profile.rx_cm:.2f} cm"),
        ("d", f"{profile.d_mm:.1f} mm", "Raio de Giracao (ry)", f"{profile.ry_cm:.2f} cm"),
        ("d'", f"{profile.d_linha_mm:.1f} mm", "Raio de Giracao Polar (r0)", f"{r.r0_cm:.2f} cm"),
    ]
    pdf.set_font("Helvetica", "", 8)
    for dim_nome, dim_valor, prop_nome, prop_valor in linhas:
        pdf.cell(22, 6, dim_nome, border=1)
        pdf.cell(20, 6, dim_valor, border=1, align="C")
        pdf.cell(45, 6, prop_nome, border=1)
        pdf.cell(27, 6, prop_valor, border=1, ln=1, align="C")

    # A tabela termina em x≈124 mm; a caixa do desenho fica centrada no
    # espaço restante com folga dos dois lados, porque as cotas têm rótulos
    # à esquerda (d, tf, y) e à direita (h, d') da seção.
    scene = build_section_scene(profile)
    _draw_section_scene(pdf, scene, x0=137, y0=y_tabela + 4, max_w=50, max_h=50)
    pdf.set_y(max(pdf.get_y(), y_tabela + 58))
    pdf.ln(4)


def _add_estabilidade_global(pdf: FPDF, r: DesignResult) -> None:
    _add_secao(pdf, "1. ESTABILIDADE GLOBAL")
    _add_linha(pdf, f"Carga Critica Flexao (Nex): {r.nex_kn:.2f} kN")
    _add_linha(pdf, f"Carga Critica Flexao (Ney): {r.ney_kn:.2f} kN")
    _add_linha(pdf, f"Carga Critica Torcao (Nez): {r.nez_kn:.2f} kN")
    _add_linha(pdf, f"Carga Critica Minima (Ne_min): {r.ne_min_kn:.2f} kN")
    _add_linha(pdf, f"Indice de esbeltez (lambda_0): {r.lambda0:.3f}")
    _add_linha(pdf, f"Fator de reducao (X): {r.chi:.4f}")


def _add_limite_esbeltez(pdf: FPDF, r: DesignResult) -> None:
    _add_secao(pdf, "2. VERIFICACAO DO LIMITE DE ESBELTEZ")
    _add_linha(pdf, f"Esbeltez em X (lambda_x) = {r.esbeltez_x:.2f}")
    _add_linha(pdf, f"Esbeltez em Y (lambda_y) = {r.esbeltez_y:.2f}")
    _add_linha(pdf, f"Esbeltez Maxima (lambda_max) = {r.esbeltez_max:.2f}")
    _add_linha(pdf, f"Limite de esbeltez = {r.limite_esbeltez:.2f}")
    if r.atende_esbeltez:
        _add_linha(pdf, "-> STATUS: ATENDE AO LIMITE DE ESBELTEZ (lambda_max <= 200)")
    else:
        _add_linha(pdf, "-> STATUS: NAO ATENDE AO LIMITE DE ESBELTEZ (lambda_max > 200)")


def _add_flambagem_local(pdf: FPDF, profile: Profile, r: DesignResult) -> None:
    _add_secao(pdf, "3. FLAMBAGEM LOCAL (AREA EFETIVA)")
    is_laminado = profile.family == ProfileFamily.LAMINADO

    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, "Mesas (elementos AL)", ln=1)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, f"b/t (bf/2.tf) = {r.bt_mesa:.2f}", ln=1)
    pdf.cell(0, 5, f"(b/t)lim = {r.limite_norma_mesa:.2f}", ln=1)
    pdf.cell(0, 5, f"(b/t)lim / raiz(X) = {r.limite_efetivo_mesa:.2f}", ln=1)
    if r.ocorre_flamb_mesa:
        pdf.cell(0, 5, "-> STATUS: OCORRE flambagem local na mesa.", ln=1)
    else:
        pdf.cell(0, 5, "-> STATUS: NAO ocorre flambagem local na mesa.", ln=1)
    pdf.cell(0, 5, f"bef(adotado) = {r.bef_mesa_mm:.2f} mm", ln=1)

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, "Alma (elemento AA)", ln=1)
    pdf.set_font("Helvetica", "", 9)
    rel_alma = "d'/tw" if is_laminado else "h/tw"
    pdf.cell(0, 5, f"b/t ({rel_alma}) = {r.bt_alma:.2f}", ln=1)
    pdf.cell(0, 5, f"(b/t)lim = {r.limite_norma_alma:.2f}", ln=1)
    pdf.cell(0, 5, f"(b/t)lim / raiz(X) = {r.limite_efetivo_alma:.2f}", ln=1)
    if r.ocorre_flamb_alma:
        pdf.cell(0, 5, "-> STATUS: OCORRE flambagem local na alma.", ln=1)
    else:
        pdf.cell(0, 5, "-> STATUS: NAO ocorre flambagem local na alma.", ln=1)
    pdf.cell(0, 5, f"bef(adotado) = {r.bef_alma_mm:.2f} mm", ln=1)

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, f"Area Bruta (Ag): {profile.ag_cm2:.2f} cm2", ln=1)
    pdf.cell(0, 5, f"Area Efetiva (Aef): {r.aef_cm2:.2f} cm2", ln=1)


def _add_resultado(pdf: FPDF, r: DesignResult) -> None:
    _add_secao(pdf, "4. RESULTADO DO DIMENSIONAMENTO")
    _add_linha(pdf, f"Esforco Resistente de Calculo (Nc,Rd): {r.nc_rd_kn:.2f} kN")
    _add_linha(pdf, f"Esforco Solicitante (Nc,Sd) informado: {r.ncsd_kn:.2f} kN")

    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 10)
    if r.aprovado:
        pdf.cell(0, 9, "VEREDITO: APROVADO!", border=1, ln=1, align="C")
    else:
        pdf.cell(0, 9, "VEREDITO: REPROVADO!", border=1, ln=1, align="C")


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
        f"Perfil: {profile.bitola} ({familia_label}) | Aco: {steel.designacao} (fy = {steel.fy_mpa:g} MPa)",
        ln=1,
    )

    _add_geometria(pdf, profile, result)
    _add_estabilidade_global(pdf, result)
    _add_limite_esbeltez(pdf, result)
    _add_flambagem_local(pdf, profile, result)
    _add_resultado(pdf, result)

    nome_arquivo = f"Memorial_Compressao_{profile.bitola.replace('/', '_')}.pdf"
    caminho = Path(output_dir) / nome_arquivo
    pdf.output(str(caminho))
    return caminho
