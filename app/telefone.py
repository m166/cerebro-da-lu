"""Número de telefone: normalização e formatação.

No WhatsApp a identidade é o número, não uma conta que alguém cria. Como o
"Cérebro da Lu" vai rodar lá dentro, o número é a chave da sessão (veja
`app/sessao.py`), e por isso ele precisa ter uma forma canônica: o mesmo
celular pode chegar como "(11) 98888-1234", "11988881234" ou
"+55 11 98888-1234", e as três têm que cair na mesma conversa.

A forma canônica é só dígitos, com DDI: `5511988881234`. É o mesmo formato
que a Cloud API da Meta usa no `wa_id`, então quando o canal real entrar
não há conversão a fazer.
"""

import re

DDI_BRASIL = "55"

# DDD brasileiro vai de 11 a 99: nenhum começa com 0 nem termina em 0.
_DDD = re.compile(r"^[1-9][1-9]$")

_SO_DIGITOS = re.compile(r"\D")


class TelefoneInvalido(ValueError):
    """O texto informado não tem cara de telefone."""


def normalizar(bruto: str) -> str:
    """Devolve o número em dígitos com DDI, ou levanta `TelefoneInvalido`.

    Aceita número com 10 ou 11 dígitos (com DDD, sem DDI) e completa o 55.
    Celular tem 11 e é o caso do WhatsApp; os 10 dígitos entram porque
    recusar um fixo só criaria atrito num simulador, sem proteger nada.
    """
    digitos = _SO_DIGITOS.sub("", bruto or "")

    if digitos.startswith(DDI_BRASIL) and len(digitos) in (12, 13):
        nacional = digitos[len(DDI_BRASIL) :]
    elif len(digitos) in (10, 11):
        nacional = digitos
    else:
        raise TelefoneInvalido(
            "Número inválido. Use DDD e o número, como 11 98888-1234."
        )

    if not _DDD.match(nacional[:2]):
        raise TelefoneInvalido(f"DDD inválido: {nacional[:2]}.")

    return DDI_BRASIL + nacional


def valido(bruto: str) -> bool:
    try:
        normalizar(bruto)
    except TelefoneInvalido:
        return False
    return True


def formatar(numero: str) -> str:
    """Versão legível do número canônico: `+55 11 98888-1234`.

    Recebe o que já está normalizado, então não valida de novo: quem chama é
    a tela e o prompt da Lu, e um valor estranho vindo do banco deve aparecer
    como está em vez de derrubar a requisição.
    """
    digitos = _SO_DIGITOS.sub("", numero or "")
    if not digitos.startswith(DDI_BRASIL) or len(digitos) not in (12, 13):
        return numero

    nacional = digitos[len(DDI_BRASIL) :]
    ddd, assinante = nacional[:2], nacional[2:]
    meio = 5 if len(assinante) == 9 else 4
    return f"+{DDI_BRASIL} {ddd} {assinante[:meio]}-{assinante[meio:]}"
