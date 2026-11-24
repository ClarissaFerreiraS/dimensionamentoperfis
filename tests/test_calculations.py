"""Testes de regressão do motor de cálculo.

Casos de validação extraídos das abas "Verif W e HP (Gerdau) 2024" e
"Verif Perfis soldados CS 2024" da planilha ``ELU Compressão.xlsx``. Os valores
esperados são os produzidos pela planilha para os perfis W 310 x 21.0 e CS
200x34 com aço ASTM A572 Grau 50, e servem para garantir que a extração para
``app/domain`` não alterou nenhuma fórmula.
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

PERFIL_CS200X34 = Profile(
    bitola="200x34",
    family=ProfileFamily.SOLDADO,
    d_mm=200,
    bf_mm=200,
    tw_mm=6.3,
    tf_mm=8,
    h_mm=184,
    d_linha_mm=184,
    ag_cm2=43.6,
    ix_cm4=3278,
    rx_cm=8.67,
    iy_cm4=1067,
    ry_cm=4.95,
    j_cm4=8,
    cw_cm6=98304,
    ec_mm=5,
)

CARREGAMENTO_CS200X34 = LoadCase(
    ncsd_kn=305,
    kx=1.0,
    lx_m=1.0,
    ky=1.0,
    ly_m=4.5,
    kz=1.0,
    lz_m=5.0,
    ea_gpa=200,
    ga_gpa=77,
)

RESULTADOS_ESPERADOS = {
    PERFIL_W310X21.bitola: {
        "nex_kn": 74535.252437,
        "ney_kn": 1934.442463,
        "nez_kn": 18948.723783,
        "lambda0": 0.696492,
        "chi": 0.816246,
        "esbeltez_max": 52.631579,
        "bt_mesa": 8.859649,
        "b_mesa_mm": 50.5,
        "ocorre_flamb_mesa": False,
        "bef_mesa_mm": 50.5,
        "bt_alma": 53.333333,
        "ocorre_flamb_alma": True,
        "bef_alma_mm": 218.716483,
        "aef_cm2": 24.482541,
        "nc_rd_kn": 626.764068,
    },
    PERFIL_CS200X34.bitola: {
        "nex_kn": 64705.126454,
        "ney_kn": 1040.085718,
        "nez_kn": 1396.767049,
        "lambda0": 1.202592,
        "chi": 0.545900,
        "esbeltez_max": 90.909091,
        "bt_mesa": 12.5,
        "b_mesa_mm": 100,
        "ocorre_flamb_mesa": False,
        "bef_mesa_mm": 100,
        "bt_alma": 29.206349,
        "ocorre_flamb_alma": False,
        "bef_alma_mm": 184,
        "aef_cm2": 43.6,
        "nc_rd_kn": 746.493941,
    },
}

CASOS_DE_CALCULO = (
    pytest.param(PERFIL_W310X21, CARREGAMENTO, id="laminado"),
    pytest.param(PERFIL_CS200X34, CARREGAMENTO_CS200X34, id="soldado"),
)

LY_PARA_FALHA_ESBELTEZ = {
    PERFIL_W310X21.bitola: 4.0,
    PERFIL_CS200X34.bitola: 12.0,
}


@pytest.fixture(
    scope="module",
    params=(
        (PERFIL_W310X21, CARREGAMENTO),
        (PERFIL_CS200X34, CARREGAMENTO_CS200X34),
    ),
    ids=("laminado", "soldado"),
)
def caso_referencia(request):
    perfil, carregamento = request.param
    return perfil, carregamento, RESULTADOS_ESPERADOS[perfil.bitola]


@pytest.fixture(scope="module")
def resultado(caso_referencia):
    perfil, carregamento, _ = caso_referencia
    return calcular_pilar(perfil, ACO_A572_GR50, carregamento)


def test_estabilidade_global(caso_referencia, resultado):
    _, _, esperado = caso_referencia
    assert resultado.nex_kn == pytest.approx(esperado["nex_kn"], rel=1e-4)
    assert resultado.ney_kn == pytest.approx(esperado["ney_kn"], rel=1e-4)
    assert resultado.nez_kn == pytest.approx(esperado["nez_kn"], rel=1e-4)
    assert resultado.lambda0 == pytest.approx(esperado["lambda0"], rel=1e-4)
    assert resultado.chi == pytest.approx(esperado["chi"], rel=1e-4)


def test_limite_esbeltez_atendido(caso_referencia, resultado):
    _, _, esperado = caso_referencia
    assert resultado.esbeltez_max == pytest.approx(esperado["esbeltez_max"], rel=1e-4)
    assert resultado.esbeltez_max <= resultado.limite_esbeltez
    assert resultado.atende_esbeltez is True


def test_flambagem_local_mesa(caso_referencia, resultado):
    _, _, esperado = caso_referencia
    assert resultado.bt_mesa == pytest.approx(esperado["bt_mesa"], rel=1e-4)
    assert resultado.ocorre_flamb_mesa is esperado["ocorre_flamb_mesa"]
    assert resultado.b_mesa_mm == pytest.approx(esperado["b_mesa_mm"])
    assert resultado.bef_mesa_mm == pytest.approx(esperado["bef_mesa_mm"])
    assert resultado.sigma_el_mesa_mpa == 0


def test_flambagem_local_alma(caso_referencia, resultado):
    _, _, esperado = caso_referencia
    assert resultado.bt_alma == pytest.approx(esperado["bt_alma"], rel=1e-4)
    assert resultado.ocorre_flamb_alma is esperado["ocorre_flamb_alma"]
    assert resultado.c1_alma == pytest.approx(0.18)
    assert resultado.c2_alma == pytest.approx(1.31)
    if resultado.ocorre_flamb_alma:
        assert resultado.sigma_el_alma_mpa > 0
    else:
        assert resultado.sigma_el_alma_mpa == 0
    assert resultado.bef_alma_mm == pytest.approx(esperado["bef_alma_mm"], rel=1e-4)


def test_area_efetiva_e_resistencia(caso_referencia, resultado):
    _, _, esperado = caso_referencia
    assert resultado.aef_cm2 == pytest.approx(esperado["aef_cm2"], rel=1e-4)
    assert resultado.nc_rd_kn == pytest.approx(esperado["nc_rd_kn"], rel=1e-4)


def test_verificacao_resistencia_atendida(resultado):
    assert resultado.nc_rd_kn >= resultado.ncsd_kn
    assert resultado.atende_resistencia is True


def test_falha_de_esbeltez_nao_altera_verificacao_de_resistencia(caso_referencia):
    perfil, carregamento, _ = caso_referencia
    loads = replace(
        carregamento,
        ncsd_kn=1.0,
        ly_m=LY_PARA_FALHA_ESBELTEZ[perfil.bitola],
    )
    resultado = calcular_pilar(perfil, ACO_A572_GR50, loads)

    assert resultado.esbeltez_max > resultado.limite_esbeltez
    assert resultado.atende_esbeltez is False
    assert resultado.nc_rd_kn >= resultado.ncsd_kn
    assert resultado.atende_resistencia is True
