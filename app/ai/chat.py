"""Orquestração da conversa: histórico + loop de tool calling.

Camada acima dos services, é aqui que o modelo decide quais ferramentas
chamar. Só o texto final (user/assistant) é persistido; as chamadas de
ferramenta ficam fora do histórico salvo.
"""

import base64
import json
import math
import time
from typing import List, Optional

from groq import BadRequestError, RateLimitError

from app import config, models, repositories
from app.ai import tools, visao
from app.ai.client import (
    POR_DIA,
    POR_MINUTO,
    ferramenta_inventada,
    get_client,
    janela_do_limite,
    segundos_de_espera,
)


class ChatIncompleto(Exception):
    """O modelo não fechou a resposta dentro do limite de rodadas de tools."""


class LimiteDeUso(Exception):
    """A conta da Groq bateu o teto de tokens por minuto."""


class ImagemRecusada(Exception):
    """A foto anexada não pôde ser lida."""


def _instrucoes(falas_do_cliente: Optional[List[str]] = None) -> str:
    """Persona somada ao que já se sabe do cliente e ao tom dele.

    O cadastro entra no system prompt, e não no histórico, porque o
    histórico enviado ao modelo é uma janela: o endereço dado há vinte
    mensagens sairia de vista e a Lu perguntaria de novo. Aqui ele está
    sempre presente, por poucos tokens.

    O registro entra pelo mesmo motivo prático: pedir na persona que ela
    espelhe o jeito do cliente não pegou, o modelo respondia neutro de
    qualquer forma. Dito a cada rodada, e já resolvido, pega.
    """
    from app import registro, services

    falas = falas_do_cliente or []
    partes = [config.persona()]

    tom = registro.instrucao(registro.detectar(falas))
    if tom:
        partes.append(f"## Tom desta conversa\n\n{tom}")

    # A apresentação da Lu só serve à mensagem em que ele diz "oi", mas
    # ficava na persona e era paga em todas. Injetada aqui, ela custa zero
    # nas outras, e cumprimento não dispara ferramenta, então esta é a
    # rodada mais barata da conversa pra carregar esse texto.
    if falas and registro.so_cumprimentou(falas[-1]):
        partes.append(f"## Esta mensagem\n\n{registro.INSTRUCAO_ABERTURA}")

    dados = services.dados_do_cliente()
    if dados:
        partes.append(_o_que_ja_sei(dados))

    lembrado = services.memoria_da_conversa()
    if lembrado:
        partes.append(_o_que_ja_rolou(lembrado))
    return "\n\n".join(partes)


def _o_que_ja_rolou(lembrado: dict) -> str:
    """O que o cliente revelou nesta compra, resolvido em vez de recordado.

    Mesmo motivo do cadastro, aplicado ao que não é cadastro: a janela de
    histórico corta, e o "meu limite é 2 mil" de doze mensagens atrás sumia
    junto com o "não gostei desse". A Lu então sugeria caro demais ou
    reoferecia o que já tinha sido recusado.

    Só entra quando há algo anotado, pra não gastar token repetindo que não
    se sabe nada, que é a mesma regra do tom neutro em `registro.py`.
    """
    rotulos = models.ROTULOS_MEMORIA
    linhas = []
    for campo, valor in lembrado.items():
        if campo == "ja_sugeridos":
            continue
        linhas.append(f"- {rotulos.get(campo, campo)}: {valor}")

    if lembrado.get("ja_sugeridos"):
        linhas.append(f"- produtos que você já mostrou: {lembrado['ja_sugeridos']}")

    return (
        "## Esta compra, até aqui\n\n"
        + "\n".join(linhas)
        + "\n\nRespeite isto sem repetir em voz alta: não ofereça acima do que ele "
        "quer gastar, não volte a sugerir o que ele descartou, e não reapresente "
        "o que já mostrou como se fosse novidade."
    )


def _o_que_ja_sei(dados: dict) -> str:
    conhecidos = "\n".join(f"- {campo}: {valor}" for campo, valor in dados.items())
    return (
        "## O que você já sabe deste cliente\n\n"
        f"{conhecidos}\n\n"
        "Use esses dados em vez de perguntar de novo. Se for usar o endereço "
        "num pedido, confirme numa frase ao invés de pedir do zero, e só peça "
        "de novo se ele disser que mudou. O telefone veio do próprio "
        "aparelho dele, então nunca pergunte o número nem peça pra confirmar."
    )


