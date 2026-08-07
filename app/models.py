"""Modelo de dados: schema das tabelas e constantes de domínio.

O projeto usa SQLite com SQL puro (sem ORM), então este arquivo guarda o
DDL das tabelas em vez de classes de ORM.
"""

CREATE_MESSAGES = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_PEDIDOS = """
CREATE TABLE IF NOT EXISTS pedidos (
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

TABELAS = (CREATE_MESSAGES, CREATE_PEDIDOS)

STATUS_INICIAL = "confirmado"
STATUS_AGENDADO = "entrega agendada"

ETAPAS_RASTREIO = [
    "confirmado",
    "em separação",
    "enviado",
    "saiu para entrega",
    "entregue",
]

LOCALIZACOES_MOCK = {
    "confirmado": "Centro de distribuição — Louveira/SP",
    "em separação": "Centro de distribuição — Louveira/SP",
    "enviado": "Centro de triagem — em trânsito",
    "saiu para entrega": "Unidade de entrega local",
    "entregue": "Endereço do cliente",
    "entrega agendada": "Centro de distribuição — Louveira/SP",
}

CRITERIOS_SUGESTAO = (
    "melhor_preco",
    "melhor_prazo",
    "melhor_avaliacao",
    "melhor_custo_beneficio",
)
