from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app import config
from app.database import get_connection
from app.main import app
from tests.conftest import id_por_nome, resposta_do_modelo, tool_call_falso

client = TestClient(app)


def _envelhecer(pedido_id, segundos):
    """Empurra a criação do pedido pra trás.

    É assim que o tempo passa nos testes de endpoint: por HTTP não dá pra
    injetar o `agora` que o service aceita, e esperar o relógio deixaria a
    suíte lenta e instável.
    """
    quando = (datetime.utcnow() - timedelta(seconds=segundos)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    conn.execute("UPDATE pedidos SET data_criacao = ? WHERE id = ?", (quando, pedido_id))
    conn.commit()
    conn.close()


def _metade_do_prazo(produto_id):
    """Instante em que o pedido vira "enviado", o meio das quatro fatias."""
    prazo = client.get(f"/api/produtos/{produto_id}").json()["prazo_entrega_dias"]
    return prazo * config.SEGUNDOS_POR_DIA_ENTREGA / 2


# --- Views ---------------------------------------------------------------

def test_index_serve_html():
    assert client.get("/").status_code == 200


# --- Catálogo -------------------------------------------------------------

def test_listar_categorias():
    resposta = client.get("/api/categorias")
    assert resposta.status_code == 200
    assert "notebooks" in resposta.json()


def test_listar_produtos_devolve_catalogo_completo():
    resposta = client.get("/api/produtos")
    assert resposta.status_code == 200
    assert len(resposta.json()) >= 100


def test_listar_produtos_filtrando_categoria():
    resposta = client.get("/api/produtos", params={"categoria": "tvs"})
    assert all(p["categoria"] == "tvs" for p in resposta.json())


def test_listar_produtos_com_limite():
    resposta = client.get("/api/produtos", params={"limite": 3})
    assert len(resposta.json()) == 3


def test_obter_produto():
    produto_id = id_por_nome("Notebook Titan X15")
    resposta = client.get(f"/api/produtos/{produto_id}")
    assert resposta.json()["nome"] == "Notebook Titan X15"


def test_obter_produto_inexistente():
    assert client.get("/api/produtos/9999").status_code == 404


def test_consultar_estoque():
    produto_id = id_por_nome("Notebook Titan X15")
    resposta = client.get(f"/api/produtos/{produto_id}/estoque")
    assert resposta.json()["disponivel"] is True


def test_sugestao_de_produto():
    resposta = client.get("/api/produtos/sugestao", params={"categoria": "air-fryers"})
    assert resposta.status_code == 200
    assert resposta.json()["produto"]["categoria"] == "air-fryers"


def test_sugestao_categoria_inexistente():
    resposta = client.get("/api/produtos/sugestao", params={"categoria": "jetpacks"})
    assert resposta.status_code == 404


def test_comparacao_de_produtos():
    resposta = client.post("/api/produtos/comparacao", json={"categoria": "monitores"})
    assert resposta.status_code == 200
    assert resposta.json()["melhor_avaliacao"] == "Monitor 32'' 4K Profissional"


def test_comparacao_com_um_produto_so():
    resposta = client.post(
        "/api/produtos/comparacao", json={"produto_ids": [id_por_nome("Mouse Sem Fio Básico")]}
    )
    assert resposta.status_code == 422


# --- Conhecimento (RAG) ----------------------------------------------------

def test_buscar_conhecimento():
    resposta = client.get("/api/conhecimento", params={"pergunta": "quantos BTUs preciso"})
    assert resposta.status_code == 200
    assert resposta.json()["encontrou"] is True


def test_buscar_conhecimento_filtrando_categoria():
    resposta = client.get(
        "/api/conhecimento", params={"pergunta": "como escolher", "categoria": "colchoes"}
    )
    assert all(t["categoria"] == "colchoes" for t in resposta.json()["trechos"])


def test_buscar_conhecimento_sem_pergunta():
    assert client.get("/api/conhecimento").status_code == 422


# --- Pedidos -------------------------------------------------------------

def test_fluxo_completo_do_pedido():
    produto_id = id_por_nome("Smartphone Nova 5G")
    criado = client.post(
        "/api/pedidos",
        json={"produto_id": produto_id, "quantidade": 1, "endereco_entrega": "Rua X, 1"},
    )
    assert criado.status_code == 200
    pedido_id = criado.json()["id"]

    assert client.get(f"/api/pedidos/{pedido_id}").status_code == 200

    rastreio = client.get(f"/api/pedidos/{pedido_id}/rastreio")
    assert rastreio.json()["etapa_atual"] == "confirmado"
    assert rastreio.json()["codigo_rastreio"].endswith("BR")

    agendado = client.post(
        f"/api/pedidos/{pedido_id}/agendar-entrega", json={"data_entrega": "2026-08-10"}
    )
    assert agendado.json()["data_entrega_agendada"] == "2026-08-10"
    assert agendado.json()["status"] == "confirmado"

    boleto = client.get(f"/api/pedidos/{pedido_id}/segunda-via", params={"tipo": "boleto"})
    assert boleto.json()["tipo"] == "boleto"

    nf = client.get(f"/api/pedidos/{pedido_id}/segunda-via", params={"tipo": "nf"})
    assert nf.json()["tipo"] == "nota_fiscal"


def test_listar_pedidos_comeca_vazio():
    assert client.get("/api/pedidos").json() == []


def test_listar_pedidos_mais_recente_primeiro():
    primeiro = client.post("/api/pedidos", json={"produto_id": id_por_nome("Smartphone Nova 5G")})
    segundo = client.post("/api/pedidos", json={"produto_id": id_por_nome("Air Fryer 4L Digital")})

    listados = client.get("/api/pedidos").json()
    assert [p["id"] for p in listados] == [segundo.json()["id"], primeiro.json()["id"]]


def test_criar_pedido_estoque_insuficiente():
    produto_id = id_por_nome("Geladeira French Door 540L")
    resposta = client.post("/api/pedidos", json={"produto_id": produto_id, "quantidade": 999})
    assert resposta.status_code == 409


def test_criar_pedido_produto_inexistente():
    assert client.post("/api/pedidos", json={"produto_id": 9999}).status_code == 404


def test_criar_pedido_quantidade_invalida():
    resposta = client.post("/api/pedidos", json={"produto_id": 1, "quantidade": 0})
    assert resposta.status_code == 422


def test_pedido_traz_codigo_de_rastreio():
    criado = client.post("/api/pedidos", json={"produto_id": id_por_nome("Air Fryer 4L Digital")})
    codigo = criado.json()["codigo_rastreio"]
    assert codigo.startswith("LU") and codigo.endswith("BR")
    assert client.get("/api/pedidos").json()[0]["codigo_rastreio"] == codigo
    assert client.get(f"/api/pedidos/{criado.json()['id']}").json()["codigo_rastreio"] == codigo


def test_rastreio_traz_etapa_valida_e_codigo():
    criado = client.post("/api/pedidos", json={"produto_id": id_por_nome("Air Fryer 4L Digital")})
    rastreio = client.get(f"/api/pedidos/{criado.json()['id']}/rastreio").json()

    assert rastreio["etapa_atual"] in rastreio["etapas"]
    assert rastreio["codigo_rastreio"] == criado.json()["codigo_rastreio"]


def test_pedido_inexistente_em_todas_as_rotas():
    assert client.get("/api/pedidos/9999").status_code == 404
    assert client.get("/api/pedidos/9999/rastreio").status_code == 404
    assert client.get("/api/pedidos/9999/segunda-via").status_code == 404
    assert client.post(
        "/api/pedidos/9999/agendar-entrega", json={"data_entrega": "2026-08-10"}
    ).status_code == 404


# --- Notificações ----------------------------------------------------------

def test_notificacoes_sem_pedido_nenhum():
    assert client.get("/api/notificacoes").json() == {"novas": []}


def test_notificacoes_nao_avisa_pedido_recem_criado():
    client.post("/api/pedidos", json={"produto_id": id_por_nome("Air Fryer 4L Digital")})
    assert client.get("/api/notificacoes").json() == {"novas": []}


def test_notificacoes_avisa_entra_no_historico_e_nao_repete(monkeypatch):
    """Escala zero derruba o pedido direto em "entregue", é o jeito de fazer
    o tempo passar sem o teste ficar esperando o relógio."""
    from app import config

    criado = client.post(
        "/api/pedidos", json={"produto_id": id_por_nome("Air Fryer 4L Digital")}
    ).json()
    monkeypatch.setattr(config, "SEGUNDOS_POR_DIA_ENTREGA", 0)

    novas = client.get("/api/notificacoes").json()["novas"]
    assert len(novas) == 1
    assert novas[0]["role"] == "assistant"
    assert f"#{criado['id']}" in novas[0]["content"]

    assert client.get("/api/history").json() == novas
    assert client.get("/api/notificacoes").json() == {"novas": []}
    assert len(client.get("/api/history").json()) == 1


def test_notificacoes_avisa_a_etapa_do_meio_do_caminho():
    produto_id = id_por_nome("Air Fryer 4L Digital")
    criado = client.post("/api/pedidos", json={"produto_id": produto_id}).json()
    _envelhecer(criado["id"], _metade_do_prazo(produto_id))

    novas = client.get("/api/notificacoes").json()["novas"]
    assert len(novas) == 1
    assert criado["codigo_rastreio"] in novas[0]["content"]
    assert client.get(f"/api/pedidos/{criado['id']}/rastreio").json()["etapa_atual"] == "enviado"


def test_status_da_lista_bate_com_a_etapa_do_rastreio():
    """O painel lê o status de /api/pedidos e a etapa do rastreio: divergir
    entre as duas telas é o mesmo pedido em dois lugares ao mesmo tempo."""
    produto_id = id_por_nome("Air Fryer 4L Digital")
    criado = client.post("/api/pedidos", json={"produto_id": produto_id}).json()
    assert criado["status"] == "confirmado"

    _envelhecer(criado["id"], _metade_do_prazo(produto_id))
    listado = client.get("/api/pedidos").json()[0]
    rastreio = client.get(f"/api/pedidos/{criado['id']}/rastreio").json()

    assert listado["status"] == rastreio["etapa_atual"] == "enviado"
    assert client.get(f"/api/pedidos/{criado['id']}").json()["status"] == "enviado"


def test_agendar_entrega_de_pedido_em_transito_nao_volta_o_status():
    produto_id = id_por_nome("Air Fryer 4L Digital")
    criado = client.post("/api/pedidos", json={"produto_id": produto_id}).json()
    _envelhecer(criado["id"], _metade_do_prazo(produto_id))

    agendado = client.post(
        f"/api/pedidos/{criado['id']}/agendar-entrega", json={"data_entrega": "2026-09-15"}
    ).json()
    assert agendado["data_entrega_agendada"] == "2026-09-15"
    assert agendado["status"] == "enviado"


# --- Chat (Groq sempre mockada) -------------------------------------------

def test_historico_comeca_vazio():
    assert client.get("/api/history").json() == []


def test_chat_sem_tool_call(groq_falso):
    groq_falso(resposta_do_modelo(content="Oi! Como posso ajudar?"))

    resposta = client.post("/api/chat", json={"content": "oi"})
    assert resposta.status_code == 200
    assert resposta.json()["reply"] == "Oi! Como posso ajudar?"

    assert client.get("/api/history").json() == [
        {"role": "user", "content": "oi", "tipo": "chat"},
        {"role": "assistant", "content": "Oi! Como posso ajudar?", "tipo": "chat"},
    ]


def test_chat_com_tool_call(groq_falso):
    produto_id = id_por_nome("Notebook Titan X15")
    chamada = tool_call_falso("consultar_estoque", f'{{"produto_id": {produto_id}}}')
    fake = groq_falso(
        resposta_do_modelo(content="", tool_calls=[chamada]),
        resposta_do_modelo(content="Tem 12 unidades em estoque."),
    )

    resposta = client.post("/api/chat", json={"content": "tem estoque do titan?"})
    assert resposta.json()["reply"] == "Tem 12 unidades em estoque."
    assert fake.chat.completions.create.call_count == 2


def test_chat_nao_persiste_mecanica_de_tool_calling(groq_falso):
    """Só o texto final entra no histórico, tool_calls não viram mensagem."""
    chamada = tool_call_falso("listar_categorias", "{}")
    groq_falso(
        resposta_do_modelo(content="", tool_calls=[chamada]),
        resposta_do_modelo(content="Temos várias categorias."),
    )

    client.post("/api/chat", json={"content": "o que voces vendem?"})

    historico = client.get("/api/history").json()
    assert [m["role"] for m in historico] == ["user", "assistant"]


def test_chat_erro_da_groq_virou_502(groq_falso):
    groq_falso(RuntimeError("falha de rede"))
    resposta = client.post("/api/chat", json={"content": "oi"})
    assert resposta.status_code == 502


def test_chat_limite_de_uso_vira_429_legivel(groq_falso):
    """Despejar o JSON cru da Groq na tela não diz nada pro cliente."""
    from unittest.mock import MagicMock

    from groq import RateLimitError

    erro = RateLimitError(
        "Rate limit reached for model. Please try again in 34.89s.",
        response=MagicMock(status_code=429, headers={}),
        body=None,
    )
    groq_falso(erro)

    resposta = client.post("/api/chat", json={"content": "oi"})
    assert resposta.status_code == 429
    detalhe = resposta.json()["detail"]
    assert "limite de uso" in detalhe
    assert "35s" in detalhe


def test_chat_envia_so_a_janela_do_historico(groq_falso, monkeypatch):
    """O histórico completo fica na tela, mas o que vai pro modelo é
    limitado, senão o custo por requisição cresce sem parar."""
    from app import config, repositories

    monkeypatch.setattr(config, "MAX_MENSAGENS_CONTEXTO", 4)
    for i in range(10):
        repositories.inserir_mensagem("user", f"antiga {i}")

    fake = groq_falso(resposta_do_modelo(content="ok"))
    client.post("/api/chat", json={"content": "nova"})

    enviadas = fake.chat.completions.create.call_args.kwargs["messages"]
    assert enviadas[0]["role"] == "system"
    assert len(enviadas) == 5
    assert enviadas[-1]["content"] == "nova"
    assert len(client.get("/api/history").json()) == 12


def test_chat_desiste_apos_limite_de_tool_calls(groq_falso, monkeypatch):
    from app import config

    monkeypatch.setattr(config, "MAX_TOOL_ITERATIONS", 2)
    chamada = tool_call_falso("listar_categorias", "{}")
    groq_falso(
        resposta_do_modelo(content="", tool_calls=[chamada]),
        resposta_do_modelo(content="", tool_calls=[chamada]),
    )

    resposta = client.post("/api/chat", json={"content": "loop infinito"})
    assert resposta.status_code == 502


def test_notificacao_se_identifica_pelo_tipo_e_nao_pelo_texto():
    """A tela precisa distinguir aviso automático de resposta da Lu. Antes
    isso era adivinhado por regex no texto, e reescrever a frase no backend
    quebrava a distinção sem erro nenhum."""
    produto_id = id_por_nome("Smartphone Nova 5G")
    pedido_id = client.post("/api/pedidos", json={"produto_id": produto_id}).json()["id"]
    _envelhecer(pedido_id, segundos=config.SEGUNDOS_POR_DIA_ENTREGA * 30)

    novas = client.get("/api/notificacoes").json()["novas"]
    assert novas
    assert all(m["tipo"] == "notificacao" for m in novas)
    assert all(m["role"] == "assistant" for m in novas)

    historico = client.get("/api/history").json()
    avisos = [m for m in historico if m["tipo"] == "notificacao"]
    assert len(avisos) == len(novas)


def test_resposta_normal_da_lu_e_do_tipo_chat(groq_falso):
    groq_falso(resposta_do_modelo(content="Seu pedido #1 chegou? Deixa eu conferir."))
    client.post("/api/chat", json={"content": "e o pedido 1?"})

    historico = client.get("/api/history").json()
    # Texto que imita o formato do aviso, mas é resposta de verdade: com o
    # regex antigo isso viraria bolha de notificação.
    assert all(m["tipo"] == "chat" for m in historico)
