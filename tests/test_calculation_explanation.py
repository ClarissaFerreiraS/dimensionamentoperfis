from __future__ import annotations

import pytest

from PySide6.QtWidgets import QApplication, QDialog, QTextBrowser

from app.db.database import open_database
from app.domain.calculation_explanation import EXPLANATION_NOTE, build_calculation_steps
from app.domain.calculations import calcular_pilar
from app.domain.models import ProfileFamily
from app.ui.project_editor import ProjectEditor
from tests.test_calculations import ACO_A572_GR50, CASOS_DE_CALCULO


@pytest.mark.parametrize(("perfil", "carregamento"), CASOS_DE_CALCULO)
def test_explanation_uses_calculated_values_and_norm_reference(perfil, carregamento):
    result = calcular_pilar(perfil, ACO_A572_GR50, carregamento)

    steps = build_calculation_steps(perfil, ACO_A572_GR50, carregamento, result)

    assert len(steps) == 6
    assert (
        f"λx = Kx·Lx·100/rx = {carregamento.kx:g}·{carregamento.lx_m:g}·100/"
        f"{perfil.rx_cm:g} = {result.esbeltez_x:.2f}"
        in steps[0].equations[0]
    )
    assert "Nₑ = mín(" in steps[1].equations[-1]
    assert f"= {result.ne_min_kn:.2f} kN" in steps[1].equations[-1]
    assert steps[2].equations[0].startswith("λ₀ =")
    assert steps[2].equations[0].endswith(f"= {result.lambda0:.4f}")
    chi_formula = "0.658^(λ₀²)" if result.lambda0 <= 1.5 else "0.877/λ₀²"
    assert f"χ = {chi_formula} = {result.chi:.4f}" in steps[2].equations[1]
    assert steps[3].equations[0] == "Mesa"
    assert steps[3].equations[1] == (
        "Ocorre flambagem local" if result.ocorre_flamb_mesa else "Não ocorre flambagem local"
    )
    assert "bf/(2·tf)" in steps[3].equations[2]
    alma_index = steps[3].equations.index("Alma")
    assert steps[3].equations[alma_index + 1] == (
        "Ocorre flambagem local" if result.ocorre_flamb_alma else "Não ocorre flambagem local"
    )
    alma_relacao = "d′/tw" if perfil.family == ProfileFamily.LAMINADO else "h/tw"
    alma_dimensoes = (
        perfil.d_linha_mm if perfil.family == ProfileFamily.LAMINADO else perfil.h_mm
    )
    assert (
        f"{alma_relacao} = {alma_dimensoes:g}/{perfil.tw_mm:g} = {result.bt_alma:.2f}"
        in steps[3].equations[alma_index + 2]
    )
    assert any("σel =" in item for item in steps[3].equations[:alma_index]) is (
        result.ocorre_flamb_mesa
    )
    assert any("σel =" in item for item in steps[3].equations[alma_index + 1 :]) is (
        result.ocorre_flamb_alma
    )
    assert steps[4].equations[0] == "Aef = Ag − Σ(b − bef)·t"
    assert f"= {result.aef_cm2:.2f} cm²" in steps[4].equations[1]
    assert "Nc,Rd = χ·Aef·(fy/10)/γA1" in steps[5].equations[0]
    assert f"= {result.nc_rd_kn:.2f} kN" in steps[5].equations[0]
    assert not any("η =" in equation for equation in steps[5].equations)
    assert "fins educacionais" in EXPLANATION_NOTE


@pytest.mark.parametrize(("perfil", "carregamento"), CASOS_DE_CALCULO)
def test_result_summary_shows_lambda_before_chi(perfil, carregamento):
    app = QApplication.instance() or QApplication([])
    connection = open_database(":memory:")
    editor = ProjectEditor(connection)
    result = calcular_pilar(perfil, ACO_A572_GR50, carregamento)

    editor._atualizar_resultado(perfil, ACO_A572_GR50, result)

    assert (
        f"λ₀ / χ: <b>{result.lambda0:.4f} / {result.chi:.4f}</b>"
        in editor.resultado_label.text()
    )
    editor.close()
    connection.close()


@pytest.mark.parametrize(("perfil", "carregamento"), CASOS_DE_CALCULO)
def test_explanation_uses_family_specific_web_slenderness(perfil, carregamento):
    result = calcular_pilar(perfil, ACO_A572_GR50, carregamento)

    steps = build_calculation_steps(perfil, ACO_A572_GR50, carregamento, result)

    alma_index = steps[3].equations.index("Alma")
    relation = "d′/tw" if perfil.family == ProfileFamily.LAMINADO else "h/tw"
    height = perfil.d_linha_mm if perfil.family == ProfileFamily.LAMINADO else perfil.h_mm
    assert (
        f"b/t = {relation} = {height:g}/{perfil.tw_mm:g} = {result.bt_alma:.2f}"
        in steps[3].equations[alma_index + 2]
    )


@pytest.mark.parametrize(("perfil", "carregamento"), CASOS_DE_CALCULO)
def test_ui_step_by_step_dialog_shows_calculated_values(monkeypatch, perfil, carregamento):
    app = QApplication.instance() or QApplication([])
    connection = open_database(":memory:")
    editor = ProjectEditor(connection)
    result = calcular_pilar(perfil, ACO_A572_GR50, carregamento)
    editor._current_result = result
    monkeypatch.setattr(editor, "_current_profile", lambda: perfil)
    monkeypatch.setattr(editor, "_current_steel", lambda: ACO_A572_GR50)
    monkeypatch.setattr(editor, "_build_load_case", lambda: carregamento)
    dialog_html: list[str] = []
    dialog_text: list[str] = []

    def capture_dialog(dialog: QDialog) -> int:
        browser = dialog.findChild(QTextBrowser)
        assert browser is not None
        dialog_html.append(browser.toHtml())
        dialog_text.append(browser.toPlainText())
        return 0

    monkeypatch.setattr(QDialog, "exec", capture_dialog)
    editor._mostrar_etapas_calculo()

    assert "Passo a passo do cálculo" in dialog_html[0]
    assert f"= {result.nc_rd_kn:.2f} kN" in dialog_html[0]
    assert "ABNT NBR 8800" not in dialog_html[0]
    assert "Mesa" in dialog_html[0]
    assert "Alma" in dialog_html[0]
    assert dialog_text[0].index(f"= {result.lambda0:.4f}") < dialog_text[0].index(
        f"= {result.chi:.4f}"
    )
    app.processEvents()
    editor.close()
    connection.close()
