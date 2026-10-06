"""Teste de regressão do motor de cálculo.

Caso de validação extraído da própria planilha ``ELU Compressão.xlsx``,
aba "Verif W e HP (Gerdau) 2024": perfil **W 310 x 21.0**, aço
**ASTM A572 Grau 50**. Os valores esperados abaixo são os que a planilha (e os
scripts originais ``Codigocompleto.py``/``CodigocomPDF.py``) produzem para
esse caso — servem para garantir que a extração para ``app/domain`` não
alterou nenhuma fórmula.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.domain.calculations import calcular_pilar
from app.domain.models import LoadCase, Profile, ProfileFamily, SteelType

PERFIL_W310X21 = Profile(
    bitola="W 310 x 21.0",
    family=ProfileFamily.LAMINADO,
    d_mm=303,
    bf_mm=101,
    tw_mm=5.1,
    tf_mm=5.7,
    h_mm=292,
    d_linha_mm=272,
    ag_cm2=27.2,
    ix_cm4=3776,
    rx_cm=11.77,
    iy_cm4=98,
    ry_cm=1.9,
    j_cm4=3.27,
    cw_cm6=21628,
)

ACO_A572_GR50 = SteelType(designacao="ASTM A572 Grau 50", fy_mpa=345, fu_mpa=450)

CARREGAMENTO = LoadCase(
    ncsd_kn=305,
    kx=1.0,
    lx_m=1.0,
    ky=1.0,
    ly_m=1.0,
    kz=1.0,
    lz_m=0.4,
    ea_gpa=200,
    ga_gpa=77,
)


@pytest.fixture(scope="module")
def resultado():
    return calcular_pilar(PERFIL_W310X21, ACO_A572_GR50, CARREGAMENTO)


def test_estabilidade_global(resultado):
    assert resultado.nex_kn == pytest.approx(74535.252437, rel=1e-4)
    assert resultado.ney_kn == pytest.approx(1934.442463, rel=1e-4)
    assert resultado.nez_kn == pytest.approx(18948.723783, rel=1e-4)
    assert resultado.lambda0 == pytest.approx(0.696492, rel=1e-4)
    assert resultado.chi == pytest.approx(0.816246, rel=1e-4)


def test_limite_esbeltez_atendido(resultado):
    assert resultado.esbeltez_max <= resultado.limite_esbeltez
    assert resultado.atende_esbeltez is True


def test_flambagem_local_mesa_nao_ocorre(resultado):
    assert resultado.bt_mesa == pytest.approx(8.859649, rel=1e-4)
    assert resultado.ocorre_flamb_mesa is False
    assert resultado.b_mesa_mm == pytest.approx(50.5)
    assert resultado.bef_mesa_mm == pytest.approx(resultado.b_mesa_mm)
    assert resultado.sigma_el_mesa_mpa == 0


def test_flambagem_local_alma_ocorre(resultado):
    assert resultado.bt_alma == pytest.approx(53.333333, rel=1e-4)
    assert resultado.ocorre_flamb_alma is True
    assert resultado.c1_alma == pytest.approx(0.18)
    assert resultado.c2_alma == pytest.approx(1.31)
    assert resultado.sigma_el_alma_mpa > 0
    assert resultado.bef_alma_mm == pytest.approx(218.716483, rel=1e-4)


def test_area_efetiva_e_resistencia(resultado):
    assert resultado.aef_cm2 == pytest.approx(24.482541, rel=1e-4)
    assert resultado.nc_rd_kn == pytest.approx(626.764068, rel=1e-4)


def test_verificacao_resistencia_atendida(resultado):
    assert resultado.nc_rd_kn >= resultado.ncsd_kn
    assert resultado.atende_resistencia is True


def test_falha_de_esbeltez_nao_altera_verificacao_de_resistencia():
    loads = replace(CARREGAMENTO, ncsd_kn=1.0, ly_m=4.0)
    resultado = calcular_pilar(PERFIL_W310X21, ACO_A572_GR50, loads)

    assert resultado.esbeltez_max > resultado.limite_esbeltez
    assert resultado.atende_esbeltez is False
    assert resultado.nc_rd_kn >= resultado.ncsd_kn
    assert resultado.atende_resistencia is True
