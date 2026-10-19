"""Motor de cálculo: compressão axial conforme NBR 8800:2024.

Extraído sem alteração de fórmula de ``Codigocompleto.py`` / ``CodigocomPDF.py``
— apenas trocando o acesso posicional (``v[2]``, ``v[3]``, ...) pelos campos
nomeados de :class:`~app.domain.models.Profile`/``SteelType``/``LoadCase``, e
substituindo os ``print`` por um :class:`~app.domain.models.DesignResult`.

Nenhuma regra de negócio nova é introduzida aqui: o objetivo é que, para o
mesmo perfil/aço/carregamento, este módulo produza exatamente os mesmos
números que os scripts originais imprimiam.
"""

from __future__ import annotations

import math

from app.domain.models import DesignResult, LoadCase, Profile, ProfileFamily, SteelType

LIMITE_ESBELTEZ = 200.0
GAMA_A1 = 1.10


def calcular_pilar(profile: Profile, steel: SteelType, loads: LoadCase) -> DesignResult:
    """Dimensiona um pilar à compressão axial, retornando todos os intermediários.

    Fórmulas de ``CodigocomPDF.py`` para os dois casos
    (laminado/soldado). A resistência e o limite de esbeltez são retornados
    como verificações independentes.
    """

    fy = steel.fy_mpa
    ea_gpa = loads.ea_gpa
    ga_gpa = loads.ga_gpa

    bf = profile.bf_mm
    tw = profile.tw_mm
    tf = profile.tf_mm
    h = profile.h_mm
    d_linha = profile.d_linha_mm
    ag = profile.ag_cm2
    ix = profile.ix_cm4
    rx = profile.rx_cm
    iy = profile.iy_cm4
    ry = profile.ry_cm
    j = profile.j_cm4
    cw = profile.cw_cm6

    # --- 1. Estabilidade global -------------------------------------------------
    esbeltez_x = (loads.kx * loads.lx_m * 100) / rx
    esbeltez_y = (loads.ky * loads.ly_m * 100) / ry
    esbeltez_max = max(esbeltez_x, esbeltez_y)
    atende_esbeltez = esbeltez_max <= LIMITE_ESBELTEZ

    r0 = ((rx**2) + (ry**2)) ** 0.5

    nex = ((math.pi**2) * (ea_gpa * 100) * ix) / ((loads.kx * loads.lx_m * 100) ** 2)
    ney = ((math.pi**2) * (ea_gpa * 100) * iy) / ((loads.ky * loads.ly_m * 100) ** 2)
    nez = (1 / (r0**2)) * (
        ((math.pi**2 * (ea_gpa * 100) * cw) / (loads.kz * loads.lz_m * 100) ** 2)
        + (ga_gpa * 100) * j
    )
    ne_min = min(nex, ney, nez)

    lambda0 = ((ag * (fy / 10)) / ne_min) ** 0.5
    chi = 0.658 ** (lambda0**2) if lambda0 <= 1.5 else 0.877 / (lambda0**2)

    # --- 2. Flambagem local ------------------------------------------------------
    sigma_c = chi * fy
    b_mesa = bf / 2
    bt_mesa = b_mesa / tf

    if profile.family == ProfileFamily.LAMINADO:
        limite_norma_mesa = 0.56 * ((ea_gpa * 1000) / fy) ** 0.5
        c1_m, c2_m = 0.22, 1.49
        bt_alma = d_linha / tw
        altura_ref_alma = d_linha
    else:
        kc = 4.0 / ((h / tw) ** 0.5)
        kc = max(0.35, min(kc, 0.76))
        limite_norma_mesa = 0.64 * ((ea_gpa * 1000 * kc) / fy) ** 0.5
        c1_m, c2_m = 0.22, 1.49
        bt_alma = h / tw
        altura_ref_alma = h

    limite_norma_alma = 1.49 * ((ea_gpa * 1000) / fy) ** 0.5
    c1_a, c2_a = 0.18, 1.31

    limite_efetivo_mesa = limite_norma_mesa / (chi**0.5)
    limite_efetivo_alma = limite_norma_alma / (chi**0.5)

    # Mesa
    sigma_el_mesa = 0.0
    if bt_mesa > limite_efetivo_mesa:
        ocorre_flamb_mesa = True
        sigma_el_mesa = ((c2_m * limite_norma_mesa) / bt_mesa) ** 2 * fy
        raiz_termo_mesa = (sigma_el_mesa / sigma_c) ** 0.5
        bef_mesa = b_mesa * (1 - c1_m * raiz_termo_mesa) * raiz_termo_mesa
    else:
        ocorre_flamb_mesa = False
        bef_mesa = b_mesa

    # Alma
    sigma_el_alma = 0.0
    if bt_alma > limite_efetivo_alma:
        ocorre_flamb_alma = True
        sigma_el_alma = ((c2_a * limite_norma_alma) / bt_alma) ** 2 * fy
        raiz_termo_alma = (sigma_el_alma / sigma_c) ** 0.5
        bef_alma = altura_ref_alma * (1 - c1_a * raiz_termo_alma) * raiz_termo_alma
    else:
        ocorre_flamb_alma = False
        bef_alma = altura_ref_alma

    perda_mesas = 4 * (b_mesa - bef_mesa) * tf
    perda_alma = (altura_ref_alma - bef_alma) * tw
    a_ef_cm2 = ((ag * 100) - perda_mesas - perda_alma) / 100

    # --- 3. Resistência e verificação -----------------------------------------------
    nc_rd = (chi * a_ef_cm2 * (fy / 10)) / GAMA_A1
    ncsd = loads.ncsd_kn
    atende_resistencia = nc_rd >= ncsd

    return DesignResult(
        esbeltez_x=esbeltez_x,
        esbeltez_y=esbeltez_y,
        esbeltez_max=esbeltez_max,
        limite_esbeltez=LIMITE_ESBELTEZ,
        atende_esbeltez=atende_esbeltez,
        r0_cm=r0,
        nex_kn=nex,
        ney_kn=ney,
        nez_kn=nez,
        ne_min_kn=ne_min,
        lambda0=lambda0,
        chi=chi,
        sigma_c_mpa=sigma_c,
        bt_mesa=bt_mesa,
        limite_norma_mesa=limite_norma_mesa,
        limite_efetivo_mesa=limite_efetivo_mesa,
        ocorre_flamb_mesa=ocorre_flamb_mesa,
        b_mesa_mm=b_mesa,
        c1_mesa=c1_m,
        c2_mesa=c2_m,
        sigma_el_mesa_mpa=sigma_el_mesa,
        bef_mesa_mm=bef_mesa,
        bt_alma=bt_alma,
        limite_norma_alma=limite_norma_alma,
        limite_efetivo_alma=limite_efetivo_alma,
        ocorre_flamb_alma=ocorre_flamb_alma,
        b_alma_mm=altura_ref_alma,
        c1_alma=c1_a,
        c2_alma=c2_a,
        sigma_el_alma_mpa=sigma_el_alma,
        bef_alma_mm=bef_alma,
        perda_mesas_cm2=perda_mesas / 100,
        perda_alma_cm2=perda_alma / 100,
        aef_cm2=a_ef_cm2,
        nc_rd_kn=nc_rd,
        ncsd_kn=ncsd,
        atende_resistencia=atende_resistencia,
    )
