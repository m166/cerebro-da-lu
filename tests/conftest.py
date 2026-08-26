import hashlib
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config, database, repositories, vectorstore
from app.data import conhecimento
from app.database import get_connection, init_db

# Banco separado, e apontado já no import: com o SQLite bastava trocar um
# caminho por teste, mas agora um teste que escapasse da fixture escreveria
# no banco de verdade do app. Definir aqui fecha essa porta antes de
# qualquer coleta.
# Sem padrão de propósito. A fixture de isolamento dá `TRUNCATE` nas tabelas
# do visitante a cada caso, então um padrão apontando pra `localhost:5432`
# apagaria dados de qualquer Postgres que estivesse escutando ali, inclusive
# um container de outro projeto. Exigir a variável troca um erro destrutivo
# e silencioso por um recado na primeira linha.
URL_DE_TESTE = os.getenv("DATABASE_URL_TEST")
if not URL_DE_TESTE:
    raise RuntimeError(
        "DATABASE_URL_TEST não configurada, e a suíte não adivinha: ela trunca "
        "tabelas a cada teste. Aponte pra um banco descartável, com a extensão "
        "pgvector. Atenção: a porta 5432 desta máquina é de outro projeto."
    )

# A troca é feita uma vez só. O pytest importa este arquivo duas vezes, como
# `conftest` e como `tests.conftest` (os testes fazem `from tests.conftest
# import ...`), e sem a marca a segunda passagem compararia a URL de teste
# com ela mesma e acusaria um conflito que não existe.
if not getattr(config, "_url_de_teste_aplicada", False):
    if URL_DE_TESTE == config.DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL_TEST é igual ao banco do app. Os testes apagam tabelas "
            "a cada caso, então isso destruiria a conversa e os pedidos reais."
        )
    config.DATABASE_URL = URL_DE_TESTE
    config._url_de_teste_aplicada = True


@pytest.fixture(scope="session", autouse=True)
def schema_de_teste():
    """Cria o schema uma vez por execução, não uma vez por teste.

    No SQLite cada teste ganhava um arquivo novo, que era grátis. Aqui criar
    tabela é ida e volta ao servidor, então o schema é montado uma vez e o
    isolamento fica por conta do TRUNCATE de cada caso.
    """
    init_db()


@pytest.fixture(autouse=True)
def banco_isolado():
    """Zera as tabelas do visitante entre os testes.

    A lista vem de `database.TABELAS_DO_VISITANTE`, não escrita à mão aqui:
    quando a tabela `memoria` entrou, a lista fixa deixou ela de fora e a
    anotação de um teste apareceu no seguinte. Deriva daquela tupla e o
    esquecimento deixa de ser possível.

    `RESTART IDENTITY` importa: sem ele o primeiro pedido de cada teste
    nasceria com id crescente, e há caso que espera o pedido #1.
    `conhecimento_vetores` fica de fora de propósito, é índice da loja e
    reencodar o corpus a cada teste seria desperdício.
    """
    conn = get_connection()
    conn.execute(
        f"TRUNCATE {', '.join(database.TABELAS_DO_VISITANTE)} RESTART IDENTITY"
    )
    conn.commit()
    conn.close()
    yield


@pytest.fixture(autouse=True)
def escala_de_entrega_previsivel(monkeypatch):
    """Fixa o ritmo da esteira, senão o `.env` da máquina decide o resultado.

    `SEGUNDOS_POR_DIA_ENTREGA` vem de variável de ambiente e o `.env.example`
    convida a mexer nela (20 pra demo, 86400 pra tempo real). Com 1, um pedido
    recém-criado já aparece "em separação" e testes de fluxo quebram sem que
    nada no código tenha mudado. Quem testa a escala redefine o valor.
    """
    monkeypatch.setattr(config, "SEGUNDOS_POR_DIA_ENTREGA", 20)


def _encoder_falso(textos):
    """Encoder determinístico de saco de palavras.

    Não é semântico, casa por sobreposição de termos, mas é o bastante
    pra exercitar índice, ranking, corte por score e filtro de categoria
    sem baixar o modelo de verdade.
    """
    import numpy as np

    # Tem que casar com `config.DIMENSOES_EMBEDDING`: a coluna do pgvector é
    # `vector(384)` e recusa vetor de outra largura. Antes disso era 128, que
    # funcionava porque a matriz vivia em memória e numpy aceita qualquer
    # forma.
    dimensoes = config.DIMENSOES_EMBEDDING
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
