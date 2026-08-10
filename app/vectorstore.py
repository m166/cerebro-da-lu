"""Índice de busca da base de conhecimento (RAG).

É a infraestrutura do RAG, o análogo de `database.py` pro SQLite. A busca
é **híbrida**: combina similaridade de embedding com BM25.

Cada sinal tem um papel, e eles não são intercambiáveis:

- **Ordenar é com o embedding.** Ele entende sinônimo e paráfrase — é o
  que liga "minhas costas doem" a "cadeira ergonômica".
- **Filtrar é com o BM25.** O cosseno do E5 vive numa faixa estreita e
  alta, e pergunta fora do domínio chega a 0.86; o BM25 quase zera quando
  nenhum termo bate, o que o torna um separador muito melhor.

A ordenação foi medida: semântica pura acerta 94,2% em 1º lugar contra
92,3% da fusão por posto recíproco (RRF) e 88,5% do BM25 sozinho. Por isso
o ranking é semântico e o BM25 entra só como porta de relevância —
`score_fusao` continua exposto pra quem quiser reavaliar isso com outro
corpus, mas não é o que ordena.

Carregamento é lazy e em duas etapas (modelo e índice) porque o modelo tem
centenas de MB: importar o app não pode pagar esse custo, e os testes
substituem o encoder por um falso pra nunca baixar nada.
"""

from typing import Callable, List, Optional, Tuple

from app import config
from app.bm25 import IndiceBM25
from app.data import conhecimento

# Constante da fusão por posto recíproco (RRF). Amortece a diferença entre
# o 1º e o 2º colocado, o que evita que um retriever muito confiante
# atropele o outro.
RRF_K = 60

_encoder: Optional[Callable] = None
_indice: Optional[Tuple[List[dict], "object", IndiceBM25]] = None


def _carregar_encoder() -> Callable:
    from sentence_transformers import SentenceTransformer

    modelo = SentenceTransformer(config.MODELO_EMBEDDING)

    def encode(textos: List[str]):
        # normalize_embeddings deixa o produto escalar já ser a similaridade
        # de cosseno, o que dispensa dividir pelas normas na busca.
        return modelo.encode(textos, normalize_embeddings=True)

    return encode


def get_encoder() -> Callable:
    global _encoder
    if _encoder is None:
        _encoder = _carregar_encoder()
    return _encoder


def definir_encoder(encoder: Optional[Callable]) -> None:
    """Troca o encoder (usado nos testes) e invalida o índice."""
    global _encoder, _indice
    _encoder = encoder
    _indice = None


def get_indice():
    global _indice
    if _indice is None:
        documentos = conhecimento.DOCUMENTOS
        textos = [conhecimento.texto_indexavel(d) for d in documentos]
        vetores = get_encoder()([config.PREFIXO_DOCUMENTO + t for t in textos])
        _indice = (documentos, vetores, IndiceBM25(textos))
    return _indice


def _postos(valores: List[float]) -> List[int]:
    """Posição de cada item no ranking (1 = melhor)."""
    ordem = sorted(range(len(valores)), key=lambda i: -valores[i])
    postos = [0] * len(valores)
    for posicao, indice in enumerate(ordem, start=1):
        postos[indice] = posicao
    return postos


def buscar(pergunta: str, k: int = 3, categoria: str = "") -> List[dict]:
    """Busca híbrida: devolve os k documentos mais próximos da pergunta.

    Cada resultado carrega `score` (similaridade de cosseno) e
    `score_lexical` (BM25). Quem chama decide o que fazer com eles — o
    corte por relevância mora no service.
    """
    if not pergunta.strip():
        return []

    documentos, matriz, indice_lexical = get_indice()
    vetor = get_encoder()([config.PREFIXO_PERGUNTA + pergunta])[0]
    semanticos = list(matriz @ vetor)
    lexicais = indice_lexical.pontuar(pergunta)

    postos_semanticos = _postos(semanticos)
    postos_lexicais = _postos(lexicais)

    candidatos = []
    for indice, documento in enumerate(documentos):
        if categoria and documento["categoria"] != categoria.lower():
            continue
        candidatos.append(
            {
                **documento,
                "score": float(semanticos[indice]),
                "score_lexical": float(lexicais[indice]),
                "score_fusao": 1 / (RRF_K + postos_semanticos[indice])
                + 1 / (RRF_K + postos_lexicais[indice]),
            }
        )

    candidatos.sort(key=lambda d: d["score"], reverse=True)
    return candidatos[:k]
