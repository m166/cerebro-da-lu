from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import config, sessao, telefone
from app.database import get_connection
from app.main import app
from tests.conftest import id_por_nome, resposta_do_modelo, tool_call_falso

# A sessão é o telefone, então o cookie do cliente de teste é um número.
# Vários testes também escrevem direto pelos repositories, e a fixture
# abaixo põe os dois caminhos na mesma conversa.
TELEFONE_DO_TESTE = "11988881234"
SESSAO_DO_TESTE = telefone.normalizar(TELEFONE_DO_TESTE)

client = TestClient(app, cookies={sessao.NOME_DO_COOKIE: TELEFONE_DO_TESTE})


@pytest.fixture(autouse=True)
def escrita_direta_na_mesma_sessao():
    """Faz `repositories.*` chamado fora de requisição cair no mesmo número.

    Só vale pro código do próprio teste: o middleware define a sessão a cada
    requisição, inclusive como `None`, então nada disso vaza pra dentro do
    app e um cliente sem cookie continua sendo tratado como desconhecido.
    """
    token = sessao.definir(SESSAO_DO_TESTE)
    yield
    sessao.restaurar(token)


def _envelhecer(pedido_id, segundos):
    """Empurra a criação do pedido pra trás.

    É assim que o tempo passa nos testes de endpoint: por HTTP não dá pra
    injetar o `agora` que o service aceita, e esperar o relógio deixaria a
    suíte lenta e instável.
    """
    # O datetime vai com fuso, não como texto: numa coluna TIMESTAMPTZ, uma
    # string sem fuso é lida no fuso da sessão do banco, e no Brasil isso
    # deixaria o pedido três horas mais novo do que o teste pediu.
    quando = datetime.now(timezone.utc) - timedelta(seconds=segundos)
    conn = get_connection()
    conn.execute("UPDATE pedidos SET data_criacao = %s WHERE id = %s", (quando, pedido_id))
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
    from app import config, sessao

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
        {"role": "user", "content": "oi", "tipo": "chat", "produtos": []},
        {"role": "assistant", "content": "Oi! Como posso ajudar?", "tipo": "chat", "produtos": []},
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
    from app import config, sessao

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


def test_cadastro_entra_no_prompt_e_sobrevive_a_janela(groq_falso, monkeypatch):
    """O endereço saía de vista quando passava da janela de histórico, e a Lu
    perguntava de novo. Agora ele vai no system prompt, não no histórico."""
    from app import config, repositories

    monkeypatch.setattr(config, "MAX_MENSAGENS_CONTEXTO", 2)
    client.post(
        "/api/pedidos",
        json={"produto_id": id_por_nome("Smartphone Nova 5G"), "endereco_entrega": "Rua A, 1"},
    )
    for i in range(10):
        repositories.inserir_mensagem("user", f"conversa {i}")

    fake = groq_falso(resposta_do_modelo(content="ok"))
    client.post("/api/chat", json={"content": "quero comprar de novo"})

    enviadas = fake.chat.completions.create.call_args.kwargs["messages"]
    system = enviadas[0]["content"]
    assert enviadas[0]["role"] == "system"
    assert "Rua A, 1" in system
    assert not any("Rua A, 1" in m["content"] for m in enviadas[1:])


def test_chat_devolve_produtos_pra_virar_cartao(groq_falso):
    """O texto sozinho não mostra foto nem preço em destaque. A resposta traz
    os produtos que as ferramentas consultaram, e a tela monta o cartão."""
    chamada = tool_call_falso("buscar_produtos", '{"categoria": "air-fryers"}')
    groq_falso(
        resposta_do_modelo(content="", tool_calls=[chamada]),
        resposta_do_modelo(content="Tenho estas opções."),
    )

    resposta = client.post("/api/chat", json={"content": "quero air fryer"}).json()
    assert resposta["produtos"]
    assert all(p["imagem"].endswith(".svg") for p in resposta["produtos"])
    assert len(resposta["produtos"]) <= config.MAX_PRODUTOS_NA_RESPOSTA


