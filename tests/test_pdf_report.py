from __future__ import annotations

from dataclasses import replace

from app.report import pdf_report
from app.domain.calculations import calcular_pilar
from app.report.pdf_report import gerar_memorial_pdf
from tests.test_calculations import ACO_A572_GR50, CARREGAMENTO, PERFIL_W310X21


def test_pdf_result_summary_shows_lambda_before_chi(monkeypatch):
    result = calcular_pilar(PERFIL_W310X21, ACO_A572_GR50, CARREGAMENTO)
    lines = []

    monkeypatch.setattr(pdf_report, "_add_secao", lambda *_args: None)
    monkeypatch.setattr(
        pdf_report,
        "_add_linha_rotulada",
        lambda _pdf, label, value: lines.append((label, value)),
    )

    class FakePDF:
        h = 297
        b_margin = 15
        _fonte_simbolos_disponivel = True

        def get_y(self):
            return 20

    pdf_report._add_resultado(FakePDF(), result)

    assert ("λ0 / χ", f": {result.lambda0:.4f} / {result.chi:.4f}") in lines
    lines.clear()
    pdf = FakePDF()
    pdf._fonte_simbolos_disponivel = False
    pdf_report._add_resultado(pdf, result)
    assert ("lambda0 / chi", f": {result.lambda0:.4f} / {result.chi:.4f}") in lines


def test_memorial_pdf_includes_structdim_logo(tmp_path):
    result = calcular_pilar(PERFIL_W310X21, ACO_A572_GR50, CARREGAMENTO)
    pdf_path = gerar_memorial_pdf(
        PERFIL_W310X21,
        ACO_A572_GR50,
        CARREGAMENTO,
        result,
        output_dir=tmp_path,
    )

    assert pdf_path.is_file()
    assert b"/Subtype /Image" in pdf_path.read_bytes()


def test_memoriais_da_mesma_bitola_nao_sobrescrevem_arquivos(tmp_path):
    result = calcular_pilar(PERFIL_W310X21, ACO_A572_GR50, CARREGAMENTO)
    primeiro = gerar_memorial_pdf(
        PERFIL_W310X21, ACO_A572_GR50, CARREGAMENTO, result, output_dir=tmp_path
    )
    conteudo_original = primeiro.read_bytes()
    outras_cargas = replace(CARREGAMENTO, ncsd_kn=100)
    outro_resultado = calcular_pilar(PERFIL_W310X21, ACO_A572_GR50, outras_cargas)

    segundo = gerar_memorial_pdf(
        PERFIL_W310X21, ACO_A572_GR50, outras_cargas, outro_resultado, output_dir=tmp_path
    )
    terceiro = gerar_memorial_pdf(
        PERFIL_W310X21, ACO_A572_GR50, outras_cargas, outro_resultado, output_dir=tmp_path
    )

    assert primeiro.name == "Memorial_Compressao_W 310 x 21.0.pdf"
    assert segundo.name == "Memorial_Compressao_W 310 x 21.0 (1).pdf"
    assert terceiro.name == "Memorial_Compressao_W 310 x 21.0 (2).pdf"
    assert primeiro.read_bytes() == conteudo_original
    assert segundo.read_bytes().startswith(b"%PDF-")
    assert segundo.read_bytes() != conteudo_original
    assert terceiro.read_bytes().startswith(b"%PDF-")
