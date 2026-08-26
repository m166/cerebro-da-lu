"""O simulador não vai pro ar junto com a app.

A tela em `static/` deixa qualquer pessoa digitar qualquer número e cair na
conversa daquele cliente, porque não existe verificação nenhuma: é aceitável
numa ferramenta local e seria vazamento numa URL pública. No WhatsApp o
problema não existe, quem informa o número é a Meta no envelope da mensagem.

Estes testes seguram as duas metades da decisão. Recarregar o `app.main` é
necessário porque o registro dos routers acontece no import, não por
requisição.
"""

import importlib

import pytest
from fastapi.testclient import TestClient

from app import config


def _app_com_simulador(ativo: bool):
    from app import main

    original = config.SIMULADOR_ATIVO
    config.SIMULADOR_ATIVO = ativo
    try:
        return importlib.reload(main).app
    finally:
        config.SIMULADOR_ATIVO = original


@pytest.fixture
def sem_simulador():
    app = _app_com_simulador(False)
    yield TestClient(app)
    _app_com_simulador(True)


@pytest.fixture
def com_simulador():
    app = _app_com_simulador(True)
    return TestClient(app)


def test_tela_do_simulador_some(sem_simulador):
    assert sem_simulador.get("/").status_code == 404


def test_arquivo_estatico_some(sem_simulador):
    """Servir o JS de uma tela que não existe entregaria o mapa da API."""
    assert sem_simulador.get("/static/script.js").status_code == 404


def test_ninguem_reivindica_um_numero_por_formulario(sem_simulador):
    """Este é o vazamento de verdade, e some junto.

    Com o endpoint de pé, tirar só o HTML seria teatro: bastaria um curl com
    o número de outra pessoa pra assumir a conversa dela.
    """
    resposta = sem_simulador.post("/api/sessao", json={"telefone": "11988881234"})
    assert resposta.status_code == 404


def test_dado_do_cliente_continua_protegido(sem_simulador):
    """Sem transporte, ninguém se identifica, então tudo do cliente é 401.

    É a resposta certa e não uma falta: quem vai dizer o número é o webhook,
    que ainda não existe.
    """
    assert sem_simulador.get("/api/history").status_code == 401
    assert sem_simulador.get("/api/pedidos").status_code == 401


def test_catalogo_continua_aberto(sem_simulador):
    """A vitrine é da loja, não de um cliente, e sobrevive sem o simulador.

    É o que a integração vai consumir sem precisar de sessão nenhuma.
    """
    assert sem_simulador.get("/api/categorias").status_code == 200
    assert sem_simulador.get("/api/produtos").status_code == 200


def test_com_simulador_tudo_continua_como_era(com_simulador):
    """A trava não pode atrapalhar o uso local, que é pra isso que ele existe."""
    assert com_simulador.get("/").status_code == 200
    resposta = com_simulador.post("/api/sessao", json={"telefone": "11988881234"})
    assert resposta.status_code == 200
