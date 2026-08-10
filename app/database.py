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
        _preparar_schema(conn)
        return conn

    return _conectar(caminho)


def _criar_tabelas(conn: sqlite3.Connection) -> None:
    for ddl in models.TABELAS:
        conn.execute(ddl)
    conn.commit()


def _migrar_colunas(conn: sqlite3.Connection) -> None:
    """Acrescenta colunas novas em banco que já existe.

    O DDL usa `CREATE TABLE IF NOT EXISTS`, que não faz nada quando a tabela
    já foi criada por uma versão anterior: sem isso, o `cerebro.db` de quem
    já usava o app continuaria sem `codigo_rastreio` e toda consulta
    quebraria. É idempotente, roda a cada init_db.
    """
    for tabela, colunas in models.COLUNAS_ADICIONADAS.items():
        existentes = {linha["name"] for linha in conn.execute(f"PRAGMA table_info({tabela})")}
        if not existentes:
            continue
        for nome, tipo in colunas:
            if nome not in existentes:
                conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {nome} {tipo}")
    conn.commit()


def _preparar_schema(conn: sqlite3.Connection) -> None:
    _criar_tabelas(conn)
    _migrar_colunas(conn)


def init_db(db_path: Optional[Path] = None) -> None:
    conn = get_connection(db_path)
    _preparar_schema(conn)
    conn.close()
