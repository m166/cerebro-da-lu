"""Orquestração da conversa: histórico + loop de tool calling.

Camada acima dos services, é aqui que o modelo decide quais ferramentas
chamar. Só o texto final (user/assistant) é persistido; as chamadas de
ferramenta ficam fora do histórico salvo.
"""

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


def responder(mensagem_do_usuario: str) -> str:
    repositories.inserir_mensagem("user", mensagem_do_usuario)

    conversa: List[dict] = [{"role": "system", "content": config.persona()}]
    conversa.extend(repositories.listar_mensagens(limite=config.MAX_MENSAGENS_CONTEXTO))

    client = get_client()

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
            repositories.inserir_mensagem("assistant", resposta)
            return resposta

        conversa.append(
            {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [tc.model_dump() for tc in message.tool_calls],
            }
        )
        for tool_call in message.tool_calls:
            conversa.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tools.executar_json(
                        tool_call.function.name, tool_call.function.arguments
                    ),
                }
            )

    raise ChatIncompleto(
        "Não consegui concluir a solicitação (muitas chamadas de ferramentas)."
    )


def historico() -> List[dict]:
    return repositories.listar_mensagens()
