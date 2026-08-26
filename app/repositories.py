"""Camada de acesso a dados.

Mensagens e pedidos vêm do PostgreSQL; o catálogo vem do mock em
`app/data/catalogo.py`. Nenhuma regra de negócio mora aqui, só leitura e
escrita.

Esta camada é a fronteira que esconde o tipo do banco do resto do app: o
Postgres devolve `datetime` em `data_criacao`, e services, schemas e a tela
falam string desde o SQLite. Converter aqui (`_linha`) mantém a coluna com
tipo de verdade sem espalhar `datetime` por cima de tudo.
"""

import unicodedata
from datetime import datetime, timezone
from typing import List, Optional

from psycopg.types.json import Jsonb

from app import models, sessao, vectorstore
from app.data import catalogo
from app.database import get_connection

# O formato que o SQLite gravava em CURRENT_TIMESTAMP e que o app inteiro
# ainda lê. `services._para_datetime` parseia exatamente isto.
FORMATO_DATA = "%Y-%m-%d %H:%M:%S"


def _valor(valor):
    """Converte o que só o Postgres devolve pro que o app espera.

    Só `datetime` precisa disso. A conversão passa por UTC porque o
    `status_derivado` compara com `datetime.utcnow()`: devolver o horário
    local faria o pedido nascer três horas adiantado e pular etapas.
    """
    if isinstance(valor, datetime):
        if valor.tzinfo is not None:
            valor = valor.astimezone(timezone.utc).replace(tzinfo=None)
        return valor.strftime(FORMATO_DATA)
    return valor


def _linha(row) -> Optional[dict]:
    return {chave: _valor(valor) for chave, valor in row.items()} if row else None


# --- Mensagens ---------------------------------------------------------

def inserir_mensagem(
    role: str,
    content: str,
    tipo: str = models.TIPO_CHAT,
    produtos: Optional[List[int]] = None,
) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO messages (sessao_id, role, content, tipo, produtos)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (sessao.atual(), role, content, tipo, Jsonb(produtos) if produtos else None),
    )
    conn.commit()
    conn.close()


def listar_mensagens(limite: Optional[int] = None) -> List[dict]:
    """Histórico em ordem cronológica. Com `limite`, traz só as últimas."""
    conn = get_connection()
    if limite:
        # A subconsulta precisa de apelido: no SQLite `FROM (SELECT ...)` sem
        # nome passava, no Postgres é erro de sintaxe.
        rows = conn.execute(
            """
            SELECT role, content, tipo, produtos FROM (
                SELECT id, role, content, tipo, produtos FROM messages
                WHERE sessao_id = %s ORDER BY id DESC LIMIT %s
            ) AS ultimas ORDER BY id
            """,
            (sessao.atual(), limite),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT role, content, tipo, produtos FROM messages WHERE sessao_id = %s ORDER BY id",
            (sessao.atual(),),
        ).fetchall()
    conn.close()
    return [
        {
            "role": row["role"],
            "content": row["content"],
            "tipo": row["tipo"],
            # JSONB volta como lista pronta, sem json.loads no caminho.
            "produtos": row["produtos"] or [],
        }
        for row in rows
    ]


def ultima_mensagem_do_cliente() -> Optional[datetime]:
    """Quando o cliente falou pela última vez, em UTC.

    É o relógio da janela de atendimento do WhatsApp, e por isso olha só
    `role = 'user'`: mensagem da Lu não reabre janela nenhuma. Devolve
    `datetime` e não string, ao contrário do resto desta camada, porque quem
    consome faz conta de tempo com ele.
    """
    conn = get_connection()
    row = conn.execute(
        """
        SELECT created_at FROM messages
        WHERE sessao_id = %s AND role = 'user'
        ORDER BY id DESC LIMIT 1
        """,
        (sessao.atual(),),
    ).fetchone()
    conn.close()
    return row["created_at"] if row else None


def momentos_do_cliente() -> List[datetime]:
    """Quando o cliente escreveu, em ordem. É o relógio da detecção de abandono.

    Devolve `datetime` e não string porque quem consome faz conta de tempo.
    Só `role = 'user'`: o ritmo é o dele, e incluir as respostas da Lu
    mediria a velocidade do servidor, não a atenção do cliente.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT created_at FROM messages
        WHERE sessao_id = %s AND role = 'user' ORDER BY id
        """,
        (sessao.atual(),),
    ).fetchall()
    conn.close()
    return [row["created_at"] for row in rows]


# --- Satisfação e sinais de melhoria ---------------------------------------