def _produtos_citados(resultado_json: str, encontrados: List[dict]) -> None:
    """Coleta os produtos que a ferramenta devolveu, pra virarem card na tela.

    A resposta do modelo é texto, e texto não mostra foto nem preço em
    destaque. Guardando o que as ferramentas retornaram, a interface
    consegue montar o cartão do produto ao lado da frase dele.
    """
    try:
        dados = json.loads(resultado_json)
    except (TypeError, ValueError):
        return
    if not isinstance(dados, dict):
        return

    candidatos = []
    if isinstance(dados.get("produto"), dict):
        candidatos.append(dados["produto"])
    if isinstance(dados.get("produtos"), list):
        candidatos.extend(p for p in dados["produtos"] if isinstance(p, dict))
    if isinstance(dados.get("produto_id"), int):
        do_catalogo = repositories.obter_produto(dados["produto_id"])
        if do_catalogo:
            candidatos.append(do_catalogo)

    ja_tem = {p["id"] for p in encontrados}
    for produto in candidatos:
        if "id" in produto and "imagem" in produto and produto["id"] not in ja_tem:
            encontrados.append(produto)
            ja_tem.add(produto["id"])


def _nomes_das_tools() -> str:
    return ", ".join(sorted(tools.DISPATCH))


def _completar(client, conversa: List[dict]):
    """Chama o modelo, esperando quando o limite por minuto for questão de
    segundos.

    O teto da conta free é 8000 tokens por minuto e uma conversa com uma
    chamada de ferramenta gasta perto de 7000: passar do limite é questão de
    ritmo, não de excesso, e a Groq costuma pedir poucos segundos de espera.
    Devolver erro nessa situação é jogar fora uma resposta que estava a
    quatro segundos de existir. Espera longa continua virando erro, porque
    aí o cliente prefere saber.
    """
    for tentativa in range(config.TENTATIVAS_APOS_LIMITE + 1):
        try:
            return client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=conversa,
                tools=tools.TOOL_SCHEMAS,
                tool_choice="auto",
            )
        except RateLimitError as exc:
            espera = segundos_de_espera(exc)
            # Teto do dia não adianta esperar: ele volta daqui a horas, não a
            # segundos. Só o teto por minuto merece uma segunda tentativa.
            do_dia = janela_do_limite(exc) == POR_DIA
            ultima = tentativa == config.TENTATIVAS_APOS_LIMITE
            if (
                ultima
                or do_dia
                or espera is None
                or espera > config.ESPERA_MAXIMA_POR_LIMITE
            ):
                raise LimiteDeUso(_aviso_de_limite(exc, espera)) from exc
            # A margem existe porque o relógio da Groq e o nosso não são o
            # mesmo: voltar no segundo exato leva 429 de novo.
            time.sleep(espera + 0.5)


def _quanto_falta(segundos: float) -> str:
    if segundos >= 3600:
        return f"{math.ceil(segundos / 3600)}h"
    if segundos >= 60:
        return f"{math.ceil(segundos / 60)} min"
    return f"{math.ceil(segundos)}s"


def _aviso_de_limite(exc, espera: Optional[float]) -> str:
    """Diz qual teto foi batido, porque a saída é diferente pra cada um.

    A primeira versão dizia "limite por minuto" em qualquer caso, e o teto
    que apareceu na prática foi o do dia: quem lia a mensagem esperava um
    minuto e batia de novo, sem entender.
    """
    janela = janela_do_limite(exc)
    quando = f" Ele libera em cerca de {_quanto_falta(espera)}." if espera else ""

    if janela == POR_DIA:
        return f"A conta da Groq atingiu o limite de tokens do dia.{quando}"
    if janela == POR_MINUTO:
        return f"A conta da Groq atingiu o limite de tokens por minuto.{quando}"
    return f"A conta da Groq atingiu um limite de uso.{quando}"


def _decodificar(imagem: str):
    """Aceita data URL ou base64 puro, devolvendo bytes e o mime."""
    mime = "image/jpeg"
    dados = imagem
    if imagem.startswith("data:"):
        cabecalho, _, dados = imagem.partition(",")
        mime = cabecalho[5:].split(";")[0] or mime
    return base64.b64decode(dados), mime


