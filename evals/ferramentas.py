"""Avaliação da escolha de ferramenta: a Lu chama a tool certa?

Consome tokens da Groq (uma chamada por caso). Só pede a decisão do
modelo, sem rodar o loop de tool calling, assim nada é executado nem
gravado: não cria pedido, não escreve histórico. Isso importa mais agora
que existem casos pra `salvar_dado_do_cliente` e `anotar_da_conversa`, que
**escreveriam no banco** se fossem executadas de verdade.

Uma execução completa custa cerca de 26 chamadas, que é da ordem de 60% a
70% da cota diária. Duas coisas aqui existem pra evitar queimar isso à toa:

- `--so <trecho>` roda só os casos cuja mensagem contém o trecho. Confirmar
  se uma queda foi ruído passa de 26 chamadas pra uma ou duas.
- `EVALS_SEM_TOOLS=nome,nome` remove ferramentas da lista enviada ao modelo
  **só aqui**, sem tocar em `app/ai/tools.py`. É o que permite testar se
  ferramenta a mais está atrapalhando a escolha das outras, com um punhado
  de chamadas em vez de uma rodada inteira.
"""

import os
import sys
import time
from typing import List, Optional, Set, Tuple

from groq import BadRequestError, RateLimitError

from app import config
from app.ai import tools
from app.ai.client import ferramenta_inventada, get_client, segundos_de_espera
from evals import casos
from evals.relatorio import Metrica, imprimir_erros, linha_erro, secao

Resultado = Tuple[List[Metrica], List[str]]


def _filtro() -> Optional[str]:
    """Trecho passado em `--so`, se houver."""
    if "--so" in sys.argv:
        posicao = sys.argv.index("--so")
        if posicao + 1 < len(sys.argv):
            return sys.argv[posicao + 1].lower()
    return None


def _selecionar(lista):
    trecho = _filtro()
    if not trecho:
        return list(lista)
    return [item for item in lista if trecho in _mensagem_de(item).lower()]


def _mensagem_de(item):
    return item if isinstance(item, str) else item[0]


def _schemas_do_experimento():
    """Os schemas enviados ao modelo, menos o que `EVALS_SEM_TOOLS` remover.

    Serve pra isolar a hipótese de que ferramenta a mais no manual atrapalha
    a escolha das outras. Sem a variável, é `tools.TOOL_SCHEMAS` inteiro.
    """
    removidas = {
        nome.strip()
        for nome in os.getenv("EVALS_SEM_TOOLS", "").split(",")
        if nome.strip()
    }
    if not removidas:
        return tools.TOOL_SCHEMAS
    return [s for s in tools.TOOL_SCHEMAS if s["function"]["name"] not in removidas]


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
                tools=_schemas_do_experimento(),
                tool_choice="auto",
            )
            chamadas = completion.choices[0].message.tool_calls or []
            return [c.function.name for c in chamadas]
        except BadRequestError as exc:
            # Ferramenta inventada é erro de escolha como outro qualquer:
            # entra na conta como caso errado. Deixar a exceção subir
            # derrubava a execução no meio e jogava fora os casos já
            # medidos. Aqui, ao contrário do chat, não se tenta de novo: a
            # avaliação mede a decisão do modelo, e insistir até acertar
            # mediria a insistência.
            inventada = ferramenta_inventada(exc)
            if inventada is None:
                raise
            return [f"{inventada} (não existe)"]
        except RateLimitError as exc:
            if tentativa == tentativas - 1:
                raise
            espera = _quanto_esperar(exc)
            print(f"    limite de tokens atingido, aguardando {espera:.0f}s")
            time.sleep(espera)
    return []


def _quanto_esperar(exc) -> float:
    """O tempo que a Groq informa, com um mínimo pra não voltar cedo demais.

    A avaliação dispara 21 casos em sequência e pode ficar minutos no
    limite, então aqui o piso é maior que no chat, onde tem gente esperando
    do outro lado.
    """
    espera = segundos_de_espera(exc)
    return 20.0 if espera is None else max(espera + 1.0, 5.0)