def test_cartao_sobrevive_ao_recarregar(groq_falso):
    """Sem guardar os ids, o cartão só existia no envio ao vivo e sumia."""
    chamada = tool_call_falso("buscar_produtos", '{"categoria": "air-fryers"}')
    groq_falso(
        resposta_do_modelo(content="", tool_calls=[chamada]),
        resposta_do_modelo(content="Tenho estas opções."),
    )
    enviados = client.post("/api/chat", json={"content": "quero air fryer"}).json()["produtos"]

    do_historico = client.get("/api/history").json()[-1]
    assert [p["id"] for p in do_historico["produtos"]] == [p["id"] for p in enviados]


def test_mensagem_do_cliente_nao_carrega_produto(groq_falso):
    groq_falso(resposta_do_modelo(content="oi"))
    client.post("/api/chat", json={"content": "oi"})

    historico = client.get("/api/history").json()
    assert historico[0]["role"] == "user"
    assert historico[0]["produtos"] == []


# --- Isolamento entre visitantes -------------------------------------------

TELEFONE_ANA = "11955551111"
TELEFONE_BRUNO = "21944442222"


def _cliente(numero):
    return TestClient(app, cookies={sessao.NOME_DO_COOKIE: numero})


def test_conversa_de_um_visitante_nao_vaza_pro_outro(groq_falso):
    """Antes das sessões o histórico era global: qualquer pessoa que abrisse
    o endereço lia a conversa de quem tinha usado antes."""
    ana, bruno = _cliente(TELEFONE_ANA), _cliente(TELEFONE_BRUNO)

    groq_falso(resposta_do_modelo(content="Oi, Ana!"))
    ana.post("/api/chat", json={"content": "meu nome e Ana"})

    assert [m["content"] for m in ana.get("/api/history").json()] == [
        "meu nome e Ana",
        "Oi, Ana!",
    ]
    assert bruno.get("/api/history").json() == []


def test_pedido_de_um_visitante_nao_aparece_pro_outro():
    ana, bruno = _cliente(TELEFONE_ANA), _cliente(TELEFONE_BRUNO)
    produto_id = id_por_nome("Smartphone Nova 5G")

    criado = ana.post("/api/pedidos", json={"produto_id": produto_id})
    pedido_id = criado.json()["id"]

    assert len(ana.get("/api/pedidos").json()) == 1
    assert bruno.get("/api/pedidos").json() == []
    # Nem pelo id direto: adivinhar o número não pode abrir o pedido alheio.
    assert bruno.get(f"/api/pedidos/{pedido_id}").status_code == 404


def test_cadastro_nao_vaza_entre_visitantes():
    ana, bruno = _cliente(TELEFONE_ANA), _cliente(TELEFONE_BRUNO)
    produto_id = id_por_nome("Smartphone Nova 5G")

    ana.post("/api/pedidos", json={"produto_id": produto_id, "endereco_entrega": "Rua da Ana, 1"})
    bruno.post("/api/pedidos", json={"produto_id": produto_id, "endereco_entrega": "Rua do Bruno, 2"})

    assert ana.get("/api/pedidos").json()[0]["endereco_entrega"] == "Rua da Ana, 1"
    assert bruno.get("/api/pedidos").json()[0]["endereco_entrega"] == "Rua do Bruno, 2"


def test_visitante_sem_numero_nao_conversa():
    """Sem saber de qual número veio, a requisição cairia na sessão `local`,
    que é a dos scripts: todo mundo conversando na mesma caixa de novo."""
    anonimo = TestClient(app)

    assert anonimo.get("/api/history").status_code == 401
    assert anonimo.get("/api/pedidos").status_code == 401
    assert anonimo.post("/api/chat", json={"content": "oi"}).status_code == 401
    assert anonimo.get("/api/sessao").status_code == 401


