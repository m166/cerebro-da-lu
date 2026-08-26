"""Sessão do visitante, para que uma conversa não veja a de outra.

**A sessão é o telefone.** No WhatsApp não existe cadastro nem login: quem
chega já chega identificado pelo número, e é ele que liga a mensagem de hoje
à conversa de três meses atrás. Como o Cérebro da Lu vai rodar lá dentro, a
chave aqui é a mesma, no formato canônico de `app/telefone.py`
(`5511988881234`). Assim o simulador do navegador exercita exatamente o
mesmo caminho que o canal real vai usar.

O id vive num contextvar preenchido pelo middleware, e não é passado de
camada em camada. A razão é prática: as ferramentas são chamadas pelo
modelo, que não conhece sessão nenhuma, então acrescentar o parâmetro na
assinatura de cada uma espalharia um detalhe de transporte por todo o
domínio. Isolamento por inquilino é um assunto transversal, e é para isso
que existe estado por requisição.

No navegador o número fica num cookie, que faz o papel do aparelho: é o que
diz de qual celular a mensagem está saindo. Trocar de número no simulador é
trocar esse cookie.
"""

from contextvars import ContextVar
from typing import Optional

from app import telefone

NOME_DO_COOKIE = "sessao_lu"

# Um ano: o visitante volta e encontra a conversa onde parou.
VALIDADE_DO_COOKIE = 60 * 60 * 24 * 365

# Sessão usada fora de uma requisição HTTP (teste de unidade, script, eval).
# Não é um telefone de propósito: nada que rode fora do canal deve cair na
# conversa de um cliente de verdade.
SESSAO_LOCAL = "local"

_sessao_atual: ContextVar[Optional[str]] = ContextVar("sessao_atual", default=None)


def definir(sessao_id: Optional[str]):
    """Fixa a sessão da requisição. `None` marca "não sei quem é"."""
    return _sessao_atual.set(sessao_id)


def restaurar(token) -> None:
    _sessao_atual.reset(token)


def atual() -> str:
    """Sessão da requisição em curso.

    Fora de uma requisição (testes de unidade, scripts) devolve uma sessão
    fixa, para que o código funcione sem middleware e sem misturar dados de
    quem usa o app.
    """
    return _sessao_atual.get() or SESSAO_LOCAL


def identificado() -> bool:
    """Se a requisição em curso sabe com qual número está falando."""
    return _sessao_atual.get() is not None


def do_cookie(valor: Optional[str]) -> Optional[str]:
    """Traduz o cookie do navegador em sessão, ou `None` se ele não serve.

    Cookie gravado por uma versão anterior guarda um id aleatório, não um
    telefone. Ele não vira sessão: quem tem um desses é tratado como quem
    ainda não se identificou, e o número informado na tela adota a conversa
    antiga (`services.identificar_cliente`).
    """
    if not valor:
        return None
    try:
        return telefone.normalizar(valor)
    except telefone.TelefoneInvalido:
        return None
