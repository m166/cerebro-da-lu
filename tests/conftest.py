import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config, repositories
from app.database import init_db


@pytest.fixture(autouse=True)
def banco_isolado(tmp_path, monkeypatch):
    """Cada teste usa um SQLite próprio, nunca o cerebro.db real do usuário."""
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    init_db()
    yield


@pytest.fixture
def groq_falso(monkeypatch):
    """Substitui o client da Groq — nenhum teste deve chamar a API de verdade.

    Devolve uma função que recebe as respostas que o modelo deve dar, em
    ordem (uma por rodada de tool calling).
    """

    def configurar(*respostas):
        client = MagicMock()
        client.chat.completions.create.side_effect = respostas
        monkeypatch.setattr("app.ai.chat.get_client", lambda: client)
        return client

    return configurar


def resposta_do_modelo(content=None, tool_calls=None):
    """Monta um objeto no formato que o SDK da Groq devolve."""
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls
    completion = MagicMock()
    completion.choices = [MagicMock(message=message)]
    return completion


def tool_call_falso(nome, argumentos, call_id="call_1"):
    tool_call = MagicMock()
    tool_call.id = call_id
    tool_call.function.name = nome
    tool_call.function.arguments = argumentos
    tool_call.model_dump.return_value = {
        "id": call_id,
        "type": "function",
        "function": {"name": nome, "arguments": argumentos},
    }
    return tool_call


def id_por_nome(nome: str) -> int:
    """Resolve o ID de um produto pelo nome — evita testes acoplados a IDs
    fixos, que mudariam ao inserir produtos no catálogo."""
    return next(p["id"] for p in repositories.listar_produtos() if p["nome"] == nome)
