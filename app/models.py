"""Modelo de dados: schema das tabelas e constantes de domínio.

O projeto usa SQLite com SQL puro (sem ORM), então este arquivo guarda o
DDL das tabelas em vez de classes de ORM.
"""

# `tipo` separa o que a Lu respondeu de um aviso automático de pedido. Os
# dois são role "assistant", porque ambos foram ditos por ela e o modelo
# precisa saber que avisou. Sem essa coluna, a única forma de distinguir na
# tela era casar o texto por regex, que quebra calado se a frase mudar.
TIPO_CHAT = "chat"
TIPO_NOTIFICACAO = "notificacao"

CREATE_MESSAGES = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    tipo TEXT NOT NULL DEFAULT 'chat',
    produtos TEXT,
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
    data_entrega_agendada TEXT,
    codigo_rastreio TEXT,
    status_notificado TEXT
)
"""

# Cadastro do cliente. Nome e endereço não podem depender do rolar da
# conversa: a janela de histórico enviada ao modelo é limitada, então o que
# ficou pra trás some. Dado que se repete em todo pedido é cadastro, não
# mensagem.
CREATE_PERFIL = """
CREATE TABLE IF NOT EXISTS perfil (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL,
    atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

TABELAS = (CREATE_MESSAGES, CREATE_PEDIDOS, CREATE_PERFIL)

CAMPOS_PERFIL = ("nome", "endereco")

# Colunas acrescentadas depois que a tabela já existia. `CREATE TABLE IF NOT
# EXISTS` não altera tabela criada por uma versão anterior, então quem abre
# um banco antigo precisa de ALTER TABLE. Formato: tabela -> (coluna, tipo).
COLUNAS_ADICIONADAS = {
    "pedidos": (
        ("codigo_rastreio", "TEXT"),
        ("status_notificado", "TEXT"),
    ),
    "messages": (
        ("tipo", "TEXT NOT NULL DEFAULT 'chat'"),
        # Ids dos produtos citados, em JSON. Sem isso o cartão do produto só
        # existe no envio ao vivo e some quando a página recarrega.
        ("produtos", "TEXT"),
    ),
}

STATUS_INICIAL = "confirmado"

# O status é sempre uma destas etapas. Agendamento de entrega não é status:
# mora em `data_entrega_agendada`, porque um pedido agendado continua
# andando pela logística (é separado, enviado, entregue).
ETAPAS_RASTREIO = [
    "confirmado",
    "em separação",
    "enviado",
    "saiu para entrega",
    "entregue",
]

LOCALIZACOES_MOCK = {
    "confirmado": "Centro de distribuição, Louveira/SP",
    "em separação": "Centro de distribuição, Louveira/SP",
    "enviado": "Centro de triagem, em trânsito",
    "saiu para entrega": "Unidade de entrega local",
    "entregue": "Endereço do cliente",
}

# Código de rastreio no formato dos Correios: 2 letras + 8 dígitos de série
# + 1 dígito verificador + "BR". O DV é calculado de verdade (módulo 11),
# mas a série é derivada do id do pedido: é rastreio mockado, não existe
# objeto postado do outro lado.
PREFIXO_RASTREIO = "LU"
SUFIXO_RASTREIO = "BR"
PESOS_DV_RASTREIO = (8, 6, 4, 2, 3, 5, 9, 7)

# Usado quando o pedido aponta pra um produto que saiu do catálogo mockado.
PRAZO_ENTREGA_PADRAO_DIAS = 7

# O que a Lu manda no chat quando um pedido avança de etapa. O código de
# rastreio só aparece de "enviado" em diante, antes disso não há o que
# rastrear.
MENSAGENS_NOTIFICACAO = {
    "confirmado": "Seu pedido #{id} ({produto}) foi confirmado e já entrou na fila de separação.",
    "em separação": "Seu pedido #{id} ({produto}) está em separação no centro de distribuição.",
    "enviado": "Seu pedido #{id} ({produto}) foi enviado. Código de rastreio: {codigo}",
    "saiu para entrega": (
        "Seu pedido #{id} ({produto}) saiu para entrega e chega hoje. "
        "Código de rastreio: {codigo}"
    ),
    "entregue": "Seu pedido #{id} ({produto}) foi entregue. Qualquer coisa, é só me chamar.",
}

CRITERIOS_SUGESTAO = (
    "melhor_preco",
    "melhor_prazo",
    "melhor_avaliacao",
    "melhor_custo_beneficio",
)