def test_catalogo_continua_aberto_a_quem_nao_se_identificou():
    """Produto e base de conhecimento são da loja, não de um cliente: exigir
    telefone pra ver a vitrine seria cadastro na frente de quem só quer olhar."""
    anonimo = TestClient(app)

    assert anonimo.get("/api/produtos").status_code == 200
    assert anonimo.get("/api/categorias").status_code == 200
    assert anonimo.get("/api/conhecimento", params={"pergunta": "quantos BTUs"}).status_code == 200


# --- Identificação pelo telefone -------------------------------------------

def test_identificar_normaliza_o_numero_e_deixa_conversar():
    visitante = TestClient(app)

    resposta = visitante.post("/api/sessao", json={"telefone": "(11) 98888-1234"})

    assert resposta.status_code == 200
    assert resposta.json()["telefone"] == "5511988881234"
    assert resposta.json()["telefone_formatado"] == "+55 11 98888-1234"
    # O cookie ficou, então a conversa seguinte já sabe quem é.
    assert visitante.get("/api/history").status_code == 200


def test_identificar_recusa_numero_sem_cara_de_telefone():
    resposta = TestClient(app).post("/api/sessao", json={"telefone": "123"})
    assert resposta.status_code == 422
    assert "inválido" in resposta.json()["detail"].lower()


def test_mesma_pessoa_volta_pelo_numero_ainda_que_de_outro_navegador(groq_falso):
    """É o que o telefone compra: a conversa não mora no cookie, mora no
    número, então trocar de aparelho não zera o histórico."""
    celular = TestClient(app)
    celular.post("/api/sessao", json={"telefone": "11977776666"})
    groq_falso(resposta_do_modelo(content="Oi!"))
    celular.post("/api/chat", json={"content": "bom dia"})

    outro_navegador = TestClient(app)
    outro_navegador.post("/api/sessao", json={"telefone": "+55 (11) 97777-6666"})

    assert [m["content"] for m in outro_navegador.get("/api/history").json()] == [
        "bom dia",
        "Oi!",
    ]


def test_trocar_de_numero_nao_leva_a_conversa_junto(groq_falso):
    navegador = TestClient(app)
    navegador.post("/api/sessao", json={"telefone": TELEFONE_ANA})
    groq_falso(resposta_do_modelo(content="Oi, Ana!"))
    navegador.post("/api/chat", json={"content": "aqui é a Ana"})

    navegador.post("/api/sessao", json={"telefone": TELEFONE_BRUNO})

    assert navegador.get("/api/history").json() == []


def test_cookie_antigo_sem_telefone_entrega_a_conversa_pro_numero(groq_falso):
    """Quem já usava o app tem cookie com id aleatório. Sem esta migração ele
    digitaria o número e encontraria a própria conversa vazia."""
    legado = "362fb988cf124512adeb4bb4fc6e0a2e"
    antigo = TestClient(app, cookies={sessao.NOME_DO_COOKIE: legado})

    token = sessao.definir(legado)
    try:
        from app import repositories

        repositories.inserir_mensagem("user", "conversa de antes do telefone")
    finally:
        sessao.restaurar(token)

    antigo.post("/api/sessao", json={"telefone": "11966665555"})

    assert [m["content"] for m in antigo.get("/api/history").json()] == [
        "conversa de antes do telefone"
    ]


def test_esquecer_o_numero_nao_apaga_a_conversa(groq_falso):
    navegador = TestClient(app)
    navegador.post("/api/sessao", json={"telefone": TELEFONE_ANA})
    groq_falso(resposta_do_modelo(content="Oi!"))
    navegador.post("/api/chat", json={"content": "oi"})

    assert navegador.delete("/api/sessao").status_code == 204
    assert navegador.get("/api/history").status_code == 401

    navegador.post("/api/sessao", json={"telefone": TELEFONE_ANA})
    assert len(navegador.get("/api/history").json()) == 2


def test_telefone_entra_no_prompt_pra_lu_nao_perguntar(groq_falso):
    cliente = TestClient(app, cookies={sessao.NOME_DO_COOKIE: TELEFONE_ANA})
    groq = groq_falso(resposta_do_modelo(content="Claro!"))

    cliente.post("/api/chat", json={"content": "qual meu numero?"})

    system = groq.chat.completions.create.call_args.kwargs["messages"][0]["content"]
    assert "+55 11 95555-1111" in system


