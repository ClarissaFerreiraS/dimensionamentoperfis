"""Equações e tabelas didáticas com valores do motor de cálculo."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import DesignResult, LoadCase, Profile, ProfileFamily, SteelType


@dataclass(frozen=True)
class CalculationBlock:
    title: str
    equations: tuple[str, ...]


@dataclass(frozen=True)
class CalculationStep:
    title: str
    equations: tuple[str, ...] = ()


def _element_block(
    *,
    title: str,
    relation: str,
    dimensions: str,
    bt: float,
    limit: float,
    effective_limit: float,
    occurs: bool,
    sigma_el: float,
    c1: float,
    c2: float,
    width: float,
    effective_width: float,
    limit_formula: str,
    chi: float,
    fy_mpa: float,
) -> CalculationBlock:
    equations = [
        "Ocorre flambagem local" if occurs else "Não ocorre flambagem local",
        f"b/t = {relation} = {dimensions} = {bt:.2f}",
        f"(b/t)lim = {limit_formula} = {limit:.2f}",
        f"(b/t)lim/√χ = {limit:.2f}/√{chi:.4f} = {effective_limit:.2f}",
    ]
    if occurs:
        root = (sigma_el / (chi * fy_mpa)) ** 0.5
        equations.extend(
            (
                f"c₁ = {c1:.2f};  c₂ = {c2:.2f}",
                f"σel = [c₂·(b/t)lim/(b/t)]²·fy = "
                f"[{c2:.2f}·{limit:.2f}/{bt:.2f}]²·{fy_mpa:.2f} "
                f"= {sigma_el:.2f} MPa",
                f"bef = b·(1 − c₁·√[σel/(χfy)])·√[σel/(χfy)]",
                f"bef = {width:.2f}·(1 − {c1:.2f}·{root:.4f})·{root:.4f} "
                f"= {effective_width:.2f} mm",
            )
        )
    else:
        equations.append(f"bef = b = {width:.2f} mm")
    return CalculationBlock(title=title, equations=tuple(equations))


def build_calculation_steps(
    profile: Profile,
    steel: SteelType,
    loads: LoadCase,
    result: DesignResult,
) -> tuple[CalculationStep, ...]:
    """Monta as fórmulas, resultados e tabelas sem repetir descrições extensas."""

    e_mpa = loads.ea_gpa * 1000
    if profile.family == ProfileFamily.LAMINADO:
        alma_relation = "d′/tw"
        alma_dimensions = f"{profile.d_linha_mm:g}/{profile.tw_mm:g}"
        altura_ref_alma = profile.d_linha_mm
        flange_limit_formula = f"0.56·√({e_mpa:.0f}/{steel.fy_mpa:.2f})"
    else:
        alma_relation = "h/tw"
        alma_dimensions = f"{profile.h_mm:g}/{profile.tw_mm:g}"
        altura_ref_alma = profile.h_mm
        h_tw = profile.h_mm / profile.tw_mm
        kc = max(0.35, min(4 / h_tw**0.5, 0.76))
        flange_limit_formula = (
            f"0.64·√({e_mpa:.0f}·{kc:.2f}/{steel.fy_mpa:.2f})"
        )
    alma_limit_formula = f"1.49·√({e_mpa:.0f}/{steel.fy_mpa:.2f})"

    flange = _element_block(
        title="Mesa",
        relation="bf/(2·tf)",
        dimensions=f"{profile.bf_mm:g}/(2·{profile.tf_mm:g})",
        bt=result.bt_mesa,
        limit=result.limite_norma_mesa,
        effective_limit=result.limite_efetivo_mesa,
        occurs=result.ocorre_flamb_mesa,
        sigma_el=result.sigma_el_mesa_mpa,
        c1=result.c1_mesa,
        c2=result.c2_mesa,
        width=result.b_mesa_mm,
        effective_width=result.bef_mesa_mm,
        limit_formula=flange_limit_formula,
        chi=result.chi,
        fy_mpa=steel.fy_mpa,
    )
    web = _element_block(
        title="Alma",
        relation=alma_relation,
        dimensions=alma_dimensions,
        bt=result.bt_alma,
        limit=result.limite_norma_alma,
        effective_limit=result.limite_efetivo_alma,
        occurs=result.ocorre_flamb_alma,
        sigma_el=result.sigma_el_alma_mpa,
        c1=result.c1_alma,
        c2=result.c2_alma,
        width=result.b_alma_mm,
        effective_width=result.bef_alma_mm,
        limit_formula=alma_limit_formula,
        chi=result.chi,
        fy_mpa=steel.fy_mpa,
    )

    return (
        CalculationStep(
            title="1. Esbeltez global",
            equations=(
                f"λx = Kx·Lx·100/rx = {loads.kx:g}·{loads.lx_m:g}·100/"
                f"{profile.rx_cm:g} = {result.esbeltez_x:.2f}",
                f"λy = Ky·Ly·100/ry = {loads.ky:g}·{loads.ly_m:g}·100/"
                f"{profile.ry_cm:g} = {result.esbeltez_y:.2f}",
                f"λmáx = máx(λx, λy) = {result.esbeltez_max:.2f}; "
                f"limite = {result.limite_esbeltez:.0f}",
            ),
        ),
        CalculationStep(
            title="2. Cargas críticas de instabilidade",
            equations=(
                f"Nₑₓ = π²EIₓ/Lx² = π²·{loads.ea_gpa * 100:g}·"
                f"{profile.ix_cm4:g}/{loads.lx_m * 100:g}² "
                f"= {result.nex_kn:.2f} kN",
                f"Nₑy = π²EIᵧ/Ly² = π²·{loads.ea_gpa * 100:g}·"
                f"{profile.iy_cm4:g}/{loads.ly_m * 100:g}² "
                f"= {result.ney_kn:.2f} kN",
                f"Nₑz = [π²ECw/Lz² + GaJ]/r₀² = "
                f"[π²·{loads.ea_gpa * 100:g}·{profile.cw_cm6:g}/"
                f"{loads.lz_m * 100:g}² + "
                f"{loads.ga_gpa * 100:g}·{profile.j_cm4:g}]/{result.r0_cm:.2f}² "
                f"= {result.nez_kn:.2f} kN",
                f"Nₑ = mín(Nₑₓ, Nₑy, Nₑz) = "
                f"mín({result.nex_kn:.2f}, {result.ney_kn:.2f}, "
                f"{result.nez_kn:.2f}) = {result.ne_min_kn:.2f} kN",
            ),
        ),
        CalculationStep(
            title="3. Esbeltez reduzida e fator de redução",
            equations=(
                f"λ₀ = √[Ag·(fy/10)/Nₑ] = √[{profile.ag_cm2:g}·"
                f"({steel.fy_mpa:g}/10)/{result.ne_min_kn:.2f}] "
                f"= {result.lambda0:.4f}",
                f"χ = {'0.658^(λ₀²)' if result.lambda0 <= 1.5 else '0.877/λ₀²'} "
                f"= {result.chi:.4f}",
            ),
        ),
        CalculationStep(
            title="4. Flambagem local",
            equations=(
                flange.title,
                *flange.equations,
                "",
                web.title,
                *web.equations,
            ),
        ),
        CalculationStep(
            title="5. Área efetiva",
            equations=(
                "Aef = Ag − Σ(b − bef)·t",
                f"Aef = {profile.ag_cm2:.2f} − "
                f"[4({result.b_mesa_mm / 10:.2f} − {result.bef_mesa_mm / 10:.2f})·"
                f"{profile.tf_mm / 10:.2f} + ({altura_ref_alma / 10:.2f} − "
                f"{result.bef_alma_mm / 10:.2f})·{profile.tw_mm / 10:.2f}] "
                f"= {result.aef_cm2:.2f} cm²",
            ),
        ),
        CalculationStep(
            title="6. Resistência à compressão",
            equations=(
                f"Nc,Rd = χ·Aef·(fy/10)/γA1 = {result.chi:.4f}·"
                f"{result.aef_cm2:.2f}·({steel.fy_mpa:.2f}/10)/1.10 "
                f"= {result.nc_rd_kn:.2f} kN",
                "Nc,Sd ≤ Nc,Rd" if result.atende_resistencia else "Nc,Sd > Nc,Rd",
            ),
        ),
    )


EXPLANATION_NOTE = (
    "Equações apresentadas para fins educacionais. Consulte a norma oficial "
    "para confirmar a aplicação ao caso estudado."
)