def registrar_satisfacao(nota: int, comentario: str = "", assunto: str = "") -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO satisfacao (sessao_id, nota, comentario, assunto)
        VALUES (%s, %s, %s, %s)
        """,
        (sessao.atual(), nota, comentario or None, assunto or None),
    )
    conn.commit()
    conn.close()


def registrar_evento(tipo: str, detalhe: Optional[dict] = None) -> None:
    """Anota algo que o sistema observou, pra alimentar o diagnóstico.

    Falha em silêncio de propósito: telemetria não pode derrubar atendimento.
    Se o banco recusar a escrita, o cliente ainda recebe a resposta dele.
    """
    try:
        conn = get_connection()
        conn.execute(
            "INSERT INTO eventos (sessao_id, tipo, detalhe) VALUES (%s, %s, %s)",
            (sessao.atual(), tipo, Jsonb(detalhe) if detalhe else None),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def contar_eventos(tipo: str, desde: Optional[datetime] = None) -> int:
    conn = get_connection()
    if desde:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM eventos WHERE tipo = %s AND criado_em >= %s",
            (tipo, desde),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM eventos WHERE tipo = %s", (tipo,)
        ).fetchone()
    conn.close()
    return row["c"]


def perguntas_sem_resposta(limite: int = 10) -> List[dict]:
    """O que os clientes perguntaram e a base não soube responder.

    Agrupado por pergunta e ordenado por frequência: é a fila de trabalho pra
    escrever documento novo, priorizada por demanda real em vez de palpite.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT detalhe->>'pergunta' AS pergunta, COUNT(*) AS vezes,
               MAX(criado_em) AS ultima
        FROM eventos
        WHERE tipo = %s AND detalhe->>'pergunta' IS NOT NULL
        GROUP BY detalhe->>'pergunta'
        ORDER BY vezes DESC, ultima DESC
        LIMIT %s
        """,
        (models.EVENTO_RAG_SEM_RESPOSTA, limite),
    ).fetchall()
    conn.close()
    return [_linha(row) for row in rows]


def resumo_da_satisfacao(desde: Optional[datetime] = None) -> dict:
    conn = get_connection()
    filtro = "WHERE criado_em >= %s" if desde else ""
    parametros = (desde,) if desde else ()
    row = conn.execute(
        f"""
        SELECT COUNT(*) AS respostas, AVG(nota)::float AS media,
               COUNT(*) FILTER (WHERE nota <= 2) AS insatisfeitos,
               COUNT(*) FILTER (WHERE nota >= 4) AS satisfeitos
        FROM satisfacao {filtro}
        """,
        parametros,
    ).fetchone()
    conn.close()
    return _linha(row)


def notas_baixas(limite: int = 10) -> List[dict]:
    """As reclamações, que é onde mora o que consertar."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT nota, comentario, assunto, criado_em FROM satisfacao
        WHERE nota <= 2 ORDER BY criado_em DESC LIMIT %s
        """,
        (limite,),
    ).fetchall()
    conn.close()
    return [_linha(row) for row in rows]


# --- Cupons ----------------------------------------------------------------

def salvar_cupom(
    codigo: str,
    produto_id: int,
    valor_desconto: float,
    margem_na_emissao: float,
    expira_em: datetime,
    motivo: str = "",
) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO cupons (codigo, sessao_id, produto_id, valor_desconto,
                            margem_na_emissao, motivo, expira_em)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            codigo,
            sessao.atual(),
            produto_id,
            valor_desconto,
            margem_na_emissao,
            motivo or None,
            expira_em,
        ),
    )
    conn.commit()
    conn.close()


def obter_cupom(codigo: str) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM cupons WHERE codigo = %s AND sessao_id = %s",
        (codigo.strip().upper(), sessao.atual()),
    ).fetchone()
    conn.close()
    return _linha(row)


def cupons_da_sessao() -> List[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM cupons WHERE sessao_id = %s ORDER BY criado_em DESC",
        (sessao.atual(),),
    ).fetchall()
    conn.close()
    return [_linha(row) for row in rows]


def marcar_cupom_usado(codigo: str) -> bool:
    """Consome o cupom, e devolve se conseguiu.

    O UPDATE só acerta a linha se ela ainda estiver sem uso, e é o banco que
    decide quem chegou primeiro. Sem essa condição, dois pedidos simultâneos
    resgatariam o mesmo desconto duas vezes.
    """
    conn = get_connection()
    cursor = conn.execute(
        """
        UPDATE cupons SET usado_em = NOW()
        WHERE codigo = %s AND sessao_id = %s AND usado_em IS NULL
          AND expira_em > NOW()
        """,
        (codigo.strip().upper(), sessao.atual()),
    )
    conn.commit()
    usou = cursor.rowcount == 1
    conn.close()
    return usou


# --- Perfil do cliente ----------------------------------------------------

def salvar_perfil(chave: str, valor: str) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO perfil (sessao_id, chave, valor, atualizado_em)
        VALUES (%s, %s, %s, NOW())
        ON CONFLICT (sessao_id, chave) DO UPDATE SET valor = excluded.valor,
                                                     atualizado_em = NOW()
        """,
        (sessao.atual(), chave, valor),
    )
    conn.commit()
    conn.close()