def test_notificacao_so_avisa_o_dono_do_pedido():
    ana, bruno = _cliente(TELEFONE_ANA), _cliente(TELEFONE_BRUNO)
    produto_id = id_por_nome("Smartphone Nova 5G")
    pedido_id = ana.post("/api/pedidos", json={"produto_id": produto_id}).json()["id"]
    _envelhecer(pedido_id, segundos=config.SEGUNDOS_POR_DIA_ENTREGA * 30)

    assert bruno.get("/api/notificacoes").json()["novas"] == []
    assert ana.get("/api/notificacoes").json()["novas"]


# --- Imagem do produto e foto do cliente ------------------------------------

def test_imagem_do_produto_sai_como_svg():
    resposta = client.get("/api/produtos/1/imagem.svg")
    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("image/svg+xml")
    assert resposta.text.startswith("<svg")


def test_imagem_de_produto_inexistente():
    assert client.get("/api/produtos/99999/imagem.svg").status_code == 404


def test_chat_com_foto_usa_a_descricao_pra_buscar(groq_falso):
    """A foto passa pelo modelo de visão e vira contexto em texto. O modelo
    de conversa não enxerga imagem, mas com a descrição usa as ferramentas
    de catálogo normalmente."""
    from unittest.mock import patch

    fake = groq_falso(resposta_do_modelo(content="Temos sim, geladeira branca."))
    with patch("app.ai.visao.descrever", return_value="Uma geladeira branca de duas portas."):
        resposta = client.post(
            "/api/chat",
            json={"content": "voces tem esse?", "imagem": "data:image/png;base64,YWJj"},
        )

    assert resposta.status_code == 200

    # No histórico fica o que o cliente escreveu; a descrição da foto é
    # recado pro modelo e não pode aparecer na tela dele.
    gravada = client.get("/api/history").json()[0]["content"]
    assert gravada == "voces tem esse?"

    enviadas = fake.chat.completions.create.call_args.kwargs["messages"]
    assert "geladeira branca" in enviadas[-1]["content"]


def test_foto_ilegivel_avisa_o_cliente(groq_falso):
    from unittest.mock import patch

    from app.ai import visao

    with patch("app.ai.visao.descrever", side_effect=visao.ImagemNaoLida("muito grande")):
        resposta = client.post(
            "/api/chat", json={"content": "e esse?", "imagem": "data:image/png;base64,YWJj"}
        )

    assert resposta.status_code == 422
    assert "muito grande" in resposta.json()["detail"]


def test_foto_sem_produto_reconhecivel_orienta_a_lu(groq_falso):
    from unittest.mock import patch

    fake = groq_falso(resposta_do_modelo(content="Não consegui ver o produto."))
    with patch("app.ai.visao.descrever", return_value="nenhum produto reconhecível"):
        client.post("/api/chat", json={"content": "", "imagem": "data:image/png;base64,YWJj"})

    # Sem texto digitado o histórico ganha uma frase legível, não vazio.
    assert client.get("/api/history").json()[0]["content"] == "Enviei uma foto."
    enviadas = fake.chat.completions.create.call_args.kwargs["messages"]
    assert "reconhecer produto nenhum" in enviadas[-1]["content"]


def test_chat_sem_foto_nao_chama_visao(groq_falso):
    from unittest.mock import patch

    groq_falso(resposta_do_modelo(content="oi"))
    with patch("app.ai.visao.descrever") as visao_falsa:
        client.post("/api/chat", json={"content": "oi"})
    visao_falsa.assert_not_called()


# --- Ferramenta que o modelo inventa ---------------------------------------

