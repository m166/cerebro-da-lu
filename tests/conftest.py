import hashlib
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config, repositories, vectorstore
from app.data import conhecimento
from app.database import init_db


@pytest.fixture(autouse=True)
def banco_isolado(tmp_path, monkeypatch):
    """Cada teste usa um SQLite próprio, nunca o cerebro.db real do usuário."""
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    init_db()
    yield


def _encoder_falso(textos):
    """Encoder determinístico de saco de palavras.

    Não é semântico, casa por sobreposição de termos, mas é o bastante
    pra exercitar índice, ranking, corte por score e filtro de categoria
    sem baixar o modelo de verdade.
    """
    import numpy as np

    dimensoes = 128
    vetores = []
    for texto in textos:
        vetor = np.zeros(dimensoes)
        for palavra in texto.lower().split():
            posicao = int(hashlib.md5(palavra.encode()).hexdigest(), 16) % dimensoes
            vetor[posicao] += 1
        norma = np.linalg.norm(vetor)
        vetores.append(vetor / norma if norma else vetor)
    return np.array(vetores)


@pytest.fixture(autouse=True)
def rag_sem_download(monkeypatch):
    """Autouse de propósito: um teste que esquecesse essa fixture baixaria
    centenas de MB de modelo na primeira execução.

    O corte por score também é zerado aqui. `SCORE_MINIMO_CONHECIMENTO` é
    calibrado pra similaridade de embeddings reais (que ficam bem acima do
    que este encoder léxico produz), então mantê-lo faria os testes medirem
    a calibração do falso, não a lógica. Quem quiser testar o corte
    redefine o valor explicitamente.
    """
    monkeypatch.setattr(config, "SCORE_MINIMO_CONHECIMENTO", 0.0)
    vectorstore.definir_encoder(_encoder_falso)
    yield
    vectorstore.definir_encoder(None)


def titulo_de_doc(trecho_do_titulo: str) -> dict:
    return next(d for d in conhecimento.DOCUMENTOS if trecho_do_titulo in d["titulo"])


@pytest.fixture
def groq_falso(monkeypatch):
    """Substitui o client da Groq, nenhum teste deve chamar a API de verdade.

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
    """Resolve o ID de um produto pelo nome, evita testes acoplados a IDs
    fixos, que mudariam ao inserir produtos no catálogo."""
    return next(p["id"] for p in repositories.listar_produtos() if p["nome"] == nome)