def avaliar_escolha(lista=None, rotulo="ferramenta correta", minimo=0.80) -> Resultado:
    """Mede se a primeira ferramenta escolhida está entre as aceitáveis.

    Recebe a lista pra que a base histórica (`FERRAMENTAS`) e a cobertura
    nova (`FERRAMENTAS_COBERTURA`) sejam medidas **separadamente**. Juntar as
    duas numa métrica só apagaria a comparação com as execuções anteriores,
    que é justamente o que se quer restaurar.
    """
    escolhidos = _selecionar(casos.FERRAMENTAS if lista is None else lista)
    if not escolhidos:
        return [], []

    acertos = 0
    sem_ferramenta = 0
    erros = []

    for mensagem, aceitaveis in escolhidos:
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

    total = len(escolhidos)
    metricas = [Metrica(rotulo, acertos, total, minimo=minimo)]
    if lista is None:
        metricas.append(
            Metrica("respondeu sem consultar", total - sem_ferramenta, total, minimo=0.90)
        )
    return metricas, erros


def avaliar_proibidas() -> Resultado:
    """Ferramenta que não pode ser chamada nesta situação.

    Confere **todas** as chamadas, não só a primeira: oferecer cupom em
    segundo lugar continua sendo oferecer cupom, e o dano é o mesmo.
    """
    escolhidos = _selecionar(casos.FERRAMENTAS_PROIBIDAS)
    if not escolhidos:
        return [], []

    corretos = 0
    erros = []

    for mensagem, proibidas in escolhidos:
        escolhidas = _ferramentas_escolhidas(mensagem)
        indevidas = proibidas & set(escolhidas)
        if indevidas:
            erros.append(linha_erro(mensagem, esperado=f"nunca {' ou '.join(sorted(proibidas))}",
                                    obtido=", ".join(escolhidas)))
        else:
            corretos += 1

    total = len(escolhidos)
    return [Metrica("nao chamou a proibida", corretos, total, minimo=1.0)], erros


def avaliar_conversa() -> Resultado:
    """Saudação e agradecimento não deveriam disparar ferramenta."""
    escolhidos = _selecionar(casos.FERRAMENTAS_SEM_CHAMADA)
    if not escolhidos:
        return [], []

    corretos = 0
    erros = []

    for mensagem in escolhidos:
        escolhidas = _ferramentas_escolhidas(mensagem)
        if escolhidas:
            erros.append(linha_erro(mensagem, esperado="nenhuma", obtido=", ".join(escolhidas)))
        else:
            corretos += 1

    total = len(escolhidos)
    return [Metrica("conversa sem ferramenta", corretos, total, minimo=0.66)], erros


def _relatar_cobertura() -> None:
    """Quais ferramentas o modelo enxerga e a avaliação não mede.

    Impresso **antes** de gastar chamada, e custa zero. É o que faz o
    descompasso aparecer sozinho: três ferramentas já entraram no manual sem
    nenhum caso, e nada apontou isso até alguém ir contar na mão.
    """
    declaradas = {schema["function"]["name"] for schema in _schemas_do_experimento()}
    sem_caso = casos.ferramentas_sem_caso(declaradas)
    print(f"  {len(declaradas)} ferramentas no manual do modelo")
    if sem_caso:
        print(f"  SEM CASO DE AVALIAÇÃO: {', '.join(sorted(sem_caso))}")
    else:
        print("  todas cobertas por pelo menos um caso")


def executar() -> List[Metrica]:
    secao("ESCOLHA DE FERRAMENTA", f"modelo: {config.GROQ_MODEL}")
    _relatar_cobertura()

    if os.getenv("EVALS_SEM_TOOLS"):
        print(f"  EXPERIMENTO: rodando sem {os.getenv('EVALS_SEM_TOOLS')}")
    if _filtro():
        print(f"  filtrando casos que contenham: {_filtro()!r}")

    total_chamadas = sum(
        len(_selecionar(lista))
        for lista in (
            casos.FERRAMENTAS,
            casos.FERRAMENTAS_COBERTURA,
            casos.FERRAMENTAS_PROIBIDAS,
            casos.FERRAMENTAS_SEM_CHAMADA,
        )
    )
    print(f"  {total_chamadas} chamadas à Groq (nada é executado nem gravado)")

    metricas, erros = [], []
    for parciais, falhas in (
        avaliar_escolha(),
        # Mínimo 0.0 de propósito: esta métrica nunca foi medida, então
        # qualquer piso seria chute, e chute aqui ou trava a execução sem
        # motivo ou passa fingindo que mediu. Ajuste pra logo abaixo do
        # medido depois da primeira execução.
        avaliar_escolha(casos.FERRAMENTAS_COBERTURA, "cobertura: ferramenta nova", 0.0),
        avaliar_proibidas(),
        avaliar_conversa(),
    ):
        metricas += parciais
        erros += falhas

    imprimir_erros(erros)
    return metricas
