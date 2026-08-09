"""Avaliação do RAG: a busca traz o documento certo?

Usa o modelo de embedding real (baixa na primeira execução) e não gasta
token de API — só CPU.
"""

from typing import List, Tuple

from app import config, vectorstore
from evals import casos
from evals.relatorio import Metrica, imprimir_erros, linha_erro, secao

K = 3
Resultado = Tuple[List[Metrica], List[str]]


def _posicao_do_esperado(pergunta: str, doc_id: int) -> int:
    """Posição do documento esperado no ranking, ou -1 se ficou fora do topo."""
    resultados = vectorstore.buscar(pergunta, k=K)
    for posicao, documento in enumerate(resultados, start=1):
        if documento["id"] == doc_id:
            return posicao
    return -1


def avaliar_acerto() -> Resultado:
    acertos_top1 = 0
    acertos_topk = 0
    reciprocos = 0.0
    erros = []

    for pergunta, doc_id in casos.RETRIEVAL:
        posicao = _posicao_do_esperado(pergunta, doc_id)
        if posicao == 1:
            acertos_top1 += 1
        if posicao > 0:
            acertos_topk += 1
            reciprocos += 1 / posicao
        else:
            obtidos = vectorstore.buscar(pergunta, k=1)
            trouxe = obtidos[0]["titulo"] if obtidos else "(nada)"
            erros.append(linha_erro(pergunta, esperado=f"doc {doc_id}", obtido=trouxe))

    total = len(casos.RETRIEVAL)
    return [
        Metrica("acerto@1", acertos_top1, total, minimo=0.60),
        Metrica(f"acerto@{K}", acertos_topk, total, minimo=0.80),
        Metrica("MRR", reciprocos, total, minimo=0.65, e_media=True),
    ], erros


def avaliar_rejeicao() -> Resultado:
    """Pergunta fora do domínio deveria voltar vazia."""
    rejeitadas = 0
    erros = []

    for pergunta in casos.RETRIEVAL_FORA_DE_ESCOPO:
        resultados = [
            d
            for d in vectorstore.buscar(pergunta, k=1)
            if d["score"] >= config.SCORE_MINIMO_CONHECIMENTO
        ]
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
    # Mínimo baixo de propósito: está documentado que o piso de score não é
    # filtro confiável de assunto. A métrica existe pra acompanhar, não pra
    # fingir que o problema está resolvido.
    return [Metrica("rejeicao fora de escopo", rejeitadas, total, minimo=0.30)], erros


def executar() -> List[Metrica]:
    secao("RETRIEVAL", f"modelo: {config.MODELO_EMBEDDING}")
    print(f"  {len(casos.RETRIEVAL)} perguntas do domínio, "
          f"{len(casos.RETRIEVAL_FORA_DE_ESCOPO)} fora dele")

    metricas_acerto, erros_acerto = avaliar_acerto()
    metricas_rejeicao, erros_rejeicao = avaliar_rejeicao()

    imprimir_erros(erros_acerto + erros_rejeicao)
    return metricas_acerto + metricas_rejeicao
