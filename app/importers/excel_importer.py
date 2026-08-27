"""Importa ``ELU Compressão.xlsx`` para o catálogo SQLite.

Lê apenas as 3 abas realmente usadas pelo motor de cálculo (as demais —
``Perfis AVA1N2``, ``Perfis CS`` e as abas "Verif ..." — são planilhas de
apoio/memória de cálculo da própria planilha original, não catálogo) e faz
upsert em ``steel_types``, ``profiles_laminados`` e ``profiles_soldados`` por
**nome de coluna**, eliminando o acesso posicional (``v[2]``, ``v[3]``...)
usado pelos scripts originais.

Uso via CLI:

    python -m app.importers.excel_importer "ELU Compressão.xlsx" catalogo.db
"""

from __future__ import annotations

import sys
from pathlib import Path

import openpyxl

from app.db.database import open_database

# Linha (1-based) onde está o cabeçalho de cada aba.
_HEADER_ROW_ACO = 2
_HEADER_ROW_PERFIS = 5

# Mapeia o texto exato do cabeçalho do Excel (com quebras de linha já
# normalizadas para espaço) para o nome de coluna do SQLite.
_COLUNAS_ACO = {
    "Designação": "designacao",
    "Tensão de escoamento, fy (MPa)": "fy_mpa",
    "Tensão última, fu (MPa)": "fu_mpa",
}

_COLUNAS_LAMINADOS = {
    "BITOLA mm x kg/m": "bitola",
    "Massa Linear kg/m": "massa_linear_kgm",
    "d mm": "d_mm",
    "bf mm": "bf_mm",
    "tw mm": "tw_mm",
    "tf mm": "tf_mm",
    "h mm": "h_mm",
    "d' mm": "d_linha_mm",
    "Ag cm2": "ag_cm2",
    "lx cm4": "ix_cm4",
    "Wx cm3": "wx_cm3",
    "rx cm": "rx_cm",
    "Zx cm3": "zx_cm3",
    "ly cm4": "iy_cm4",
    "Wy cm3": "wy_cm3",
    "ry cm": "ry_cm",
    "Zy cm3": "zy_cm3",
    "rt cm": "rt_cm",
    "lt cm4": "j_cm4",
    "Mesa: λf bf/2.tf": "lambda_f",
    "Alma: λw d'/tw": "lambda_w",
    "Cw cm6": "cw_cm6",
    "u m2/m": "u_m2m",
    "BITOLA in x Ib/ft": "bitola_in",
}

_COLUNAS_SOLDADOS = {
    "BITOLA mm x kg/m": "bitola",
    "Massa Linear kg/m": "massa_linear_kgm",
    "A cm²": "ag_cm2",
    "d mm": "d_mm",
    "tw mm": "tw_mm",
    "h mm": "h_mm",
    "tf mm": "tf_mm",
    "bf mm": "bf_mm",
    "Ix cm4": "ix_cm4",
    "Wx cm³": "wx_cm3",
    "rx cm": "rx_cm",
    "Zx cm³": "zx_cm3",
    "Iy cm4": "iy_cm4",
    "Wy cm³": "wy_cm3",
    "ry cm": "ry_cm",
    "Zy cm³": "zy_cm3",
    "rt cm": "rt_cm",
    "It cm4": "j_cm4",
    "Cw cm5": "cw_cm5",
    "h/tw": "h_tw",
    "b/2tf": "b_2tf",
    "d/Af cm-1": "d_af_cm_1",
    "ec mm": "ec_mm",
    "u m²/m": "u_m2m",
    "u/A m-¹": "u_a_m_1",
}


def _normalize_header(value: object) -> str:
    return " ".join(str(value).split()) if value is not None else ""


def _read_sheet_rows(
    workbook: openpyxl.Workbook, sheet_name: str, header_row: int, column_map: dict[str, str]
) -> list[dict[str, object]]:
    sheet = workbook[sheet_name]
    header_cells = next(sheet.iter_rows(min_row=header_row, max_row=header_row))
    headers = [_normalize_header(cell.value) for cell in header_cells]

    unmapped = [h for h in headers if h and h not in column_map]
    if unmapped:
        raise ValueError(
            f"Coluna(s) não mapeada(s) na aba '{sheet_name}': {unmapped}. "
            "Atualize o dicionário de colunas em excel_importer.py."
        )

    records: list[dict[str, object]] = []
    for row in sheet.iter_rows(min_row=header_row + 1, values_only=True):
        if all(v is None for v in row):
            continue
        record: dict[str, object] = {}
        for header, value in zip(headers, row):
            column = column_map.get(header)
            if column:
                record[column] = value
        if record.get("bitola") is None and record.get("designacao") is None:
            continue
        records.append(record)
    return records


def import_from_excel(xlsx_path: str | Path, db_path: str | Path) -> dict[str, int]:
    """Importa as 3 abas de catálogo do Excel para o SQLite em ``db_path``.

    Retorna a contagem de linhas importadas por tabela, útil para conferência
    (via CLI ou pela UI, que pode exibir um resumo após o import).
    """

    workbook = openpyxl.load_workbook(str(xlsx_path), data_only=True)
    conn = open_database(db_path)

    counts = {"steel_types": 0, "profiles_laminados": 0, "profiles_soldados": 0}
    try:
        acos = _read_sheet_rows(workbook, "Tipos de aço", _HEADER_ROW_ACO, _COLUNAS_ACO)
        for row in acos:
            conn.execute(
                """
                INSERT INTO steel_types (designacao, fy_mpa, fu_mpa)
                VALUES (:designacao, :fy_mpa, :fu_mpa)
                ON CONFLICT(designacao) DO UPDATE SET
                    fy_mpa = excluded.fy_mpa, fu_mpa = excluded.fu_mpa
                """,
                row,
            )
        counts["steel_types"] = len(acos)

        laminados = _read_sheet_rows(workbook, "Perfis W e HP", _HEADER_ROW_PERFIS, _COLUNAS_LAMINADOS)
        for row in laminados:
            columns = list(row.keys())
            placeholders = ", ".join(f":{c}" for c in columns)
            update_clause = ", ".join(f"{c} = excluded.{c}" for c in columns if c != "bitola")
            conn.execute(
                f"""
                INSERT INTO profiles_laminados ({", ".join(columns)})
                VALUES ({placeholders})
                ON CONFLICT(bitola) DO UPDATE SET {update_clause}
                """,
                row,
            )
        counts["profiles_laminados"] = len(laminados)

        soldados = _read_sheet_rows(workbook, "PerfilCS", _HEADER_ROW_PERFIS, _COLUNAS_SOLDADOS)
        for row in soldados:
            columns = list(row.keys())
            placeholders = ", ".join(f":{c}" for c in columns)
            update_clause = ", ".join(f"{c} = excluded.{c}" for c in columns if c != "bitola")
            conn.execute(
                f"""
                INSERT INTO profiles_soldados ({", ".join(columns)})
                VALUES ({placeholders})
                ON CONFLICT(bitola) DO UPDATE SET {update_clause}
                """,
                row,
            )
        counts["profiles_soldados"] = len(soldados)

        conn.commit()
    finally:
        conn.close()

    return counts


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 2:
        print("Uso: python -m app.importers.excel_importer <caminho.xlsx> <catalogo.db>")
        return 1

    xlsx_path, db_path = argv
    counts = import_from_excel(xlsx_path, db_path)
    print(f"Importação concluída em '{db_path}':")
    for table, count in counts.items():
        print(f"  {table}: {count} linha(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
