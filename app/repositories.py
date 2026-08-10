"""Camada de acesso a dados.

Mensagens e pedidos vêm do SQLite; o catálogo vem do mock em
`app/data/catalogo.py`. Nenhuma regra de negócio mora aqui, só leitura e
escrita.
"""

import unicodedata
from typing import List, Optional

from app import models, vectorstore
from app.data import catalogo
from app.database import get_connection


# --- Mensagens ---------------------------------------------------------

def inserir_mensagem(role: str, content: str, tipo: str = models.TIPO_CHAT) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO messages (role, content, tipo) VALUES (?, ?, ?)",
        (role, content, tipo),
    )
    conn.commit()
    conn.close()


def listar_mensagens(limite: Optional[int] = None) -> List[dict]:
    """Histórico em ordem cronológica. Com `limite`, traz só as últimas."""
    conn = get_connection()
    if limite:
        rows = conn.execute(
            """
            SELECT role, content, tipo FROM (
                SELECT id, role, content, tipo FROM messages ORDER BY id DESC LIMIT ?
            ) ORDER BY id
            """,
            (limite,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT role, content, tipo FROM messages ORDER BY id"
        ).fetchall()
    conn.close()
    return [
        {"role": row["role"], "content": row["content"], "tipo": row["tipo"]}
        for row in rows
    ]


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
        INSERT INTO pedidos (
            produto_id, produto_nome, quantidade, valor_total, endereco_entrega,
            status, status_notificado
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            produto_id,
            produto_nome,
            quantidade,
            valor_total,
            endereco_entrega,
            models.STATUS_INICIAL,
            # Nasce com o status inicial já dado como comunicado: quem criou o
            # pedido acabou de ver a confirmação, notificar de novo seria eco.
            models.STATUS_INICIAL,
        ),
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
    """Mais recentes primeiro, é a ordem em que o cliente quer ver."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM pedidos ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def atualizar_entrega_agendada(pedido_id: int, data_entrega: str) -> Optional[dict]:
    """Agendar não mexe no status: são eixos diferentes (data combinada com o
    cliente x onde o pedido está na logística)."""
    conn = get_connection()
    conn.execute(
        "UPDATE pedidos SET data_entrega_agendada = ? WHERE id = ?",
        (data_entrega, pedido_id),
    )
    conn.commit()
    conn.close()
    return obter_pedido(pedido_id)


def definir_codigo_rastreio(pedido_id: int, codigo: str) -> Optional[dict]:
    conn = get_connection()
    conn.execute("UPDATE pedidos SET codigo_rastreio = ? WHERE id = ?", (codigo, pedido_id))
    conn.commit()
    conn.close()
    return obter_pedido(pedido_id)


def marcar_status_notificado(pedido_id: int, status: str) -> bool:
    """Tenta reservar o direito de avisar este status. Devolve se conseguiu.

    O UPDATE só acerta a linha se ela ainda não estiver marcada com este
    status, e é o próprio banco que decide quem chegou primeiro. Sem essa
    condição, duas abas fazendo poll ao mesmo tempo liam o mesmo estado
    antigo e gravavam duas vezes a mesma mensagem no histórico.

    Grava também em `status`, pra que a coluna reflita a última etapa
    observada em vez de ficar parada no valor da criação. Quem manda continua
    sendo o status derivado do tempo, isto aqui é cache.
    """
    conn = get_connection()
    cursor = conn.execute(
        """
        UPDATE pedidos SET status = ?, status_notificado = ?
        WHERE id = ? AND (status_notificado IS NULL OR status_notificado != ?)
        """,
        (status, status, pedido_id, status),
    )
    conn.commit()
    reservou = cursor.rowcount == 1
    conn.close()
    return reservou


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
    frase completa deixava a busca quebradiça, "fone cancelamento ruido"
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
