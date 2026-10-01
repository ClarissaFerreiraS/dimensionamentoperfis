from __future__ import annotations

from dataclasses import replace

from app.domain.drawing import build_section_scene
from app.domain.models import ProfileFamily
from tests.test_calculations import PERFIL_W310X21


def test_perfil_soldado_usa_cotas_do_esboco_e_mantem_soldas():
    perfil = replace(
        PERFIL_W310X21,
        family=ProfileFamily.SOLDADO,
        d_linha_mm=PERFIL_W310X21.h_mm,
        ec_mm=8,
    )

    scene = build_section_scene(perfil)

    simbolos = [dim.label.split(" =")[0] for dim in scene.dimensions]
    assert simbolos == ["bf", "d", "tf", "tf", "tw", "h"]
    assert not scene.circles
    assert len(scene.outline) == 5