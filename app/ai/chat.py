"""Orquestração da conversa: histórico + loop de tool calling.

Camada acima dos services — é aqui que o modelo decide quais ferramentas
chamar. Só o texto final (user/assistant) é persistido; as chamadas de
ferramenta ficam fora do histórico salvo.
"""

from typing import List

from app import config, repositories
from app.ai import tools
from app.ai.client import get_client


class ChatIncompleto(Exception):
    """O modelo não fechou a resposta dentro do limite de rodadas de tools."""


def responder(mensagem_do_usuario: str) -> str:
    repositories.inserir_mensagem("user", mensagem_do_usuario)

    conversa: List[dict] = [{"role": "system", "content": config.persona()}]
    conversa.extend(repositories.listar_mensagens())

    client = get_client()

    for _ in range(config.MAX_TOOL_ITERATIONS):
        completion = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=conversa,
            tools=tools.TOOL_SCHEMAS,
            tool_choice="auto",
        )
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
