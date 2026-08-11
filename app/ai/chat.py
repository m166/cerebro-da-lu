"""Orquestração da conversa: histórico + loop de tool calling.

Camada acima dos services, é aqui que o modelo decide quais ferramentas
chamar. Só o texto final (user/assistant) é persistido; as chamadas de
ferramenta ficam fora do histórico salvo.
"""

import json
import math
import re
from typing import List, Optional

from groq import RateLimitError

from app import config, repositories
from app.ai import tools
from app.ai.client import get_client


class ChatIncompleto(Exception):
    """O modelo não fechou a resposta dentro do limite de rodadas de tools."""


class LimiteDeUso(Exception):
    """A conta da Groq bateu o teto de tokens por minuto."""


def _segundos_para_tentar(mensagem: str) -> Optional[int]:
    """Extrai o tempo de espera que a Groq informa na mensagem de erro."""
    achado = re.search(r"try again in ([\d.]+)s", mensagem)
    return math.ceil(float(achado.group(1))) if achado else None


def _instrucoes() -> str:
    """Persona somada ao que já se sabe do cliente.

    O cadastro entra no system prompt, e não no histórico, porque o
    histórico enviado ao modelo é uma janela: o endereço dado há vinte
    mensagens sairia de vista e a Lu perguntaria de novo. Aqui ele está
    sempre presente, por poucos tokens.
    """
    from app import services

    dados = services.dados_do_cliente()
    if not dados:
        return config.persona()

    conhecidos = "\n".join(f"- {campo}: {valor}" for campo, valor in dados.items())
    return (
        f"{config.persona()}\n\n"
        "## O que você já sabe deste cliente\n\n"
        f"{conhecidos}\n\n"
        "Use esses dados em vez de perguntar de novo. Se for usar o endereço "
        "num pedido, confirme numa frase ao invés de pedir do zero, e só peça "
        "de novo se ele disser que mudou."
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


def responder(mensagem_do_usuario: str) -> dict:
    """Devolve o texto da Lu e os produtos que ela consultou pra respondê-lo."""
    repositories.inserir_mensagem("user", mensagem_do_usuario)

    conversa: List[dict] = [{"role": "system", "content": _instrucoes()}]
    # Só role e content vão pro modelo. `tipo` é informação nossa, de tela, e
    # a API rejeita campo que ela não conhece dentro da mensagem.
    conversa.extend(
        {"role": m["role"], "content": m["content"]}
        for m in repositories.listar_mensagens(limite=config.MAX_MENSAGENS_CONTEXTO)
    )

    client = get_client()
    produtos: List[dict] = []

    for _ in range(config.MAX_TOOL_ITERATIONS):
        try:
            completion = client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=conversa,
                tools=tools.TOOL_SCHEMAS,
                tool_choice="auto",
            )
        except RateLimitError as exc:
            espera = _segundos_para_tentar(str(exc))
            quando = f" Tente de novo em {espera}s." if espera else ""
            raise LimiteDeUso(
                f"A conta da Groq atingiu o limite de uso por minuto.{quando}"
            ) from exc

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
