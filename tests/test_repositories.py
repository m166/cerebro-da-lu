from app import repositories
from app.data import catalogo
from tests.conftest import id_por_nome


# --- Mensagens ---------------------------------------------------------

def test_inserir_e_listar_mensagens():
    repositories.inserir_mensagem("user", "oi")
    repositories.inserir_mensagem("assistant", "ola")
    assert repositories.listar_mensagens() == [
        {"role": "user", "content": "oi"},
        {"role": "assistant", "content": "ola"},
    ]


def test_historico_comeca_vazio():
    assert repositories.listar_mensagens() == []


def test_listar_mensagens_com_limite_traz_as_ultimas_em_ordem():
    """O modelo recebe só uma janela do histórico; reenviar a conversa
    inteira a cada rodada de tool calling estourava o limite de tokens."""
    for i in range(6):
        repositories.inserir_mensagem("user", f"mensagem {i}")

    recentes = repositories.listar_mensagens(limite=3)
    assert [m["content"] for m in recentes] == ["mensagem 3", "mensagem 4", "mensagem 5"]


def test_listar_mensagens_sem_limite_traz_tudo():
    for i in range(4):
        repositories.inserir_mensagem("user", f"mensagem {i}")
    assert len(repositories.listar_mensagens()) == 4


def test_banco_apagado_com_app_no_ar_se_recupera():
    """Sem isso, apagar o arquivo deixa toda consulta falhando com
    "no such table" até alguém reiniciar o processo."""
    from app import config

    repositories.inserir_mensagem("user", "antes")
    config.DB_PATH.unlink()

    assert repositories.listar_mensagens() == []
    repositories.inserir_mensagem("user", "depois")
    assert repositories.listar_mensagens() == [{"role": "user", "content": "depois"}]


# --- Pedidos -------------------------------------------------------------

def test_inserir_e_obter_pedido():
    pedido = repositories.inserir_pedido(1, "Notebook Titan X15", 1, 4899.90, "Rua Teste, 123")
    assert pedido["status"] == "confirmado"

    obtido = repositories.obter_pedido(pedido["id"])
    assert obtido["produto_nome"] == "Notebook Titan X15"
    assert obtido["endereco_entrega"] == "Rua Teste, 123"


def test_obter_pedido_inexistente_retorna_none():
    assert repositories.obter_pedido(9999) is None


def test_atualizar_entrega_agendada():
    pedido = repositories.inserir_pedido(1, "Notebook Titan X15", 1, 4899.90)
    atualizado = repositories.atualizar_entrega_agendada(pedido["id"], "2026-08-05")
    assert atualizado["data_entrega_agendada"] == "2026-08-05"
    assert atualizado["status"] == "entrega agendada"


# --- Catálogo -------------------------------------------------------------

def test_catalogo_tem_mais_de_cem_produtos():
    assert len(catalogo.PRODUTOS) >= 100


def test_toda_categoria_tem_no_minimo_quatro_produtos():
    """O mínimo de 4 por categoria é o que viabiliza comparação de verdade."""
    for categoria in catalogo.CATEGORIAS:
        produtos = repositories.listar_produtos(categoria=categoria)
        assert len(produtos) >= 4, f"categoria {categoria} tem só {len(produtos)}"


def test_ids_sao_unicos_e_sequenciais():
    ids = [p["id"] for p in catalogo.PRODUTOS]
    assert ids == list(range(1, len(ids) + 1))


def test_listar_produtos_por_categoria():
    produtos = repositories.listar_produtos(categoria="notebooks")
    assert all(p["categoria"] == "notebooks" for p in produtos)


def test_busca_prefere_quem_casa_todos_os_termos():
    resultado = repositories.listar_produtos(query="notebook gamer")
    assert [p["nome"] for p in resultado] == ["Notebook Titan X15"]


def test_busca_ignora_acento():
    """O modelo escreve sem acento com frequência; exigir o acento fazia a
    busca voltar vazia e ele gastar rodadas reformulando."""
    com = repositories.listar_produtos(query="fone cancelamento ruído")
    sem = repositories.listar_produtos(query="fone cancelamento ruido")
    assert sem == com
    assert sem


def test_busca_cai_pra_casamento_parcial():
    """Um termo a mais na frase não pode zerar o resultado."""
    resultado = repositories.listar_produtos(query="fone cancelamento de ruido ativo")
    assert resultado
    assert "Fone" in resultado[0]["nome"]


def test_casamento_parcial_ordena_por_termos_casados():
    resultado = repositories.listar_produtos(query="geladeira inexistentetotal")
    assert resultado
    assert resultado[0]["categoria"] == "geladeiras"


def test_busca_sem_nenhum_termo_util():
    assert repositories.listar_produtos(query="   ") == repositories.listar_produtos()


def test_busca_casa_por_categoria_tambem():
    resultado = repositories.listar_produtos(query="geladeiras")
    assert len(resultado) >= 4


def test_busca_sem_resultado():
    assert repositories.listar_produtos(query="jetpack interplanetario") == []


def test_limite_da_busca():
    assert len(repositories.listar_produtos(limite=5)) == 5


def test_obter_produto_por_id():
    produto_id = id_por_nome("Smartphone Nova 5G")
    assert repositories.obter_produto(produto_id)["nome"] == "Smartphone Nova 5G"


def test_obter_produto_inexistente_retorna_none():
    assert repositories.obter_produto(9999) is None
