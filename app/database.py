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


def _migrar_perfil(conn: sqlite3.Connection) -> None:
    """Reconstrói `perfil` quando ele ainda tem a chave primária antiga.

    A chave passou de `chave` pra `sessao_id + chave`, e SQLite não altera
    chave primária com ALTER TABLE: é preciso criar a tabela nova, copiar e
    trocar. As linhas antigas ficam sem sessão, e são adotadas depois pelo
    primeiro visitante, junto com o resto dos dados órfãos.
    """
    tabelas = {
        linha["name"]
        for linha in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    colunas = {linha["name"] for linha in conn.execute("PRAGMA table_info(perfil)")}

    # Uma tentativa anterior pode ter renomeado a tabela e morrido antes de
    # copiar. Nesse caso a tabela nova existe vazia e o dado está na antiga,
    # então a recuperação é a mesma coisa: copiar e só então descartar.
    precisa_copiar = models.PERFIL_ANTIGO in tabelas
    if not precisa_copiar:
        if not colunas or "sessao_id" in colunas:
            return
        conn.execute(f"ALTER TABLE perfil RENAME TO {models.PERFIL_ANTIGO}")

    conn.execute(models.CREATE_PERFIL)
    conn.execute(
        f"""
        INSERT OR REPLACE INTO perfil (sessao_id, chave, valor, atualizado_em)
        SELECT NULL, chave, valor, atualizado_em FROM {models.PERFIL_ANTIGO}
        """
    )
    # Só descarta depois de a cópia ter dado certo: a versão anterior deste
    # código descartava sem conferir, e teria perdido o cadastro se a ordem
    # das operações fosse outra.
    copiadas = conn.execute("SELECT COUNT(*) c FROM perfil").fetchone()["c"]
    originais = conn.execute(
        f"SELECT COUNT(*) c FROM {models.PERFIL_ANTIGO}"
    ).fetchone()["c"]
    if copiadas >= originais:
        conn.execute(f"DROP TABLE {models.PERFIL_ANTIGO}")
    conn.commit()


def adotar_dados_orfaos(sessao_id: str) -> None:
    """Entrega ao primeiro visitante os dados gravados antes das sessões.

    Sem isto, quem já usava o app abriria a página e encontraria conversa,
    pedidos e cadastro vazios, porque as linhas antigas não pertencem a
    sessão nenhuma. Acontece uma vez só: depois da primeira adoção não
    sobra linha órfã.
    """
    conn = get_connection()
    for tabela in ("messages", "pedidos", "perfil"):
        conn.execute(
            f"UPDATE {tabela} SET sessao_id = ? WHERE sessao_id IS NULL", (sessao_id,)
        )
    conn.commit()
    conn.close()


def _preparar_schema(conn: sqlite3.Connection) -> None:
    _criar_tabelas(conn)
    _migrar_colunas(conn)
    _migrar_perfil(conn)


def init_db(db_path: Optional[Path] = None) -> None:
    conn = get_connection(db_path)
    _preparar_schema(conn)
    conn.close()
