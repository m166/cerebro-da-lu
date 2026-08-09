"""Suíte de avaliação do Cérebro da Lu.

    python -m evals              tudo
    python -m evals retrieval    só o RAG (sem custo de API)
    python -m evals ferramentas  só a escolha de tool (usa a Groq)

Sai com código 1 se alguma métrica ficar abaixo do mínimo, pra poder
travar um pipeline.
"""

import sys

from evals import ferramentas, retrieval
from evals.relatorio import imprimir_resumo

SUITES = {
    "retrieval": retrieval.executar,
    "ferramentas": ferramentas.executar,
}


def main() -> int:
    escolhidas = sys.argv[1:] or list(SUITES)

    desconhecidas = [nome for nome in escolhidas if nome not in SUITES]
    if desconhecidas:
        print(f"suíte desconhecida: {', '.join(desconhecidas)}")
        print(f"disponíveis: {', '.join(SUITES)}")
        return 2

    metricas = []
    for nome in escolhidas:
        metricas.extend(SUITES[nome]())

    return 0 if imprimir_resumo(metricas) else 1


if __name__ == "__main__":
    sys.exit(main())