def _erro_de_ferramenta_inventada(nome="buscar_conocimiento"):
    """O 400 que a Groq devolve quando o modelo chama tool inexistente.

    Aconteceu de verdade: o modelo escreveu `buscar_conocimiento`, em
    espanhol, e o cliente recebeu 502 no lugar da resposta.
    """
    import httpx
    from groq import BadRequestError

    corpo = {
        "error": {
            "message": (
                "Tool call validation failed: tool call validation failed: "
                f"attempted to call tool '{nome}' which was not in request.tools"
            ),
            "type": "invalid_request_error",
            "code": "tool_use_failed",
        }
    }
    requisicao = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    return BadRequestError(
        "400", response=httpx.Response(400, json=corpo, request=requisicao), body=corpo
    )


def test_ferramenta_inventada_pelo_modelo_nao_vira_erro_pro_cliente(groq_falso):
    groq = groq_falso(
        _erro_de_ferramenta_inventada(),
        resposta_do_modelo(content="Pra academia, o ProSound resolve."),
    )

    resposta = client.post("/api/chat", json={"content": "fone bom pra academia"})

    assert resposta.status_code == 200
    assert resposta.json()["reply"] == "Pra academia, o ProSound resolve."

    # A segunda tentativa leva o aviso com os nomes válidos, senão o modelo
    # repetiria o mesmo palpite errado.
    segunda = groq.chat.completions.create.call_args_list[1].kwargs["messages"]
    aviso = segunda[-1]
    assert aviso["role"] == "system"
    assert "buscar_conocimiento" in aviso["content"]
    assert "buscar_conhecimento" in aviso["content"]


def test_o_erro_recuperado_nao_entra_no_historico_do_cliente(groq_falso):
    groq_falso(
        _erro_de_ferramenta_inventada(),
        resposta_do_modelo(content="Achei aqui."),
    )
    client.post("/api/chat", json={"content": "fone bom pra academia"})

    conversa = [m["content"] for m in client.get("/api/history").json()]
    assert conversa == ["fone bom pra academia", "Achei aqui."]


def test_400_que_nao_e_ferramenta_inventada_continua_estourando(groq_falso):
    """Requisição malformada é bug nosso: engolir viraria falha silenciosa."""
    import httpx
    from groq import BadRequestError

    corpo = {"error": {"message": "schema inválido", "code": "outra_coisa"}}
    requisicao = httpx.Request("POST", "https://api.groq.com/x")
    groq_falso(
        BadRequestError(
            "400", response=httpx.Response(400, json=corpo, request=requisicao), body=corpo
        )
    )

    assert client.post("/api/chat", json={"content": "oi"}).status_code == 502


# --- Tom espelhado no system prompt ----------------------------------------

def _system_prompt(groq, chamada=0):
    return groq.chat.completions.create.call_args_list[chamada].kwargs["messages"][0][
        "content"
    ]


def test_tom_solto_do_cliente_entra_no_prompt(groq_falso):
    """Pedir espelhamento só na persona não pegava: o modelo respondia
    neutro. A instrução do tom vai resolvida, a cada rodada."""
    groq = groq_falso(resposta_do_modelo(content="Achei aqui"))

    client.post("/api/chat", json={"content": "eae blz mano, tem fone barato?"})

    assert "está escrevendo solto" in _system_prompt(groq)


def test_tom_formal_do_cliente_entra_no_prompt(groq_falso):
    groq = groq_falso(resposta_do_modelo(content="Claro"))

    client.post(
        "/api/chat",
        json={"content": "Boa tarde. Gostaria de saber o prazo, por gentileza."},
    )

    assert "de maneira formal" in _system_prompt(groq)


def test_cliente_neutro_nao_ganha_instrucao_de_tom(groq_falso):
    groq = groq_falso(resposta_do_modelo(content="Oi"))

    client.post("/api/chat", json={"content": "quero um notebook"})

    prompt = _system_prompt(groq)
    assert "Tom desta conversa" not in prompt


def test_a_persona_entra_uma_vez_so_no_prompt(groq_falso):
    """Com cadastro, a montagem antiga colava a persona dentro dela mesma."""
    from app import repositories

    repositories.salvar_perfil("nome", "Matheus")
    groq = groq_falso(resposta_do_modelo(content="Oi"))

    client.post("/api/chat", json={"content": "oi"})

    prompt = _system_prompt(groq)
    assert prompt.count("# Persona: Lu") == 1
    assert "Matheus" in prompt


