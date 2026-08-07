"""Client da Groq, criado sob demanda.

A criação é lazy pra que importar o app (nos testes, por exemplo) não exija
uma GROQ_API_KEY configurada.
"""

from typing import Optional

from groq import Groq

from app import config

_client: Optional[Groq] = None


def get_client() -> Groq:
    global _client
    if _client is None:
        if not config.GROQ_API_KEY:
            raise RuntimeError(
                "GROQ_API_KEY não encontrada. Copie .env.example para .env e "
                "preencha sua chave (gere uma grátis em https://console.groq.com/keys)."
            )
        _client = Groq(api_key=config.GROQ_API_KEY)
    return _client
