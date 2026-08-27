"""Conexão com o catálogo SQLite e aplicação do esquema.

O app usa um único arquivo de banco (``catalogo.db`` por padrão, na raiz do
projeto). O esquema é idempotente (``CREATE TABLE IF NOT EXISTS``), então
``ensure_schema`` pode ser chamado toda vez que o app inicia sem apagar dados
existentes.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "catalogo.db"


def get_connection(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Abre (criando se necessário) a conexão com o catálogo SQLite."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Garante que todas as tabelas do esquema existam na conexão dada."""
    ddl = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(ddl)
    conn.commit()


def open_database(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Atalho: abre a conexão e já garante o esquema."""
    conn = get_connection(db_path)
    ensure_schema(conn)
    return conn
