"""Camada de acesso a dados.

Mensagens e pedidos vêm do SQLite; o catálogo vem do mock em
`app/data/catalogo.py`. Nenhuma regra de negócio mora aqui — só leitura e
escrita.
"""

import unicodedata
from typing import List, Optional

from app import models, vectorstore
from app.data import catalogo
from app.database import get_connection


# --- Mensagens ---------------------------------------------------------

def inserir_mensagem(role: str, content: str) -> None:
    conn = get_connection()
    conn.execute("INSERT INTO messages (role, content) VALUES (?, ?)", (role, content))
    conn.commit()
    conn.close()


def listar_mensagens() -> List[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT role, content FROM messages ORDER BY id").fetchall()
    conn.close()
    return [{"role": row["role"], "content": row["content"]} for row in rows]


# --- Pedidos -------------------------------------------------------------

def inserir_pedido(
    produto_id: int,
    produto_nome: str,
    quantidade: int,
    valor_total: float,
    endereco_entrega: str = "",
) -> dict:
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO pedidos (produto_id, produto_nome, quantidade, valor_total, endereco_entrega, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (produto_id, produto_nome, quantidade, valor_total, endereco_entrega, models.STATUS_INICIAL),
    )
    conn.commit()
    pedido_id = cursor.lastrowid
    conn.close()
    return obter_pedido(pedido_id)


def obter_pedido(pedido_id: int) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def listar_pedidos() -> List[dict]:
    """Mais recentes primeiro — é a ordem em que o cliente quer ver."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM pedidos ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def atualizar_entrega_agendada(pedido_id: int, data_entrega: str) -> Optional[dict]:
    conn = get_connection()
    conn.execute(
        "UPDATE pedidos SET data_entrega_agendada = ?, status = ? WHERE id = ?",
        (data_entrega, models.STATUS_AGENDADO, pedido_id),
    )
    conn.commit()
    conn.close()
    return obter_pedido(pedido_id)


# --- Catálogo -------------------------------------------------------------

def _sem_acento(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def _termos_casados(produto: dict, termos: List[str]) -> int:
    texto = _sem_acento(f"{produto['nome']} {produto['descricao']} {produto['categoria']}")
    return sum(1 for termo in termos if termo in texto)


def listar_produtos(query: str = "", categoria: str = "", limite: Optional[int] = None) -> List[dict]:
    """Busca por categoria e/ou texto livre.

    Compara sem acento e, quando nenhum produto casa com a frase inteira,
    cai pra casamento parcial ordenado por quantidade de termos. Exigir a
    frase completa deixava a busca quebradiça — "fone cancelamento ruido"
    voltava vazio por causa do acento, e "de ativo" a mais zerava o
    resultado. Devolver vazio faz o modelo gastar rodadas de tool calling
    reformulando a pergunta, e às vezes estourar o limite.
    """
    resultado = catalogo.PRODUTOS
    if categoria:
        resultado = [p for p in resultado if p["categoria"] == categoria.lower()]

    if query:
        termos = [t for t in _sem_acento(query).split() if len(t) > 1]
        if termos:
            completos = [p for p in resultado if _termos_casados(p, termos) == len(termos)]
            if completos:
                resultado = completos
            else:
                parciais = [(p, _termos_casados(p, termos)) for p in resultado]
                parciais = sorted(
                    ((p, n) for p, n in parciais if n > 0), key=lambda item: -item[1]
                )
                resultado = [p for p, _ in parciais]

    return resultado[:limite] if limite else resultado


def obter_produto(produto_id: int) -> Optional[dict]:
    return next((p for p in catalogo.PRODUTOS if p["id"] == produto_id), None)


def listar_categorias() -> List[str]:
    return catalogo.CATEGORIAS


# --- Base de conhecimento (RAG) -------------------------------------------

def buscar_conhecimento(pergunta: str, k: int, categoria: str = "") -> List[dict]:
    return vectorstore.buscar(pergunta, k=k, categoria=categoria)
