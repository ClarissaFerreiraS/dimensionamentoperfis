from __future__ import annotations

from app.domain.calculations import calcular_pilar
from app.report.pdf_report import gerar_memorial_pdf
from tests.test_calculations import ACO_A572_GR50, CARREGAMENTO, PERFIL_W310X21


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
