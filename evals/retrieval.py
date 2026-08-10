"""Avaliação do RAG: a busca traz o documento certo?

Usa o modelo de embedding real (baixa na primeira execução) e não gasta
token de API, só CPU.
"""

from typing import List, Tuple

from app import config, vectorstore
from evals import casos
from evals.relatorio import Metrica, imprimir_erros, linha_erro, secao

K = 3
Resultado = Tuple[List[Metrica], List[str]]


def _posicao_do_esperado(resultados: List[dict], doc_id: int) -> int:
    """Posição do documento esperado no ranking, ou -1 se ficou fora do topo."""
    for posicao, documento in enumerate(resultados, start=1):
        if documento["id"] == doc_id:
            return posicao
    return -1


def avaliar_acerto() -> Resultado:
    acertos_top1 = 0
    acertos_topk = 0
    reciprocos = 0.0
    erros = []
    quase = []

    for pergunta, doc_id in casos.RETRIEVAL:
        resultados = vectorstore.buscar(pergunta, k=K)
        posicao = _posicao_do_esperado(resultados, doc_id)

        if posicao == 1:
            acertos_top1 += 1
            acertos_topk += 1
            reciprocos += 1
        elif posicao > 1:
            # Está no top-K mas perdeu o 1º lugar. Não conta como erro, e
            # antes disso ficava invisível, que é justamente o caso que
            # rende diagnóstico: dá pra ver quem passou na frente.
            acertos_topk += 1
            reciprocos += 1 / posicao
            venceu = resultados[0]
            quase.append(
                f"  - {pergunta[:52]!r}\n"
                f"      esperado em 1º: doc {doc_id}, veio em {posicao}º\n"
                f"      passou na frente: {venceu['titulo']} ({venceu['score']:.3f})"
            )
        else:
            trouxe = resultados[0]["titulo"] if resultados else "(nada)"
            erros.append(linha_erro(pergunta, esperado=f"doc {doc_id}", obtido=trouxe))

    if quase:
        print(f"\n  {len(quase)} caso(s) no top-{K} mas fora do 1º lugar:")
        for linha in quase:
            print(linha)

    # Mínimos logo abaixo do medido depois do enriquecimento dos documentos
    # (94% / 100% / 0.97). Frouxo demais não trava regressão: com 60% aqui,
    # perder um quarto do acerto passaria batido.
    total = len(casos.RETRIEVAL)
    return [
        Metrica("acerto@1", acertos_top1, total, minimo=0.88),
        Metrica(f"acerto@{K}", acertos_topk, total, minimo=0.96),
        Metrica("MRR", reciprocos, total, minimo=0.92, e_media=True),
    ], erros


def _passa_no_corte(pergunta: str) -> List[dict]:
    """Espelha o service: mesmo k e mesmos cortes.

    Usar k=1 aqui mediria outra coisa, o service entrega até
    LIMITE_CONHECIMENTO trechos, e basta um passar pra Lu ter contexto.
    """
    return [
        d
        for d in vectorstore.buscar(pergunta, k=config.LIMITE_CONHECIMENTO)
        if d["score"] >= config.SCORE_MINIMO_CONHECIMENTO
        or d["score_lexical"] >= config.SCORE_LEXICAL_MINIMO
    ]


def avaliar_cobertura() -> Resultado:
    """Pergunta do domínio precisa sobreviver ao corte de relevância.

    Mede o outro lado da rejeição, que ficava sem medida: um corte muito
    apertado faz a Lu responder "não tenho essa informação" sobre assunto
    que a base cobre, e nada apontava isso.
    """
    cobertas = 0
    erros = []

    for pergunta, doc_id in casos.RETRIEVAL:
        if _passa_no_corte(pergunta):
            cobertas += 1
        else:
            melhor = vectorstore.buscar(pergunta, k=1)
            detalhe = (
                f"cos {melhor[0]['score']:.3f} / lex {melhor[0]['score_lexical']:.2f}"
                if melhor
                else "(nada)"
            )
            erros.append(
                linha_erro(
                    pergunta,
                    esperado=f"doc {doc_id} acima do corte",
                    obtido=f"barrado pelo corte ({detalhe})",
                )
            )

    total = len(casos.RETRIEVAL)
    return [Metrica("cobertura do domínio", cobertas, total, minimo=0.98)], erros


def avaliar_rejeicao() -> Resultado:
    """Pergunta fora do domínio deveria voltar vazia."""
    rejeitadas = 0
    erros = []

    for pergunta in casos.RETRIEVAL_FORA_DE_ESCOPO:
        resultados = _passa_no_corte(pergunta)
        if resultados:
            erros.append(
                linha_erro(
                    pergunta,
                    esperado="nada",
                    obtido=f"{resultados[0]['titulo']} ({resultados[0]['score']:.3f})",
                )
            )
        else:
            rejeitadas += 1

    total = len(casos.RETRIEVAL_FORA_DE_ESCOPO)
    # Leia junto com "cobertura do domínio": as duas se puxam em direções
    # opostas, e a calibração escolheu não barrar pergunta legítima. O
    # mínimo fica abaixo do medido porque a amostra fora do domínio é
    # pequena (8) e uma variação aqui diz menos que na cobertura.
    return [Metrica("rejeicao fora de escopo", rejeitadas, total, minimo=0.75)], erros


def executar() -> List[Metrica]:
    secao("RETRIEVAL", f"modelo: {config.MODELO_EMBEDDING}")
    print(f"  {len(casos.RETRIEVAL)} perguntas do domínio, "
          f"{len(casos.RETRIEVAL_FORA_DE_ESCOPO)} fora dele")

    metricas_acerto, erros_acerto = avaliar_acerto()
    metricas_cobertura, erros_cobertura = avaliar_cobertura()
    metricas_rejeicao, erros_rejeicao = avaliar_rejeicao()

    imprimir_erros(erros_acerto + erros_cobertura + erros_rejeicao)
    return metricas_acerto + metricas_cobertura + metricas_rejeicao
