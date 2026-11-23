from __future__ import annotations

from dataclasses import replace

import pytest

from app.report import pdf_report
from app.domain.calculations import calcular_pilar
from app.report.pdf_report import gerar_memorial_pdf
from tests.test_calculations import ACO_A572_GR50, CASOS_DE_CALCULO


@pytest.mark.parametrize(("perfil", "carregamento"), CASOS_DE_CALCULO)
def test_pdf_result_summary_shows_lambda_before_chi(monkeypatch, perfil, carregamento):
    result = calcular_pilar(perfil, ACO_A572_GR50, carregamento)
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


@pytest.mark.parametrize(("perfil", "carregamento"), CASOS_DE_CALCULO)
def test_memorial_pdf_includes_structdim_logo(tmp_path, perfil, carregamento):
    result = calcular_pilar(perfil, ACO_A572_GR50, carregamento)
    pdf_path = gerar_memorial_pdf(
        perfil,
        ACO_A572_GR50,
        carregamento,
        result,
        output_dir=tmp_path,
    )

    assert pdf_path.is_file()
    assert b"/Subtype /Image" in pdf_path.read_bytes()


@pytest.mark.parametrize(("perfil", "carregamento"), CASOS_DE_CALCULO)
def test_memoriais_da_mesma_bitola_nao_sobrescrevem_arquivos(tmp_path, perfil, carregamento):
    result = calcular_pilar(perfil, ACO_A572_GR50, carregamento)
    primeiro = gerar_memorial_pdf(
        perfil, ACO_A572_GR50, carregamento, result, output_dir=tmp_path
    )
    conteudo_original = primeiro.read_bytes()
    outras_cargas = replace(carregamento, ncsd_kn=100)
    outro_resultado = calcular_pilar(perfil, ACO_A572_GR50, outras_cargas)

    segundo = gerar_memorial_pdf(
        perfil, ACO_A572_GR50, outras_cargas, outro_resultado, output_dir=tmp_path
    )
    terceiro = gerar_memorial_pdf(
        perfil, ACO_A572_GR50, outras_cargas, outro_resultado, output_dir=tmp_path
    )

    nome_base = f"Memorial_Compressao_{perfil.bitola}"
    assert primeiro.name == f"{nome_base}.pdf"
    assert segundo.name == f"{nome_base} (1).pdf"
    assert terceiro.name == f"{nome_base} (2).pdf"
    assert primeiro.read_bytes() == conteudo_original
    assert segundo.read_bytes().startswith(b"%PDF-")
    assert segundo.read_bytes() != conteudo_original
    assert terceiro.read_bytes().startswith(b"%PDF-")
