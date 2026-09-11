"""Repositórios CRUD sobre o catálogo SQLite (``app/db``).

Cada repositório converte linhas de tabela (``sqlite3.Row``) em/para os
dataclasses de :mod:`app.domain.models`, mantendo o SQL isolado da UI e do
motor de cálculo. ``ProfileRepository`` também resolve a diferença de esquema
entre perfis laminados e soldados (a coluna ``d_linha_mm`` só existe na
tabela de laminados; para soldados, ``d' = h`` é sintetizado aqui).
"""

from __future__ import annotations

import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone

from app.domain.models import LoadCase, Profile, ProfileFamily, SteelType

_LAMINADOS_COLUMNS = (
    "bitola",
    "massa_linear_kgm",
    "d_mm",
    "bf_mm",
    "tw_mm",
    "tf_mm",
    "h_mm",
    "d_linha_mm",
    "ag_cm2",
    "ix_cm4",
    "wx_cm3",
    "rx_cm",
    "zx_cm3",
    "iy_cm4",
    "wy_cm3",
    "ry_cm",
    "zy_cm3",
    "rt_cm",
    "j_cm4",
    "lambda_f",
    "lambda_w",
    "cw_cm6",
    "u_m2m",
    "bitola_in",
)

_SOLDADOS_COLUMNS = (
    "bitola",
    "massa_linear_kgm",
    "ag_cm2",
    "d_mm",
    "tw_mm",
    "h_mm",
    "tf_mm",
    "bf_mm",
    "ix_cm4",
    "wx_cm3",
    "rx_cm",
    "zx_cm3",
    "iy_cm4",
    "wy_cm3",
    "ry_cm",
    "zy_cm3",
    "rt_cm",
    "j_cm4",
    "cw_cm5",
    "h_tw",
    "b_2tf",
    "d_af_cm_1",
    "ec_mm",
    "u_m2m",
    "u_a_m_1",
)


