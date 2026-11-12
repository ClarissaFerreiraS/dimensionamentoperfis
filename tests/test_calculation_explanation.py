from __future__ import annotations

from dataclasses import replace

from PySide6.QtWidgets import QApplication, QDialog, QTextBrowser

from app.db.database import open_database
from app.domain.calculation_explanation import EXPLANATION_NOTE, build_calculation_steps
from app.domain.calculations import calcular_pilar
from app.domain.models import ProfileFamily
from app.ui.project_editor import ProjectEditor
from tests.test_calculations import ACO_A572_GR50, CARREGAMENTO, PERFIL_W310X21


def test_explanation_uses_calculated_values_and_norm_reference():
    result = calcular_pilar(PERFIL_W310X21, ACO_A572_GR50, CARREGAMENTO)

    steps = build_calculation_steps(PERFIL_W310X21, ACO_A572_GR50, CARREGAMENTO, result)

    assert len(steps) == 6
    assert "λx = Kx·Lx·100/rx = 1·1·100/11.77 = 8.50" in steps[0].equations[0]
    assert "Nₑ = mín(" in steps[1].equations[-1]
    assert "= 1934.44 kN" in steps[1].equations[-1]
    assert steps[2].equations[0].startswith("λ₀ =")
    assert steps[2].equations[0].endswith(f"= {result.lambda0:.4f}")
    assert "χ = 0.658^(λ₀²) = 0.8162" in steps[2].equations[1]
    assert steps[3].equations[0] == "Mesa"
    assert steps[3].equations[1] == "Não ocorre flambagem local"
    assert "bf/(2·tf)" in steps[3].equations[2]
    alma_index = steps[3].equations.index("Alma")
    assert steps[3].equations[alma_index + 1] == "Ocorre flambagem local"
    assert "d′/tw = 272/5.1 = 53.33" in steps[3].equations[alma_index + 2]
    assert not any("σel =" in item for item in steps[3].equations[:alma_index])
    assert any("σel =" in item for item in steps[3].equations[alma_index + 1 :])
    assert steps[4].equations[0] == "Aef = Ag − Σ(b − bef)·t"
    assert "4(5.05 − 5.05)·0.57" in steps[4].equations[1]
    assert "= 24.48 cm²" in steps[4].equations[1]
    assert "Nc,Rd = χ·Aef·(fy/10)/γA1" in steps[5].equations[0]
    assert "= 626.76 kN" in steps[5].equations[0]
    assert not any("η =" in equation for equation in steps[5].equations)
    assert "fins educacionais" in EXPLANATION_NOTE


def test_result_summary_shows_lambda_before_chi():
    app = QApplication.instance() or QApplication([])
    connection = open_database(":memory:")
    editor = ProjectEditor(connection)
    result = calcular_pilar(PERFIL_W310X21, ACO_A572_GR50, CARREGAMENTO)

    editor._atualizar_resultado(PERFIL_W310X21, ACO_A572_GR50, result)

    assert (
        f"λ₀ / χ: <b>{result.lambda0:.4f} / {result.chi:.4f}</b>"
        in editor.resultado_label.text()
    )
    editor.close()
    connection.close()


def test_explanation_uses_welded_web_slenderness():
    perfil_soldado = replace(PERFIL_W310X21, family=ProfileFamily.SOLDADO)
    result = calcular_pilar(perfil_soldado, ACO_A572_GR50, CARREGAMENTO)

    steps = build_calculation_steps(perfil_soldado, ACO_A572_GR50, CARREGAMENTO, result)

    alma_index = steps[3].equations.index("Alma")
    assert "b/t = h/tw = 292/5.1 = 57.25" in steps[3].equations[alma_index + 2]


def test_ui_step_by_step_dialog_shows_calculated_values(monkeypatch):
    app = QApplication.instance() or QApplication([])
    connection = open_database(":memory:")
    editor = ProjectEditor(connection)
    result = calcular_pilar(PERFIL_W310X21, ACO_A572_GR50, CARREGAMENTO)
    editor._current_result = result
    monkeypatch.setattr(editor, "_current_profile", lambda: PERFIL_W310X21)
    monkeypatch.setattr(editor, "_current_steel", lambda: ACO_A572_GR50)
    monkeypatch.setattr(editor, "_build_load_case", lambda: CARREGAMENTO)
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
    assert "= 626.76 kN" in dialog_html[0]
    assert "ABNT NBR 8800" not in dialog_html[0]
    assert "Mesa" in dialog_html[0]
    assert "Alma" in dialog_html[0]
    assert dialog_text[0].index(f"= {result.lambda0:.4f}") < dialog_text[0].index(
        f"= {result.chi:.4f}"
    )
    app.processEvents()
    editor.close()
    connection.close()
