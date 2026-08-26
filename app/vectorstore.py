"""Índice de busca da base de conhecimento (RAG), agora sobre pgvector.

É a infraestrutura do RAG, o análogo de `database.py`. A busca é **híbrida**:
combina similaridade de embedding com BM25.

Cada sinal tem um papel, e eles não são intercambiáveis:

- **Ordenar é com o embedding.** Ele entende sinônimo e paráfrase, é o
  que liga "minhas costas doem" a "cadeira ergonômica".
- **Filtrar é com o BM25.** O cosseno do E5 vive numa faixa estreita e
  alta, e pergunta fora do domínio chega a 0.86; o BM25 quase zera quando
  nenhum termo bate, o que o torna um separador muito melhor.

A ordenação foi medida: semântica pura acerta 94,2% em 1º lugar contra
92,3% da fusão por posto recíproco (RRF) e 88,5% do BM25 sozinho. Por isso
o ranking é semântico e o BM25 entra só como porta de relevância.

## O que mudou com o Postgres

O vetor deixou de ser uma matriz numpy recriada a cada boot e passou a
morar na tabela `conhecimento_vetores`. Quem manda continua sendo o código:
`data/conhecimento.py` é a fonte da verdade, e a tabela é cache derivado
dele. Editar um documento muda a impressão do texto, e o `_garantir_indice`
reencoda só o que mudou.

Duas decisões que parecem faltar e são deliberadas:

- **A distância é calculada no banco, mas o `LIMIT k` não está no SQL.**
  O `score_fusao` compara a posição de cada documento nos dois rankings, e
  posição só existe olhando o corpus inteiro. Com 40 documentos a consulta
  varre tudo de qualquer jeito, então cortar no Postgres economizaria nada
  e custaria a métrica que serve pra reavaliar a escolha de ordenação.
  Quando o corpus crescer, é aqui que o LIMIT entra, e o `score_fusao` sai.
- **Não há índice HNSW nem IVFFlat.** Com 40 linhas o planejador ignora
  índice vetorial e faz varredura sequencial de qualquer forma; criar um
  seria enfeite que ainda por cima perde recall (ANN é aproximado). O
  gatilho pra criar é o corpus passar de alguns milhares de documentos.
"""

import hashlib
from typing import Callable, List, Optional, Tuple

from app import config
from app.bm25 import IndiceBM25
from app.data import conhecimento
from app.database import get_connection

# Constante da fusão por posto recíproco (RRF). Amortece a diferença entre
# o 1º e o 2º colocado, o que evita que um retriever muito confiante
# atropele o outro.
RRF_K = 60

_encoder: Optional[Callable] = None
_lexical: Optional[Tuple[List[dict], IndiceBM25]] = None
_reindexar = True


def _carregar_encoder() -> Callable:
    from sentence_transformers import SentenceTransformer

    modelo = SentenceTransformer(config.MODELO_EMBEDDING)

    def encode(textos: List[str]):
        # normalize_embeddings deixa o produto escalar já ser a similaridade
        # de cosseno, que é o que o operador <=> do pgvector mede.
        return modelo.encode(textos, normalize_embeddings=True)

    return encode


def get_encoder() -> Callable:
    global _encoder
    if _encoder is None:
        _encoder = _carregar_encoder()
    return _encoder


def definir_encoder(encoder: Optional[Callable]) -> None:
    """Troca o encoder (usado nos testes) e marca o índice pra refazer.

    Refazer é obrigatório, não otimização: vetor gravado por outro encoder
    continua com a mesma impressão de texto, então sem esta marca a busca
    compararia a pergunta de um modelo com os documentos de outro.
    """
    global _encoder, _lexical, _reindexar
    _encoder = encoder
    _lexical = None
    _reindexar = True


def _impressao(documento: dict, texto: str) -> str:
    """Identifica o conteúdo indexado de um documento.

    A categoria entra junto porque ela é filtro na consulta: mudar só a
    categoria não mexeria no texto, e a linha ficaria com o filtro velho.
    """
    bruto = f"{documento['categoria']}|{texto}"
    return hashlib.sha256(bruto.encode()).hexdigest()


def _literal(vetor) -> str:
    """Formato que o pgvector lê num cast `::vector`.

    Evita depender do pacote `pgvector` só pra serializar uma lista.
    """
    return "[" + ",".join(repr(float(v)) for v in vetor) + "]"


def _indice_lexical() -> Tuple[List[dict], IndiceBM25]:
    """O BM25 continua em memória: é léxico, é barato e não é o que ordena."""
    global _lexical
    if _lexical is None:
        documentos = conhecimento.DOCUMENTOS
        textos = [conhecimento.texto_indexavel(d) for d in documentos]
        _lexical = (documentos, IndiceBM25(textos))
    return _lexical


