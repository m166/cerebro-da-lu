"""Migração de banco que já existe.

`CREATE TABLE IF NOT EXISTS` não altera tabela criada por uma versão
anterior, então quem já usava o app não ganharia as colunas novas: o
`cerebro.db` dele continuaria sem `codigo_rastreio` e toda consulta
quebraria com "no such column".
"""

import sqlite3

import pytest

from app import config, database, models, repositories, services
from app.database import init_db
from tests.conftest import id_por_nome

SCHEMA_ANTIGO = """
CREATE TABLE pedidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id INTEGER NOT NULL,
    produto_nome TEXT NOT NULL,
    quantidade INTEGER NOT NULL,
    valor_total REAL NOT NULL,
    endereco_entrega TEXT,
    status TEXT NOT NULL DEFAULT 'confirmado',
    data_criacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_entrega_agendada TEXT
)
"""

MESSAGES_ANTIGO = """
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""


def _colunas(caminho, tabela):
    conn = sqlite3.connect(caminho)
    nomes = {linha[1] for linha in conn.execute(f"PRAGMA table_info({tabela})")}
    conn.close()
    return nomes


@pytest.fixture
def banco_antigo(tmp_path, monkeypatch):
    """Banco no schema anterior ao rastreio, com um pedido já gravado."""
    caminho = tmp_path / "antigo.db"
    conn = sqlite3.connect(caminho)
    conn.execute(MESSAGES_ANTIGO)
    conn.execute(SCHEMA_ANTIGO)
    conn.execute(
        """
        INSERT INTO pedidos (produto_id, produto_nome, quantidade, valor_total,
                             endereco_entrega, status, data_criacao)
        VALUES (1, 'Notebook Titan X15', 1, 4899.90, 'Rua Antiga, 1',
                'confirmado', '2020-01-01 10:00:00')
        """
    )
    conn.execute("INSERT INTO messages (role, content) VALUES ('user', 'oi')")
    conn.commit()
    conn.close()

    monkeypatch.setattr(config, "DB_PATH", caminho)
    return caminho


def test_banco_antigo_nao_tem_as_colunas_novas(banco_antigo):
    colunas = _colunas(banco_antigo, "pedidos")
    assert "codigo_rastreio" not in colunas
    assert "status_notificado" not in colunas


def test_init_db_acrescenta_as_colunas_que_faltam(banco_antigo):
    init_db()
    assert {"codigo_rastreio", "status_notificado"} <= _colunas(banco_antigo, "pedidos")


def test_migracao_preserva_os_dados(banco_antigo):
    init_db()
    pedido = repositories.obter_pedido(1)
    assert pedido["produto_nome"] == "Notebook Titan X15"
    assert pedido["endereco_entrega"] == "Rua Antiga, 1"
    assert pedido["codigo_rastreio"] is None
    assert repositories.listar_mensagens() == [{"role": "user", "content": "oi", "tipo": "chat"}]


def test_migracao_e_idempotente(banco_antigo):
    init_db()
    init_db()
    assert {"codigo_rastreio", "status_notificado"} <= _colunas(banco_antigo, "pedidos")


def test_migracao_repetida_nao_mexe_nos_dados(banco_antigo):
    """ALTER TABLE repetido estouraria com "duplicate column name" e deixaria
    o commit pela metade."""
    for _ in range(3):
        init_db()

    pedidos = repositories.listar_pedidos()
    assert len(pedidos) == 1
    assert pedidos[0]["produto_nome"] == "Notebook Titan X15"
    assert repositories.listar_mensagens() == [{"role": "user", "content": "oi", "tipo": "chat"}]


def test_migracao_parcial_completa_so_o_que_falta(tmp_path, monkeypatch):
    """Quem atualizou no meio do caminho tem uma coluna nova e não a outra."""
    caminho = tmp_path / "parcial.db"
    conn = sqlite3.connect(caminho)
    conn.execute(MESSAGES_ANTIGO)
    conn.execute(SCHEMA_ANTIGO.replace("data_entrega_agendada TEXT", "data_entrega_agendada TEXT, codigo_rastreio TEXT"))
    conn.execute(
        """
        INSERT INTO pedidos (produto_id, produto_nome, quantidade, valor_total, codigo_rastreio)
        VALUES (1, 'Notebook Titan X15', 1, 4899.90, 'LU000000014BR')
        """
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(config, "DB_PATH", caminho)

    init_db()
    assert {"codigo_rastreio", "status_notificado"} <= _colunas(caminho, "pedidos")
    assert repositories.obter_pedido(1)["codigo_rastreio"] == "LU000000014BR"


def test_migrar_colunas_ignora_tabela_que_nao_existe(tmp_path):
    """PRAGMA de tabela ausente volta vazio, e ALTER TABLE nela estouraria."""
    conn = sqlite3.connect(tmp_path / "sem_tabelas.db")
    conn.row_factory = sqlite3.Row
    database._migrar_colunas(conn)
    conn.close()


def test_pedido_antigo_continua_funcionando(banco_antigo):
    init_db()
    pedido = services.obter_pedido(1)
    assert pedido["codigo_rastreio"] == services.gerar_codigo_rastreio(1)
    assert pedido["status"] == "entregue"

    rastreio = services.rastrear_pedido(1)
    assert rastreio["etapa_atual"] == "entregue"
    assert rastreio["codigo_rastreio"] == pedido["codigo_rastreio"]


def test_pedido_antigo_e_notificado_uma_vez_so(banco_antigo):
    """Linha migrada tem `status_notificado` nulo: nada foi comunicado ainda,
    então vale um aviso do estado atual, e só um."""
    init_db()
    novas = services.sincronizar_notificacoes()
    assert len(novas) == 1
    assert "entregue" in novas[0]["content"]
    assert services.sincronizar_notificacoes() == []


def test_pedido_novo_em_banco_migrado(banco_antigo):
    """Migrar precisa deixar o banco pronto pra escrita também: o INSERT de
    pedido preenche `status_notificado`, coluna que não existia antes."""
    init_db()
    pedido = services.criar_pedido(id_por_nome("Air Fryer 4L Digital"))

    assert pedido["codigo_rastreio"] == services.gerar_codigo_rastreio(pedido["id"])
    assert repositories.obter_pedido(pedido["id"])["status_notificado"] == "confirmado"

    novas = services.sincronizar_notificacoes()
    assert [f"#{pedido['id']}" in n["content"] for n in novas] == [False]


def test_status_gravado_por_versao_antiga_nao_vaza_pro_rastreio(banco_antigo):
    """A versão anterior escrevia "entrega agendada" na coluna status, valor
    que nem existe em ETAPAS_RASTREIO, e o rastreio devolvia isso ao cliente."""
    conn = sqlite3.connect(banco_antigo)
    conn.execute("UPDATE pedidos SET status = 'entrega agendada' WHERE id = 1")
    conn.commit()
    conn.close()

    init_db()
    assert services.obter_pedido(1)["status"] in models.ETAPAS_RASTREIO
    assert services.rastrear_pedido(1)["etapa_atual"] in models.ETAPAS_RASTREIO
    assert services.rastrear_pedido(1)["localizacao"] != "Desconhecida"


def test_banco_novo_ja_nasce_com_as_colunas(tmp_path, monkeypatch):
    caminho = tmp_path / "novo.db"
    monkeypatch.setattr(config, "DB_PATH", caminho)
    init_db()
    assert {"codigo_rastreio", "status_notificado"} <= _colunas(caminho, "pedidos")
