"""Índice vetorial da base de conhecimento (RAG).

É a infraestrutura do RAG, o análogo de `database.py` pro SQLite: aqui
mora o modelo de embedding e o índice em memória. Quem consulta é o
`repositories.py`.

Carregamento é lazy e em duas etapas (modelo e índice) porque o modelo tem
centenas de MB: importar o app não pode pagar esse custo, e os testes
substituem o encoder por um falso pra nunca baixar nada.
"""

from typing import Callable, List, Optional, Tuple

from app import config
from app.data import conhecimento

_encoder: Optional[Callable] = None
_indice: Optional[Tuple[List[dict], "object"]] = None


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
        textos = [
            config.PREFIXO_DOCUMENTO + conhecimento.texto_indexavel(d) for d in documentos
        ]
        _indice = (documentos, get_encoder()(textos))
    return _indice


def buscar(pergunta: str, k: int = 3, categoria: str = "") -> List[dict]:
    """Busca semântica: devolve os k documentos mais próximos da pergunta.

    Cada resultado carrega o `score` de similaridade (0 a 1) pra que quem
    chama possa descartar resultado fraco.
    """
    if not pergunta.strip():
        return []

    documentos, matriz = get_indice()
    vetor = get_encoder()([config.PREFIXO_PERGUNTA + pergunta])[0]
    similaridades = matriz @ vetor

    candidatos = [
        {**documento, "score": float(score)}
        for documento, score in zip(documentos, similaridades)
        if not categoria or documento["categoria"] == categoria.lower()
    ]
    candidatos.sort(key=lambda d: d["score"], reverse=True)
    return candidatos[:k]
