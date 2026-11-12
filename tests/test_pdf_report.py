from __future__ import annotations

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
