"""Modelos de domínio: aço, perfil, dados de carga/comprimento e resultado.

Estes dataclasses são o contrato entre o banco (``repositories.py``), o motor
de cálculo (``calculations.py``), o desenho (``drawing.py``) e a UI/relatório
PDF. Não têm dependência de Qt, fpdf ou sqlite3.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ProfileFamily(str, Enum):
    LAMINADO = "laminado"
    SOLDADO = "soldado"


@dataclass(frozen=True)
class SteelType:
    designacao: str
    fy_mpa: float
    fu_mpa: float


@dataclass(frozen=True)
class Profile:
    """Geometria e propriedades de um perfil (laminado W/HP ou soldado CS).

    Os nomes de campo seguem a convenção da NBR 8800 / dos scripts originais
    (d, bf, tw, tf, h, d', Ag, Ix, rx, Iy, ry, J, Cw), não os rótulos do bloco
    do AutoCAD de referência (W, Wt, Ft, R) — ver README para a justificativa.
    """

    bitola: str
    family: ProfileFamily
    d_mm: float
    bf_mm: float
    tw_mm: float
    tf_mm: float
    h_mm: float
    d_linha_mm: float
    ag_cm2: float
    ix_cm4: float
    rx_cm: float
    iy_cm4: float
    ry_cm: float
    j_cm4: float
    cw_cm6: float

    @property
    def raio_concordancia_mm(self) -> float:
        """Raio de concordância aproximado mesa/alma.

        Para laminados, deriva-se de ``r = (h - d') / 2`` (validado com o
        perfil W150x13: h=138mm, d'=118mm -> r=10mm, valor plausível de
        catálogo). Perfis soldados não têm raio de concordância (canto vivo:
        ``d' = h``), então ``r = 0``.
        """
        return max(0.0, (self.h_mm - self.d_linha_mm) / 2.0)


@dataclass(frozen=True)
class LoadCase:
    """Dados de carregamento e comprimentos de flambagem de um projeto."""

    ncsd_kn: float
    kx: float
    lx_m: float
    ky: float
    ly_m: float
    kz: float
    lz_m: float
    ea_gpa: float = 200.0
    ga_gpa: float = 77.0


@dataclass(frozen=True)
class DesignResult:
    """Todos os valores intermediários e finais do dimensionamento à compressão.

    Carrega tudo que os relatórios de terminal/PDF originais imprimiam, para
    que UI e PDF apenas exibam — sem recalcular nada por conta própria.
    """

    # Esbeltez / estabilidade global
    esbeltez_x: float
    esbeltez_y: float
    esbeltez_max: float
    limite_esbeltez: float
    atende_esbeltez: bool
    r0_cm: float
    nex_kn: float
    ney_kn: float
    nez_kn: float
    ne_min_kn: float
    lambda0: float
    chi: float
    sigma_c_mpa: float

    # Flambagem local - mesa
    bt_mesa: float
    limite_norma_mesa: float
    limite_efetivo_mesa: float
    ocorre_flamb_mesa: bool
    bef_mesa_mm: float

    # Flambagem local - alma
    bt_alma: float
    limite_norma_alma: float
    limite_efetivo_alma: float
    ocorre_flamb_alma: bool
    bef_alma_mm: float

    # Área efetiva / resistência
    perda_mesas_cm2: float
    perda_alma_cm2: float
    aef_cm2: float
    nc_rd_kn: float

    # Veredito
    ncsd_kn: float
    aprovado: bool

    @property
    def taxa_utilizacao(self) -> float:
        return self.ncsd_kn / self.nc_rd_kn if self.nc_rd_kn else float("inf")