class SteelTypeRepository:
    """CRUD sobre a tabela ``steel_types``."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list_all(self) -> list[SteelType]:
        # Sem ORDER BY designacao (alfabetico): preserva a ordem de insercao
        # (rowid), que segue o agrupamento por familia da planilha original.
        rows = self._conn.execute(
            "SELECT designacao, fy_mpa, fu_mpa FROM steel_types ORDER BY rowid"
        ).fetchall()
        return [SteelType(designacao=r["designacao"], fy_mpa=r["fy_mpa"], fu_mpa=r["fu_mpa"]) for r in rows]

    def get(self, designacao: str) -> SteelType | None:
        row = self._conn.execute(
            "SELECT designacao, fy_mpa, fu_mpa FROM steel_types WHERE designacao = ?",
            (designacao,),
        ).fetchone()
        if row is None:
            return None
        return SteelType(designacao=row["designacao"], fy_mpa=row["fy_mpa"], fu_mpa=row["fu_mpa"])

    def upsert(self, steel: SteelType) -> None:
        self._conn.execute(
            """
            INSERT INTO steel_types (designacao, fy_mpa, fu_mpa)
            VALUES (:designacao, :fy_mpa, :fu_mpa)
            ON CONFLICT(designacao) DO UPDATE SET
                fy_mpa = excluded.fy_mpa,
                fu_mpa = excluded.fu_mpa
            """,
            asdict(steel),
        )
        self._conn.commit()

    def delete(self, designacao: str) -> None:
        self._conn.execute("DELETE FROM steel_types WHERE designacao = ?", (designacao,))
        self._conn.commit()


class ProfileRepository:
    """CRUD sobre ``profiles_laminados``/``profiles_soldados``, unificado em ``Profile``."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list_all(self, family: ProfileFamily | None = None) -> list[Profile]:
        profiles: list[Profile] = []
        if family in (None, ProfileFamily.LAMINADO):
            profiles.extend(self._list_laminados())
        if family in (None, ProfileFamily.SOLDADO):
            profiles.extend(self._list_soldados())
        return sorted(profiles, key=lambda p: p.bitola)

    def get(self, bitola: str, family: ProfileFamily) -> Profile | None:
        # Comparação por igualdade, não identidade: `family` normalmente vem de
        # QComboBox.currentData(), e o PySide6 desempacota um Enum(str, Enum)
        # de volta como `str` puro (perde a identidade do membro, mas não o
        # valor) ao passar pelo QVariant. `is` faria isso cair sempre no ramo
        # "soldado".
        if family == ProfileFamily.LAMINADO:
            row = self._conn.execute(
                "SELECT * FROM profiles_laminados WHERE bitola = ?", (bitola,)
            ).fetchone()
            return self._row_to_laminado(row) if row else None
        row = self._conn.execute(
            "SELECT * FROM profiles_soldados WHERE bitola = ?", (bitola,)
        ).fetchone()
        return self._row_to_soldado(row) if row else None

    def upsert(self, profile: Profile, extra_columns: dict[str, object] | None = None) -> None:
        """Insere/atualiza um perfil.

        ``extra_columns`` permite preservar colunas informativas do Excel que
        não fazem parte do :class:`Profile` (ex.: ``wx_cm3``, ``zx_cm3``) ao
        editar um perfil pela UI; quando omitido, essas colunas ficam ``NULL``
        em uma inserção nova e são preservadas em uma atualização feita via
        SQL parcial (não é o caminho usado aqui, que sempre reescreve a linha
        inteira das colunas do domínio).
        """

        extra = extra_columns or {}
        if profile.family == ProfileFamily.LAMINADO:
            values = {
                "bitola": profile.bitola,
                "d_mm": profile.d_mm,
                "bf_mm": profile.bf_mm,
                "tw_mm": profile.tw_mm,
                "tf_mm": profile.tf_mm,
                "h_mm": profile.h_mm,
                "d_linha_mm": profile.d_linha_mm,
                "ag_cm2": profile.ag_cm2,
                "ix_cm4": profile.ix_cm4,
                "rx_cm": profile.rx_cm,
                "iy_cm4": profile.iy_cm4,
                "ry_cm": profile.ry_cm,
                "j_cm4": profile.j_cm4,
                "cw_cm6": profile.cw_cm6,
                **{k: v for k, v in extra.items() if k in _LAMINADOS_COLUMNS},
            }
            columns = list(values.keys())
            placeholders = ", ".join(f":{c}" for c in columns)
            update_clause = ", ".join(f"{c} = excluded.{c}" for c in columns if c != "bitola")
            self._conn.execute(
                f"""
                INSERT INTO profiles_laminados ({", ".join(columns)})
                VALUES ({placeholders})
                ON CONFLICT(bitola) DO UPDATE SET {update_clause}
                """,
                values,
            )
        else:
            values = {
                "bitola": profile.bitola,
                "ag_cm2": profile.ag_cm2,
                "d_mm": profile.d_mm,
                "tw_mm": profile.tw_mm,
                "h_mm": profile.h_mm,
                "tf_mm": profile.tf_mm,
                "bf_mm": profile.bf_mm,
                "ix_cm4": profile.ix_cm4,
                "rx_cm": profile.rx_cm,
                "iy_cm4": profile.iy_cm4,
                "ry_cm": profile.ry_cm,
                "j_cm4": profile.j_cm4,
                "cw_cm5": profile.cw_cm6,
                "ec_mm": profile.ec_mm,
                **{k: v for k, v in extra.items() if k in _SOLDADOS_COLUMNS},
            }
            columns = list(values.keys())
            placeholders = ", ".join(f":{c}" for c in columns)
            update_clause = ", ".join(f"{c} = excluded.{c}" for c in columns if c != "bitola")
            self._conn.execute(
                f"""
                INSERT INTO profiles_soldados ({", ".join(columns)})
                VALUES ({placeholders})
                ON CONFLICT(bitola) DO UPDATE SET {update_clause}
                """,
                values,
            )
        self._conn.commit()

    def delete(self, bitola: str, family: ProfileFamily) -> None:
        table = "profiles_laminados" if family == ProfileFamily.LAMINADO else "profiles_soldados"
        self._conn.execute(f"DELETE FROM {table} WHERE bitola = ?", (bitola,))
        self._conn.commit()

    def _list_laminados(self) -> list[Profile]:
        rows = self._conn.execute("SELECT * FROM profiles_laminados ORDER BY bitola").fetchall()
        return [self._row_to_laminado(r) for r in rows]

    def _list_soldados(self) -> list[Profile]:
        rows = self._conn.execute("SELECT * FROM profiles_soldados ORDER BY bitola").fetchall()
        return [self._row_to_soldado(r) for r in rows]

    @staticmethod
    def _row_to_laminado(row: sqlite3.Row) -> Profile:
        return Profile(
            bitola=row["bitola"],
            family=ProfileFamily.LAMINADO,
            d_mm=row["d_mm"],
            bf_mm=row["bf_mm"],
            tw_mm=row["tw_mm"],
            tf_mm=row["tf_mm"],
            h_mm=row["h_mm"],
            d_linha_mm=row["d_linha_mm"],
            ag_cm2=row["ag_cm2"],
            ix_cm4=row["ix_cm4"],
            rx_cm=row["rx_cm"],
            iy_cm4=row["iy_cm4"],
            ry_cm=row["ry_cm"],
            j_cm4=row["j_cm4"],
            cw_cm6=row["cw_cm6"],
        )

    @staticmethod
    def _row_to_soldado(row: sqlite3.Row) -> Profile:
        # A tabela de soldados não tem coluna d_linha_mm: perfis soldados não
        # têm raio de concordância (canto vivo), então d' = h por definição
        # (ver Profile.raio_concordancia_mm e CodigocomPDF.py original).
        return Profile(
            bitola=row["bitola"],
            family=ProfileFamily.SOLDADO,
            d_mm=row["d_mm"],
            bf_mm=row["bf_mm"],
            tw_mm=row["tw_mm"],
            tf_mm=row["tf_mm"],
            h_mm=row["h_mm"],
            d_linha_mm=row["h_mm"],
            ag_cm2=row["ag_cm2"],
            ix_cm4=row["ix_cm4"],
            rx_cm=row["rx_cm"],
            iy_cm4=row["iy_cm4"],
            ry_cm=row["ry_cm"],
            j_cm4=row["j_cm4"],
            cw_cm6=row["cw_cm5"],
            ec_mm=row["ec_mm"] or 0.0,
        )


