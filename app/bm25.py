"""Índice léxico BM25, em Python puro.

Complementa a busca vetorial. O embedding entende sinônimo e paráfrase,
mas confunde documentos vizinhos ("bateria de smartwatch" com "bateria de
celular") e dá score alto até pra pergunta que não é do domínio. O BM25 é
o oposto: só pontua quando a palavra aparece de verdade, e pesa mais os
termos raros. Onde um erra, o outro costuma acertar.

Sem dependência nova: são umas poucas dezenas de linhas e o corpus tem 40
documentos.
"""

from __future__ import annotations

import math
import re
import unicodedata
from typing import Dict, List

K1 = 1.5
B = 0.75

# Palavras funcionais do português: aparecem em quase todo documento, o
# que já as penalizaria via IDF, mas tirá-las evita que pergunta fora do
# domínio ("quanto é 2 mais 2") pontue só por conta delas.
_VAZIAS = {
    "a", "as", "o", "os", "um", "uma", "uns", "umas", "de", "do", "da", "dos", "das",
    "em", "no", "na", "nos", "nas", "por", "pra", "para", "com", "sem", "que", "qual",
    "quais", "quanto", "quantos", "quanta", "quantas", "e", "ou", "se", "eh", "ser",
    "sao", "esta", "estao", "meu", "minha", "meus", "minhas", "eu", "voce", "me", "mim",
    "isso", "esse", "essa", "este", "esta", "ao", "aos", "as", "mais", "menos", "muito",
    "muita", "pouco", "tem", "ter", "tenho", "vou", "vai", "faz", "fazer", "onde",
    "quando", "como", "porque", "pois", "mas", "ja", "so", "tambem", "entre", "sobre",
}


def tokenizar(texto: str) -> List[str]:
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return [t for t in re.findall(r"[a-z0-9]+", texto) if t not in _VAZIAS and len(t) > 1]


class IndiceBM25:
    def __init__(self, documentos: List[str]):
        self.docs = [tokenizar(d) for d in documentos]
        self.tamanhos = [len(d) for d in self.docs]
        self.media_tamanho = (sum(self.tamanhos) / len(self.docs)) if self.docs else 0.0

        self.frequencias: List[Dict[str, int]] = []
        aparicoes: Dict[str, int] = {}
        for tokens in self.docs:
            freq: Dict[str, int] = {}
            for token in tokens:
                freq[token] = freq.get(token, 0) + 1
            self.frequencias.append(freq)
            for token in freq:
                aparicoes[token] = aparicoes.get(token, 0) + 1

        total = len(self.docs)
        self.idf = {
            token: math.log(1 + (total - n + 0.5) / (n + 0.5)) for token, n in aparicoes.items()
        }

    def pontuar(self, pergunta: str) -> List[float]:
        termos = tokenizar(pergunta)
        scores = [0.0] * len(self.docs)

        for indice, freq in enumerate(self.frequencias):
            tamanho = self.tamanhos[indice] or 1
            acumulado = 0.0
            for termo in termos:
                ocorrencias = freq.get(termo, 0)
                if not ocorrencias:
                    continue
                norma = K1 * (1 - B + B * tamanho / (self.media_tamanho or 1))
                acumulado += self.idf.get(termo, 0.0) * ocorrencias * (K1 + 1) / (ocorrencias + norma)
            scores[indice] = acumulado

        return scores
