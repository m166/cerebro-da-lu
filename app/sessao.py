"""Sessão do visitante, para que uma conversa não veja a de outra.

O id vive num contextvar preenchido pelo middleware, e não é passado de
camada em camada. A razão é prática: as ferramentas são chamadas pelo
modelo, que não conhece sessão nenhuma, então acrescentar o parâmetro na
assinatura de cada uma espalharia um detalhe de transporte por todo o
domínio. Isolamento por inquilino é um assunto transversal, e é para isso
que existe estado por requisição.

Não há login: cada navegador ganha um id anônimo no primeiro acesso. Isso
resolve o problema real (o histórico era global e visível a qualquer um)
sem colocar cadastro na frente de quem só quer experimentar. Login, se um
dia fizer sentido, se apoia nesta mesma coluna.
"""

import uuid
from contextvars import ContextVar
from typing import Optional

NOME_DO_COOKIE = "sessao_lu"

# Um ano: o visitante volta e encontra a conversa onde parou.
VALIDADE_DO_COOKIE = 60 * 60 * 24 * 365

_sessao_atual: ContextVar[Optional[str]] = ContextVar("sessao_atual", default=None)


def nova() -> str:
    return uuid.uuid4().hex


def definir(sessao_id: str):
    return _sessao_atual.set(sessao_id)


def restaurar(token) -> None:
    _sessao_atual.reset(token)


def atual() -> str:
    """Sessão da requisição em curso.

    Fora de uma requisição (testes de unidade, scripts) devolve uma sessão
    fixa, para que o código funcione sem middleware e sem misturar dados de
    quem usa o app.
    """
    return _sessao_atual.get() or "local"