class ProjectRepository:
    """CRUD sobre ``projects``. Guarda apenas os dados de entrada de cada caso.

    O resultado (``DesignResult``) nunca é persistido: é sempre recalculado a
    partir do perfil/aço atuais do catálogo quando o projeto é aberto (ver
    ``app/domain/calculations.calcular_pilar``). Assim, editar um perfil no
    catálogo atualiza automaticamente todos os projetos que o referenciam.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list_all(self) -> list[sqlite3.Row]:
        return self._conn.execute("SELECT * FROM projects ORDER BY atualizado_em DESC").fetchall()

    def get(self, project_id: int) -> sqlite3.Row | None:
        return self._conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()

    def create(
        self,
        nome: str,
        autor: str | None,
        family: ProfileFamily,
        bitola: str,
        steel_designacao: str,
        loads: LoadCase,
        observacoes: str | None = None,
    ) -> int:
        now = _now_iso()
        cursor = self._conn.execute(
            """
            INSERT INTO projects (
                nome, autor, criado_em, atualizado_em, family, bitola,
                steel_designacao, ea_gpa, ga_gpa, ncsd_kn,
                kx, lx_m, ky, ly_m, kz, lz_m, observacoes
            ) VALUES (
                :nome, :autor, :criado_em, :atualizado_em, :family, :bitola,
                :steel_designacao, :ea_gpa, :ga_gpa, :ncsd_kn,
                :kx, :lx_m, :ky, :ly_m, :kz, :lz_m, :observacoes
            )
            """,
            {
                "nome": nome,
                "autor": autor,
                "criado_em": now,
                "atualizado_em": now,
                "family": family.value,
                "bitola": bitola,
                "steel_designacao": steel_designacao,
                "ea_gpa": loads.ea_gpa,
                "ga_gpa": loads.ga_gpa,
                "ncsd_kn": loads.ncsd_kn,
                "kx": loads.kx,
                "lx_m": loads.lx_m,
                "ky": loads.ky,
                "ly_m": loads.ly_m,
                "kz": loads.kz,
                "lz_m": loads.lz_m,
                "observacoes": observacoes,
            },
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def update(
        self,
        project_id: int,
        nome: str,
        autor: str | None,
        family: ProfileFamily,
        bitola: str,
        steel_designacao: str,
        loads: LoadCase,
        observacoes: str | None = None,
    ) -> None:
        self._conn.execute(
            """
            UPDATE projects SET
                nome = :nome, autor = :autor, atualizado_em = :atualizado_em,
                family = :family, bitola = :bitola, steel_designacao = :steel_designacao,
                ea_gpa = :ea_gpa, ga_gpa = :ga_gpa, ncsd_kn = :ncsd_kn,
                kx = :kx, lx_m = :lx_m, ky = :ky, ly_m = :ly_m, kz = :kz, lz_m = :lz_m,
                observacoes = :observacoes
            WHERE id = :id
            """,
            {
                "id": project_id,
                "nome": nome,
                "autor": autor,
                "atualizado_em": _now_iso(),
                "family": family.value,
                "bitola": bitola,
                "steel_designacao": steel_designacao,
                "ea_gpa": loads.ea_gpa,
                "ga_gpa": loads.ga_gpa,
                "ncsd_kn": loads.ncsd_kn,
                "kx": loads.kx,
                "lx_m": loads.lx_m,
                "ky": loads.ky,
                "ly_m": loads.ly_m,
                "kz": loads.kz,
                "lz_m": loads.lz_m,
                "observacoes": observacoes,
            },
        )
        self._conn.commit()

    def delete(self, project_id: int) -> None:
        self._conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        self._conn.commit()

    @staticmethod
    def load_case_from_row(row: sqlite3.Row) -> LoadCase:
        return LoadCase(
            ncsd_kn=row["ncsd_kn"],
            kx=row["kx"],
            lx_m=row["lx_m"],
            ky=row["ky"],
            ly_m=row["ly_m"],
            kz=row["kz"],
            lz_m=row["lz_m"],
            ea_gpa=row["ea_gpa"],
            ga_gpa=row["ga_gpa"],
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
