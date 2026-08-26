"""Client da Groq, criado sob demanda.

A criação é lazy pra que importar o app (nos testes, por exemplo) não exija
uma GROQ_API_KEY configurada.

Aqui mora também a leitura dos erros da Groq: é a fronteira com o provedor,
então quem traduz o formato dele é este módulo, e não cada chamador.
"""

import re
from typing import Optional

from groq import Groq

from app import config

_client: Optional[Groq] = None

# A Groq recusa a geração com 400 quando o modelo chama uma ferramenta que
# não existe. Já saiu "buscar_conocimiento", em espanhol, no lugar de
# "buscar_conhecimento".
CODIGO_FERRAMENTA_INVALIDA = "tool_use_failed"

_NOME_INVENTADO = re.compile(r"attempted to call tool '([^']+)'")

# A duração vem em formatos bem diferentes conforme o limite batido:
# "340ms", "4.5s" e também "22m2.784s" quando o teto é o do dia. A primeira
# versão daqui só entendia segundos, então o limite diário devolvia `None` e
# a mensagem saía sem prazo nenhum.
_ESPERA = re.compile(r"try again in ([0-9hms.]+)")
_COMPONENTE = re.compile(r"(\d+(?:\.\d+)?)(ms|h|m|s)")

# "ms" antes de "m" e "s" importa: sem isso "800ms" leria 800 minutos.
_EM_SEGUNDOS = {"ms": 0.001, "s": 1.0, "m": 60.0, "h": 3600.0}

# A Groq tem teto por minuto e teto por dia, e a diferença muda o que dizer
# pro cliente: um passa em segundos, o outro só no dia seguinte.
POR_MINUTO = "minuto"
POR_DIA = "dia"

_JANELA = re.compile(r"tokens per (day|minute)", re.I)
_JANELAS = {"day": POR_DIA, "minute": POR_MINUTO}


def _mensagem(exc) -> str:
    return erro_da_groq(exc).get("message") or str(exc)


def segundos_de_espera(exc) -> Optional[float]:
    """Quanto a Groq pediu pra esperar, em segundos, ou `None` se não disse."""
    achado = _ESPERA.search(_mensagem(exc))
    if not achado:
        return None
    partes = _COMPONENTE.findall(achado.group(1))
    if not partes:
        return None
    return sum(float(valor) * _EM_SEGUNDOS[unidade] for valor, unidade in partes)


def janela_do_limite(exc) -> Optional[str]:
    """Se o teto batido foi o do minuto ou o do dia, quando dá pra saber."""
    achado = _JANELA.search(_mensagem(exc))
    return _JANELAS[achado.group(1).lower()] if achado else None


def erro_da_groq(exc) -> dict:
    """O corpo estruturado do erro, que é onde o motivo vem confiável.

    `str(exc)` costuma trazer o mesmo texto, mas depende de como o SDK
    montou a mensagem; ler o corpo não depende de formatação.
    """
    corpo = getattr(exc, "body", None)
    erro = corpo.get("error") if isinstance(corpo, dict) else None
    return erro if isinstance(erro, dict) else {}


def ferramenta_inventada(exc) -> Optional[str]:
    """Nome da ferramenta que o modelo tentou chamar, se foi esse o erro.

    Devolve `None` pra qualquer outro 400: requisição malformada é bug
    nosso e precisa estourar, não ser tratada como capricho do modelo.
    """
    erro = erro_da_groq(exc)
    if erro.get("code") != CODIGO_FERRAMENTA_INVALIDA:
        return None
    achado = _NOME_INVENTADO.search(erro.get("message") or "")
    return achado.group(1) if achado else "desconhecida"


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