def test_o_tom_da_lu_nao_realimenta_a_deteccao(groq_falso):
    """Só o que o cliente escreve conta. Se as falas dela entrassem, ela
    ficaria solta pra sempre depois da primeira gíria dele."""
    from app import repositories

    repositories.inserir_mensagem("user", "eae blz mano")
    repositories.inserir_mensagem("assistant", "Eae! Tmj, vou ver aqui")
    groq = groq_falso(resposta_do_modelo(content="Certo"))

    client.post(
        "/api/chat",
        json={"content": "Boa tarde, gostaria de solicitar a nota fiscal."},
    )

    assert "de maneira formal" in _system_prompt(groq)


def test_cumprimento_ganha_a_instrucao_de_abertura(groq_falso):
    groq = groq_falso(resposta_do_modelo(content="Oi! Aqui é a Lu"))

    client.post("/api/chat", json={"content": "oi"})

    assert "só cumprimentou" in _system_prompt(groq)


def test_mensagem_comum_nao_paga_a_instrucao_de_abertura(groq_falso):
    """Ela vive fora da persona justamente pra não ser paga em toda rodada."""
    groq = groq_falso(resposta_do_modelo(content="Achei"))

    client.post("/api/chat", json={"content": "quero uma air fryer"})

    assert "só cumprimentou" not in _system_prompt(groq)


# --- Limite de tokens por minuto -------------------------------------------

def _limite_de_uso(mensagem):
    from unittest.mock import MagicMock

    from groq import RateLimitError

    return RateLimitError(
        mensagem, response=MagicMock(status_code=429, headers={}), body=None
    )


def test_espera_curta_e_aguardada_em_vez_de_virar_erro(groq_falso, monkeypatch):
    """8000 tokens/min com conversa de ~7000: estourar é questão de ritmo.
    Devolver erro joga fora uma resposta que estava a 2 segundos de existir."""
    dormiu = []
    monkeypatch.setattr("app.ai.chat.time.sleep", dormiu.append)

    groq_falso(
        _limite_de_uso("Rate limit reached. Please try again in 1.8s."),
        resposta_do_modelo(content="Achei aqui"),
    )

    resposta = client.post("/api/chat", json={"content": "tem air fryer?"})

    assert resposta.status_code == 200
    assert resposta.json()["reply"] == "Achei aqui"
    # Espera com margem: voltar no segundo exato leva 429 de novo.
    assert dormiu == [2.3]


def test_espera_longa_continua_virando_aviso_pro_cliente(groq_falso, monkeypatch):
    """Meio minuto de "digitando..." é pior que dizer o que aconteceu."""
    monkeypatch.setattr("app.ai.chat.time.sleep", lambda _: None)
    groq_falso(_limite_de_uso("Rate limit reached. Please try again in 34.89s."))

    resposta = client.post("/api/chat", json={"content": "oi"})

    assert resposta.status_code == 429
    assert "35s" in resposta.json()["detail"]


def test_desiste_depois_das_tentativas_configuradas(groq_falso, monkeypatch):
    """Sem teto de tentativas, um minuto ruim seguraria a requisição presa."""
    monkeypatch.setattr("app.ai.chat.time.sleep", lambda _: None)
    monkeypatch.setattr(config, "TENTATIVAS_APOS_LIMITE", 2)
    groq = groq_falso(*[_limite_de_uso("try again in 1s.")] * 3)

    assert client.post("/api/chat", json={"content": "oi"}).status_code == 429
    assert groq.chat.completions.create.call_count == 3


def test_espera_em_milissegundos_e_entendida(groq_falso, monkeypatch):
    dormiu = []
    monkeypatch.setattr("app.ai.chat.time.sleep", dormiu.append)
    groq_falso(
        _limite_de_uso("Please try again in 800ms."),
        resposta_do_modelo(content="Pronto"),
    )

    assert client.post("/api/chat", json={"content": "oi"}).status_code == 200
    assert dormiu == [1.3]