def obter_perfil() -> dict:
    conn = get_connection()
    rows = conn.execute(
        "SELECT chave, valor FROM perfil WHERE sessao_id = %s", (sessao.atual(),)
    ).fetchall()
    conn.close()
    return {row["chave"]: row["valor"] for row in rows}


# --- Memória da conversa ---------------------------------------------------

def salvar_memoria(chave: str, valor: str) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO memoria (sessao_id, chave, valor, atualizado_em)
        VALUES (%s, %s, %s, NOW())
        ON CONFLICT (sessao_id, chave) DO UPDATE SET valor = excluded.valor,
                                                     atualizado_em = NOW()
        """,
        (sessao.atual(), chave, valor),
    )
    conn.commit()
    conn.close()


def obter_memoria() -> dict:
    conn = get_connection()
    rows = conn.execute(
        "SELECT chave, valor FROM memoria WHERE sessao_id = %s", (sessao.atual(),)
    ).fetchall()
    conn.close()
    return {row["chave"]: row["valor"] for row in rows}


def produtos_ja_citados(limite: int = 8) -> List[int]:
    """Ids dos produtos que a Lu já mostrou nesta conversa, do mais recente.

    Sai da coluna que o chat já preenche pra montar os cartões, então não
    depende de o modelo lembrar de anotar nada. Limitado porque o objetivo é
    ela não repetir a mesma indicação, e não recitar a conversa inteira.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT produtos FROM messages
        WHERE sessao_id = %s AND role = 'assistant' AND produtos IS NOT NULL
        ORDER BY id DESC
        """,
        (sessao.atual(),),
    ).fetchall()
    conn.close()

    vistos = []
    for row in rows:
        for produto_id in row["produtos"] or []:
            if produto_id not in vistos:
                vistos.append(produto_id)
        if len(vistos) >= limite:
            break
    return vistos[:limite]


def endereco_do_ultimo_pedido() -> Optional[str]:
    """Serve de padrão pra quem já comprou antes de existir o cadastro."""
    conn = get_connection()
    row = conn.execute(
        """
        SELECT endereco_entrega FROM pedidos
        WHERE sessao_id = %s AND endereco_entrega IS NOT NULL AND endereco_entrega != ''
        ORDER BY id DESC LIMIT 1
        """,
        (sessao.atual(),),
    ).fetchone()
    conn.close()
    return row["endereco_entrega"] if row else None


# --- Pedidos -------------------------------------------------------------

def inserir_pedido(
    produto_id: int,
    produto_nome: str,
    quantidade: int,
    valor_total: float,
    endereco_entrega: str = "",
) -> dict:
    conn = get_connection()
    # RETURNING no lugar do `lastrowid` do SQLite, que o psycopg não tem.
    # É mais confiável de qualquer jeito: vem do próprio INSERT, não de um
    # estado do cursor que a próxima instrução sobrescreve.
    cursor = conn.execute(
        """
        INSERT INTO pedidos (
            sessao_id, produto_id, produto_nome, quantidade, valor_total,
            endereco_entrega, status, status_notificado
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            sessao.atual(),
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
    pedido_id = cursor.fetchone()["id"]
    conn.commit()
    conn.close()
    return obter_pedido(pedido_id)


def obter_pedido(pedido_id: int) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM pedidos WHERE id = %s AND sessao_id = %s",
        (pedido_id, sessao.atual()),
    ).fetchone()
    conn.close()
    return _linha(row)


def listar_pedidos() -> List[dict]:
    """Mais recentes primeiro, é a ordem em que o cliente quer ver."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM pedidos WHERE sessao_id = %s ORDER BY id DESC", (sessao.atual(),)
    ).fetchall()
    conn.close()
    return [_linha(row) for row in rows]


def atualizar_entrega_agendada(pedido_id: int, data_entrega: str) -> Optional[dict]:
    """Agendar não mexe no status: são eixos diferentes (data combinada com o
    cliente x onde o pedido está na logística)."""
    conn = get_connection()
    conn.execute(
        "UPDATE pedidos SET data_entrega_agendada = %s WHERE id = %s AND sessao_id = %s",
        (data_entrega, pedido_id, sessao.atual()),
    )
    conn.commit()
    conn.close()
    return obter_pedido(pedido_id)


def definir_codigo_rastreio(pedido_id: int, codigo: str) -> Optional[dict]:
    conn = get_connection()
    conn.execute(
        "UPDATE pedidos SET codigo_rastreio = %s WHERE id = %s AND sessao_id = %s",
        (codigo, pedido_id, sessao.atual()),
    )
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
        UPDATE pedidos SET status = %s, status_notificado = %s
        WHERE id = %s AND sessao_id = %s
          AND (status_notificado IS NULL OR status_notificado != %s)
        """,
        (status, status, pedido_id, sessao.atual(), status),
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
