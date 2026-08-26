"""Conexão com o PostgreSQL e criação do schema.

O driver é o psycopg 3. Duas diferenças em relação ao `sqlite3` que estava
aqui antes e que aparecem no código todo:

- **O placeholder é `%s`, não `?`.** Vale pra qualquer parâmetro, inclusive
  o `LIMIT %s` das consultas de histórico.
- **`conn.execute` existe, mas quem tem `.fetchone()` é o cursor.** O
  psycopg devolve cursor nos dois casos, então as chamadas continuam se
  parecendo com as antigas; o que muda é a fábrica de linha, que aqui é
  `dict_row` em vez do `sqlite3.Row`.

A conexão continua sendo aberta e fechada por operação, como no SQLite. Não
virou pool porque o gargalo do app é a chamada ao modelo, não o banco, e
pool com `--reload` esconde erro de conexão atrás de processo reiniciado.
"""

from typing import Optional

import psycopg
from psycopg.rows import dict_row

from app import config, models


def get_connection(dsn: Optional[str] = None) -> psycopg.Connection:
    # Lê config.DATABASE_URL na chamada (não no import) pra que os testes
    # possam apontar pro banco de teste sem recarregar o módulo.
    alvo = dsn or config.DATABASE_URL
    if not alvo:
        # Falha aqui, e não com um padrão conveniente, porque o padrão óbvio
        # (`localhost:5432`) é a porta de um container de trabalho nesta
        # máquina. Conectar no banco errado por comodidade é o tipo de erro
        # que só aparece depois que a tabela já foi truncada.
        raise RuntimeError(
            "DATABASE_URL não configurada. Copie .env.example para .env e "
            "aponte pra um Postgres com a extensão pgvector. Atenção: a porta "
            "5432 desta máquina é usada por outro projeto, escolha outra."
        )
    return psycopg.connect(alvo, row_factory=dict_row)


def _criar_tabelas(conn: psycopg.Connection) -> None:
    # A extensão vem antes das tabelas: o tipo `vector` do índice do RAG só
    # existe depois dela, e `CREATE TABLE` com coluna VECTOR falharia com
    # "type vector does not exist".
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    for ddl in models.TABELAS:
        conn.execute(ddl)
    conn.execute(
        models.CREATE_CONHECIMENTO_VETORES.format(dimensoes=config.DIMENSOES_EMBEDDING)
    )
    conn.commit()


def _migrar_colunas(conn: psycopg.Connection) -> None:
    """Acrescenta colunas novas em banco que já existe.

    O DDL usa `CREATE TABLE IF NOT EXISTS`, que não faz nada quando a tabela
    já foi criada por uma versão anterior: sem isso, um banco já publicado
    continuaria sem `codigo_rastreio` e toda consulta quebraria.

    No SQLite era preciso consultar o `PRAGMA table_info` antes, porque
    `ALTER TABLE ADD COLUMN` repetido estourava com "duplicate column name".
    O Postgres tem `IF NOT EXISTS` no próprio ALTER, então a checagem manual
    saiu. Continua idempotente e roda a cada init_db.
    """
    for tabela, colunas in models.COLUNAS_ADICIONADAS.items():
        existe = conn.execute(
            "SELECT to_regclass(%s) AS tabela", (f"public.{tabela}",)
        ).fetchone()["tabela"]
        if not existe:
            continue
        for nome, tipo in colunas:
            conn.execute(f"ALTER TABLE {tabela} ADD COLUMN IF NOT EXISTS {nome} {tipo}")
    conn.commit()


# As tabelas que pertencem a um visitante, e não à loja. Toda consulta a elas
# filtra por sessão, e toda migração de sessão passa por todas.
# `conhecimento_vetores` não entra: é índice da loja, não dado de cliente.
#
# Esta tupla é a lista de verdade, não uma anotação: a fixture de teste zera
# o que estiver aqui, e a adoção e a transferência percorrem o que estiver
# aqui. Tabela nova de cliente que ficar de fora vaza entre sessões e entre
# testes, e foi assim que `memoria` quase escapou.
TABELAS_DO_VISITANTE = ("messages", "pedidos", "perfil", "memoria")


def adotar_dados_orfaos(sessao_id: str) -> None:
    """Entrega ao primeiro visitante os dados gravados antes das sessões.

    Sem isto, quem já usava o app abriria a página e encontraria conversa,
    pedidos e cadastro vazios, porque as linhas antigas não pertencem a
    sessão nenhuma. Acontece uma vez só: depois da primeira adoção não
    sobra linha órfã.
    """
    conn = get_connection()
    for tabela in TABELAS_DO_VISITANTE:
        conn.execute(
            f"UPDATE {tabela} SET sessao_id = %s WHERE sessao_id IS NULL", (sessao_id,)
        )
    conn.commit()
    conn.close()


def _tem_dados(conn: psycopg.Connection, sessao_id: str) -> bool:
    return any(
        conn.execute(
            f"SELECT 1 FROM {tabela} WHERE sessao_id = %s LIMIT 1", (sessao_id,)
        ).fetchone()
        for tabela in TABELAS_DO_VISITANTE
    )


def transferir_sessao(de: str, para: str) -> bool:
    """Passa conversa, pedidos e cadastro de uma sessão pra outra.

    Existe por causa da virada pra identidade por telefone: quem já usava o
    app tem um cookie com id aleatório, e sem isto abriria a tela, digitaria
    o número e encontraria tudo vazio.

    Quem diz de onde transferir é o cookie antigo do próprio navegador, não
    uma varredura do banco. É a diferença entre mover a conversa certa e
    despejar a de todo mundo no primeiro que digitar um número.

    Só transfere pra número que ainda não tem nada: mesclar dois cadastros
    seria pior do que não migrar, e não dá pra desfazer.
    """
    if de == para:
        return False

    conn = get_connection()
    try:
        if _tem_dados(conn, para) or not _tem_dados(conn, de):
            return False
        for tabela in TABELAS_DO_VISITANTE:
            conn.execute(
                f"UPDATE {tabela} SET sessao_id = %s WHERE sessao_id = %s", (para, de)
            )
        conn.commit()
        return True
    finally:
        conn.close()


def _preparar_schema(conn: psycopg.Connection) -> None:
    _criar_tabelas(conn)
    _migrar_colunas(conn)


def init_db(dsn: Optional[str] = None) -> None:
    conn = get_connection(dsn)
    try:
        _preparar_schema(conn)
    finally:
        conn.close()
