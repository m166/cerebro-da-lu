"""Suíte de avaliação do Cérebro da Lu.

    python -m evals                            tudo
    python -m evals retrieval                  só o RAG (sem custo de API)
    python -m evals ferramentas                só a escolha de tool (usa a Groq)
    python -m evals ferramentas --so desconto  só os casos com esse trecho

Sai com código 1 se alguma métrica ficar abaixo do mínimo, pra poder
travar um pipeline.

`--so` existe pra confirmar um caso específico sem pagar a rodada inteira:
uma execução completa de `ferramentas` são 26 chamadas à Groq, e confirmar
se uma queda foi ruído costuma precisar de uma.
"""

import sys

from evals import ferramentas, retrieval
from evals.relatorio import imprimir_resumo

SUITES = {
    "retrieval": retrieval.executar,
    "ferramentas": ferramentas.executar,
}

# Opções que carregam um valor logo depois. Precisam sair da lista antes de
# procurar nome de suíte, senão `--so desconto` vira "suíte desconhecida".
# Quem lê o valor é `evals.ferramentas`, direto de sys.argv.
OPCOES_COM_VALOR = {"--so"}


def _suites_pedidas(argumentos) -> list:
    nomes = []
    pular = False
    for argumento in argumentos:
        if pular:
            pular = False
            continue
        if argumento in OPCOES_COM_VALOR:
            pular = True
            continue
        nomes.append(argumento)
    return nomes


def main() -> int:
    escolhidas = _suites_pedidas(sys.argv[1:]) or list(SUITES)

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
