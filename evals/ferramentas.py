"""Avaliação da escolha de ferramenta: a Lu chama a tool certa?

Consome tokens da Groq (uma chamada por caso). Só pede a decisão do
modelo, sem rodar o loop de tool calling — assim nada é executado nem
gravado: não cria pedido, não escreve histórico.
"""

from typing import List, Set, Tuple

from app import config
from app.ai import tools
from app.ai.client import get_client
from evals import casos
from evals.relatorio import Metrica, imprimir_erros, linha_erro, secao

Resultado = Tuple[List[Metrica], List[str]]


def _ferramentas_escolhidas(mensagem: str) -> List[str]:
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