def _garantir_indice(conn) -> None:
    """Deixa `conhecimento_vetores` igual ao corpus, encodando só a diferença.

    É o que substitui o "reencoda tudo a cada boot" da versão em memória.

    É chamado na busca, não no `init_db`, pra não perder o carregamento
    preguiçoso: subir o app não pode pagar o download de centenas de MB do
    modelo de embedding, e nos testes o encoder é trocado por um falso
    depois que o banco já foi criado.
    """
    global _reindexar

    documentos = conhecimento.DOCUMENTOS
    textos = [conhecimento.texto_indexavel(d) for d in documentos]
    impressoes = {
        d["id"]: _impressao(d, texto) for d, texto in zip(documentos, textos)
    }

    guardadas = {}
    if not _reindexar:
        guardadas = {
            linha["documento_id"]: linha["impressao"]
            for linha in conn.execute(
                "SELECT documento_id, impressao FROM conhecimento_vetores"
            ).fetchall()
        }

    pendentes = [
        (documento, texto)
        for documento, texto in zip(documentos, textos)
        if guardadas.get(documento["id"]) != impressoes[documento["id"]]
    ]

    if pendentes:
        vetores = get_encoder()(
            [config.PREFIXO_DOCUMENTO + texto for _, texto in pendentes]
        )
        for (documento, texto), vetor in zip(pendentes, vetores):
            conn.execute(
                """
                INSERT INTO conhecimento_vetores (documento_id, impressao, vetor)
                VALUES (%s, %s, %s::vector)
                ON CONFLICT (documento_id) DO UPDATE
                    SET impressao = excluded.impressao, vetor = excluded.vetor
                """,
                (documento["id"], impressoes[documento["id"]], _literal(vetor)),
            )

    # Documento removido do corpus precisa sair do índice, senão a busca
    # devolveria um id que `conhecimento.py` não conhece mais.
    conn.execute(
        "DELETE FROM conhecimento_vetores WHERE documento_id <> ALL(%s)",
        (list(impressoes),),
    )
    conn.commit()
    _reindexar = False


def sincronizar_indice() -> None:
    """Reindexa fora de uma busca, pra aquecer o índice sem depender de tráfego."""
    conn = get_connection()
    try:
        _garantir_indice(conn)
    finally:
        conn.close()


def _postos(valores: List[float]) -> List[int]:
    """Posição de cada item no ranking (1 = melhor)."""
    ordem = sorted(range(len(valores)), key=lambda i: -valores[i])
    postos = [0] * len(valores)
    for posicao, indice in enumerate(ordem, start=1):
        postos[indice] = posicao
    return postos


def buscar(pergunta: str, k: int = 3, categoria: str = "") -> List[dict]:
    """Busca híbrida: devolve os k documentos mais próximos da pergunta.

    Cada resultado carrega `score` (similaridade de cosseno, vinda do
    pgvector) e `score_lexical` (BM25). Quem chama decide o que fazer com
    eles, o corte por relevância mora no service.
    """
    if not pergunta.strip():
        return []

    documentos, indice_lexical = _indice_lexical()

    conn = get_connection()
    try:
        # Indexar vem antes de encodar a pergunta: o corpus precisa estar no
        # banco pelo mesmo encoder que vai ler a pergunta.
        _garantir_indice(conn)
        vetor = get_encoder()([config.PREFIXO_PERGUNTA + pergunta])[0]
        # `<=>` é distância de cosseno, então a similaridade é 1 menos ela.
        # É o mesmo número que o produto escalar dava antes, porque os
        # vetores saem normalizados do encoder.
        linhas = conn.execute(
            """
            SELECT documento_id, 1 - (vetor <=> %s::vector) AS score
            FROM conhecimento_vetores
            ORDER BY vetor <=> %s::vector
            """,
            (_literal(vetor), _literal(vetor)),
        ).fetchall()
    finally:
        conn.close()

    semanticos = {linha["documento_id"]: float(linha["score"]) for linha in linhas}
    lexicais = indice_lexical.pontuar(pergunta)

    postos_semanticos = _postos([semanticos.get(d["id"], 0.0) for d in documentos])
    postos_lexicais = _postos(lexicais)

    candidatos = []
    for indice, documento in enumerate(documentos):
        if categoria and documento["categoria"] != categoria.lower():
            continue
        candidatos.append(
            {
                **documento,
                "score": semanticos.get(documento["id"], 0.0),
                "score_lexical": float(lexicais[indice]),
                "score_fusao": 1 / (RRF_K + postos_semanticos[indice])
                + 1 / (RRF_K + postos_lexicais[indice]),
            }
        )

    candidatos.sort(key=lambda d: d["score"], reverse=True)
    return candidatos[:k]
