"""Camada de acesso a dados.

Mensagens e pedidos vêm do SQLite; o catálogo vem do mock em
`app/data/catalogo.py`. Nenhuma regra de negócio mora aqui — só leitura e
escrita.
"""

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

def _match(produto: dict, query: str) -> bool:
    """Casa se todos os termos da busca aparecem em nome, descrição ou categoria."""
    texto = f"{produto['nome']} {produto['descricao']} {produto['categoria']}".lower()
    return all(termo in texto for termo in query.lower().split())


def listar_produtos(query: str = "", categoria: str = "", limite: Optional[int] = None) -> List[dict]:
    resultado = catalogo.PRODUTOS
    if categoria:
        resultado = [p for p in resultado if p["categoria"] == categoria.lower()]
    if query:
        resultado = [p for p in resultado if _match(p, query)]
    return resultado[:limite] if limite else resultado


def obter_produto(produto_id: int) -> Optional[dict]:
    return next((p for p in catalogo.PRODUTOS if p["id"] == produto_id), None)


def listar_categorias() -> List[str]:
    return catalogo.CATEGORIAS


# --- Base de conhecimento (RAG) -------------------------------------------

def buscar_conhecimento(pergunta: str, k: int, categoria: str = "") -> List[dict]:
    return vectorstore.buscar(pergunta, k=k, categoria=categoria)