def responder(mensagem_do_usuario: str, imagem: Optional[str] = None) -> dict:
    """Devolve o texto da Lu e os produtos que ela consultou pra respondê-lo.

    Com foto anexada, ela passa antes pelo modelo de visão e a descrição
    entra na conversa como contexto. O modelo principal não enxerga imagem,
    mas com a descrição em texto ele usa as mesmas ferramentas de catálogo
    pra dizer se a loja tem aquilo.
    """
    contexto_da_foto = None
    if imagem:
        try:
            descricao = visao.descrever(*_decodificar(imagem))
        except (visao.ImagemNaoLida, ValueError, TypeError) as exc:
            raise ImagemRecusada(str(exc)) from exc

        if visao.reconheceu_produto(descricao):
            contexto_da_foto = (
                f"[Contexto: o cliente anexou uma foto. Quem olhou descreveu "
                f"assim: {descricao} Procure no catálogo o que mais se parece "
                f"e responda sobre disponibilidade.]"
            )
        else:
            contexto_da_foto = (
                "[Contexto: o cliente anexou uma foto, mas não deu pra "
                "reconhecer produto nenhum nela. Diga isso e peça pra ele "
                "escrever o que procura.]"
            )

    # No histórico fica o que o cliente escreveu, não o recado que montamos
    # pro modelo: aquele texto entre colchetes apareceria na tela dele.
    repositories.inserir_mensagem("user", mensagem_do_usuario or "Enviei uma foto.")

    janela = repositories.listar_mensagens(limite=config.MAX_MENSAGENS_CONTEXTO)

    # O tom é lido só do que o cliente escreveu. Incluir as falas da Lu
    # criaria eco: ela responderia solto porque respondeu solto antes,
    # mesmo depois de o cliente ter mudado de tom.
    falas_do_cliente = [m["content"] for m in janela if m["role"] == "user"]

    conversa: List[dict] = [
        {"role": "system", "content": _instrucoes(falas_do_cliente)}
    ]
    # Só role e content vão pro modelo. `tipo` é informação nossa, de tela, e
    # a API rejeita campo que ela não conhece dentro da mensagem.
    conversa.extend({"role": m["role"], "content": m["content"]} for m in janela)

    # A descrição da foto vale só pra esta rodada, então entra na cópia que
    # vai pro modelo e não no que fica gravado.
    if contexto_da_foto:
        conversa[-1] = {
            "role": "user",
            "content": f"{contexto_da_foto}\n{conversa[-1]['content']}",
        }

    client = get_client()
    produtos: List[dict] = []

    for _ in range(config.MAX_TOOL_ITERATIONS):
        try:
            completion = _completar(client, conversa)
        except BadRequestError as exc:
            # O modelo às vezes chama uma ferramenta que não existe (já saiu
            # "buscar_conocimiento", em espanhol) e a Groq recusa a geração
            # inteira com 400. Sem tratar, isso virava 502 na cara do
            # cliente por um deslize que a tentativa seguinte não repete.
            #
            # Não dá pra responder com role "tool": a mensagem do assistente
            # foi rejeitada, então não existe tool_call_id pra casar. O que
            # resta é avisar o modelo e deixar ele tentar de novo, gastando
            # uma rodada das que o loop já limita.
            inventada = ferramenta_inventada(exc)
            if inventada is None:
                raise
            conversa.append(
                {
                    "role": "system",
                    "content": (
                        f"A ferramenta '{inventada}' não existe e a chamada foi "
                        f"recusada. Os nomes válidos são: {_nomes_das_tools()}. "
                        "Chame um deles, escrito exatamente assim, ou responda "
                        "sem ferramenta."
                    ),
                }
            )
            continue

        message = completion.choices[0].message

        if not message.tool_calls:
            resposta = message.content
            citados = produtos[: config.MAX_PRODUTOS_NA_RESPOSTA]
            repositories.inserir_mensagem(
                "assistant", resposta, produtos=[p["id"] for p in citados]
            )
            return {"reply": resposta, "produtos": citados}

        conversa.append(
            {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [tc.model_dump() for tc in message.tool_calls],
            }
        )
        for tool_call in message.tool_calls:
            resultado = tools.executar_json(
                tool_call.function.name, tool_call.function.arguments
            )
            _produtos_citados(resultado, produtos)
            conversa.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": resultado,
                }
            )

    raise ChatIncompleto(
        "Não consegui concluir a solicitação (muitas chamadas de ferramentas)."
    )


def historico() -> List[dict]:
    """Histórico pronto pra tela: os ids guardados viram produto completo."""
    mensagens = repositories.listar_mensagens()
    for mensagem in mensagens:
        ids = mensagem.get("produtos") or []
        completos = (repositories.obter_produto(i) for i in ids)
        mensagem["produtos"] = [p for p in completos if p]
    return mensagens
