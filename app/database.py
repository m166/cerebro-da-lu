"""Conexão com o SQLite e criação do schema."""

import sqlite3
from pathlib import Path
from typing import Optional

from app import config, models


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    # Lê config.DB_PATH na chamada (não no import) pra que os testes possam
    # trocar o caminho por um banco temporário.
    conn = sqlite3.connect(db_path or config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    conn = get_connection(db_path)
    for ddl in models.TABELAS:
        conn.execute(ddl)
    conn.commit()
    conn.close()
