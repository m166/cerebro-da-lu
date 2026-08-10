"""Conexão com o SQLite e criação do schema."""

import sqlite3
from pathlib import Path
from typing import Optional

from app import config, models


def _conectar(caminho: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(caminho)
    conn.row_factory = sqlite3.Row
    return conn


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    # Lê config.DB_PATH na chamada (não no import) pra que os testes possam
    # trocar o caminho por um banco temporário.
    caminho = db_path or config.DB_PATH

    # Se o arquivo sumiu com o app no ar, o sqlite recria vazio e toda
    # consulta passa a falhar com "no such table" até alguém reiniciar.
    # Recriar o schema aqui custa um stat por conexão e evita esse estado.
    if not Path(caminho).exists():
        conn = _conectar(caminho)
        _criar_tabelas(conn)
        return conn

    return _conectar(caminho)


def _criar_tabelas(conn: sqlite3.Connection) -> None:
    for ddl in models.TABELAS:
        conn.execute(ddl)
    conn.commit()


def init_db(db_path: Optional[Path] = None) -> None:
    conn = get_connection(db_path)
    _criar_tabelas(conn)
    conn.close()
