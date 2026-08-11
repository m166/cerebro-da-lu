"""Avaliação da escolha de ferramenta: a Lu chama a tool certa?

Consome tokens da Groq (uma chamada por caso). Só pede a decisão do
modelo, sem rodar o loop de tool calling, assim nada é executado nem
gravado: não cria pedido, não escreve histórico.
"""

import re
import time
from typing import List, Set, Tuple

from groq import RateLimitError

from app import config
from app.ai import tools
from app.ai.client import get_client
from evals import casos
from evals.relatorio import Metrica, imprimir_erros, linha_erro, secao

Resultado = Tuple[List[Metrica], List[str]]


def _ferramentas_escolhidas(mensagem: str, tentativas: int = 4) -> List[str]:
    """Pergunta ao modelo qual ferramenta ele usaria, respeitando o limite.

    A conta free trabalha com 8000 tokens por minuto e cada caso custa uns
    2600 (persona mais schemas). Disparar os 21 casos em sequência estoura o
    teto e a avaliação morria no meio com 429. Aqui ela espera o tempo que a
    própria Groq informa e tenta de novo, em vez de derrubar a execução.
    """
    for tentativa in range(tentativas):
        try:
            completion = get_client().chat.completions.create(
                model=config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": config.persona()},
                    {"role": "user", "content": mensagem},
                ],
                tools=tools.TOOL_SCHEMAS,
                tool_choice="auto",
            )
            chamadas = completion.choices[0].message.tool_calls or []
            return [c.function.name for c in chamadas]
        except RateLimitError as exc:
            if tentativa == tentativas - 1:
                raise
            espera = _segundos_de_espera(str(exc))
            print(f"    limite de tokens atingido, aguardando {espera:.0f}s")
            time.sleep(espera)
    return []


def _segundos_de_espera(mensagem: str) -> float:
    """Usa o tempo que a Groq informa, com um mínimo pra não voltar cedo."""
    achado = re.search(r"try again in ([\d.]+)(m?s)", mensagem)
    if not achado:
        return 20.0
    valor = float(achado.group(1))
    segundos = valor / 1000 if achado.group(2) == "ms" else valor
    return max(segundos + 1.0, 5.0)


def avaliar_escolha() -> Resultado:
    acertos = 0
    sem_ferramenta = 0
    erros = []

    for mensagem, aceitaveis in casos.FERRAMENTAS:
        escolhidas = _ferramentas_escolhidas(mensagem)
        if not escolhidas:
            sem_ferramenta += 1
            erros.append(linha_erro(mensagem, esperado=" ou ".join(sorted(aceitaveis)),
                                    obtido="nenhuma ferramenta (respondeu de cabeça)"))
        elif escolhidas[0] in aceitaveis:
            acertos += 1
        else:
            erros.append(linha_erro(mensagem, esperado=" ou ".join(sorted(aceitaveis)),
                                    obtido=", ".join(escolhidas)))

    total = len(casos.FERRAMENTAS)
    return [
        Metrica("ferramenta correta", acertos, total, minimo=0.80),
        Metrica("respondeu sem consultar", total - sem_ferramenta, total, minimo=0.90),
    ], erros


def avaliar_conversa() -> Resultado:
    """Saudação e agradecimento não deveriam disparar ferramenta."""
    corretos = 0
    erros = []

    for mensagem in casos.FERRAMENTAS_SEM_CHAMADA:
        escolhidas = _ferramentas_escolhidas(mensagem)
        if escolhidas:
            erros.append(linha_erro(mensagem, esperado="nenhuma", obtido=", ".join(escolhidas)))
        else:
            corretos += 1

    total = len(casos.FERRAMENTAS_SEM_CHAMADA)
    return [Metrica("conversa sem ferramenta", corretos, total, minimo=0.66)], erros


def executar() -> List[Metrica]:
    total_chamadas = len(casos.FERRAMENTAS) + len(casos.FERRAMENTAS_SEM_CHAMADA)
    secao("ESCOLHA DE FERRAMENTA", f"modelo: {config.GROQ_MODEL}")
    print(f"  {total_chamadas} chamadas à Groq (nada é executado nem gravado)")

    metricas_escolha, erros_escolha = avaliar_escolha()
    metricas_conversa, erros_conversa = avaliar_conversa()

    imprimir_erros(erros_escolha + erros_conversa)
    return metricas_escolha + metricas_conversa
