from __future__ import annotations

import pytest

from app.domain.drawing import build_section_scene
from app.domain.models import ProfileFamily
from tests.test_calculations import CASOS_DE_CALCULO


@pytest.mark.parametrize(("perfil", "_carregamento"), CASOS_DE_CALCULO)
def test_secao_e_cotas_sao_montadas_para_as_duas_familias(perfil, _carregamento):
    scene = build_section_scene(perfil)

    simbolos = [dim.label.split(" =")[0] for dim in scene.dimensions]
    simbolos_esperados = ["bf", "d", "tf", "tf", "tw", "h"]
    if perfil.family == ProfileFamily.LAMINADO:
        simbolos_esperados.append("d'")
    assert simbolos == simbolos_esperados
    assert scene.profile_bitola == perfil.bitola
    assert not scene.circles
    assert len(scene.outline) == (1 if perfil.family == ProfileFamily.LAMINADO else 5)