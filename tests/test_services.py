import pytest

from app import exceptions, services
from tests.conftest import id_por_nome


# --- Catálogo e estoque ---------------------------------------------------

def test_obter_produto_inexistente_levanta():
    with pytest.raises(exceptions.ProdutoNaoEncontrado):
        services.obter_produto(9999)


def test_consultar_estoque():
    produto_id = id_por_nome("Notebook Titan X15")
    resultado = services.consultar_estoque(produto_id)
    assert resultado["estoque"] == 12
    assert resultado["disponivel"] is True


def test_listar_categorias():
    categorias = services.listar_categorias()
    assert "notebooks" in categorias
    assert len(categorias) >= 20


# --- Sugestão ---------------------------------------------------------------

def test_sugerir_melhor_preco():
    resultado = services.sugerir_produto(categoria="notebooks", criterio="melhor_preco")
    assert resultado["produto"]["nome"] == "Notebook Essencial 14"


def test_sugerir_melhor_prazo():
    resultado = services.sugerir_produto(categoria="notebooks", criterio="melhor_prazo")
    assert resultado["produto"]["nome"] == "Notebook UltraBook Air 13"


def test_sugerir_melhor_avaliacao():
    resultado = services.sugerir_produto(categoria="audio", criterio="melhor_avaliacao")
    assert resultado["produto"]["nome"] == "Fone de Ouvido Studio Monitor"


def test_custo_beneficio_pesa_avaliacao_e_prazo_alem_do_preco():
    """Em celulares o mais barato é o Basic Go (3.7 estrelas, 7 dias), mas o
    custo-benefício prefere o Nova 5G — melhor avaliado e entrega em 2 dias."""
    barato = services.sugerir_produto(categoria="celulares", criterio="melhor_preco")
    equilibrado = services.sugerir_produto(categoria="celulares", criterio="melhor_custo_beneficio")
    assert barato["produto"]["nome"] == "Smartphone Basic Go"
    assert equilibrado["produto"]["nome"] == "Smartphone Nova 5G"


def test_custo_beneficio_pode_coincidir_com_o_mais_barato():
    """Ser o mais barato não desqualifica: nos notebooks o Essencial 14 ganha
    nos dois critérios, porque a diferença de preço pros outros é grande e a
    avaliação dele não é ruim."""
    barato = services.sugerir_produto(categoria="notebooks", criterio="melhor_preco")
    equilibrado = services.sugerir_produto(categoria="notebooks", criterio="melhor_custo_beneficio")
    assert barato["produto"]["nome"] == equilibrado["produto"]["nome"] == "Notebook Essencial 14"


def test_custo_beneficio_e_o_criterio_padrao():
    assert services.sugerir_produto(categoria="tvs") == services.sugerir_produto(
        categoria="tvs", criterio="melhor_custo_beneficio"
    )


def test_sugerir_categoria_inexistente_levanta():
    with pytest.raises(exceptions.SemProdutosDisponiveis):
        services.sugerir_produto(categoria="jetpacks")


# --- Comparação -------------------------------------------------------------

def test_comparar_por_categoria():
    resultado = services.comparar_produtos(categoria="celulares")
    assert len(resultado["produtos"]) == 6
    assert resultado["melhor_preco"] == "Smartphone Basic Go"
    assert resultado["melhor_avaliacao"] == "Smartphone Galaxy Vision Ultra"
    assert resultado["melhor_prazo"] == "Smartphone Nova 5G"


def test_comparar_por_ids():
    ids = [id_por_nome("Smart TV 32'' HD"), id_por_nome("Smart TV 75'' 8K Premium")]
    resultado = services.comparar_produtos(produto_ids=ids)
    assert resultado["melhor_preco"] == "Smart TV 32'' HD"
    assert resultado["melhor_avaliacao"] == "Smart TV 75'' 8K Premium"


def test_comparar_com_menos_de_dois_produtos_levanta():
    with pytest.raises(exceptions.ComparacaoInvalida):
        services.comparar_produtos(produto_ids=[id_por_nome("Mouse Sem Fio Básico")])


def test_comparar_ignora_ids_inexistentes():
    ids = [id_por_nome("Mouse Sem Fio Básico"), 99999]
    with pytest.raises(exceptions.ComparacaoInvalida):
        services.comparar_produtos(produto_ids=ids)


# --- Pedidos -------------------------------------------------------------

def test_criar_pedido_calcula_valor_total():
    produto_id = id_por_nome("Fone de Ouvido Bluetooth ProSound")
    pedido = services.criar_pedido(produto_id, quantidade=2)
    assert pedido["valor_total"] == 699.80


def test_criar_pedido_produto_inexistente_levanta():
    with pytest.raises(exceptions.ProdutoNaoEncontrado):
        services.criar_pedido(9999)


def test_criar_pedido_estoque_insuficiente_levanta():
    produto_id = id_por_nome("Geladeira French Door 540L")
    with pytest.raises(exceptions.EstoqueInsuficiente):
        services.criar_pedido(produto_id, quantidade=100)


def test_listar_pedidos_vazio():
    assert services.listar_pedidos() == []


def test_listar_pedidos_traz_todos():
    services.criar_pedido(id_por_nome("Smartphone Nova 5G"))
    services.criar_pedido(id_por_nome("Mouse Gamer 16000 DPI"))
    assert len(services.listar_pedidos()) == 2


def test_rastrear_pedido():
    pedido = services.criar_pedido(id_por_nome("Smartphone Nova 5G"))
    rastreio = services.rastrear_pedido(pedido["id"])
    assert rastreio["etapa_atual"] == "confirmado"
    assert "Louveira" in rastreio["localizacao"]


def test_rastrear_pedido_inexistente_levanta():
    with pytest.raises(exceptions.PedidoNaoEncontrado):
        services.rastrear_pedido(9999)


def test_agendar_entrega():
    pedido = services.criar_pedido(id_por_nome("Smartphone Nova 5G"))
    atualizado = services.agendar_entrega(pedido["id"], "2026-08-10")
    assert atualizado["status"] == "entrega agendada"
    assert atualizado["data_entrega_agendada"] == "2026-08-10"


def test_agendar_entrega_pedido_inexistente_levanta():
    with pytest.raises(exceptions.PedidoNaoEncontrado):
        services.agendar_entrega(9999, "2026-08-10")


def test_segunda_via_boleto():
    pedido = services.criar_pedido(id_por_nome("Smartphone Nova 5G"))
    documento = services.gerar_segunda_via(pedido["id"], "boleto")
    assert documento["tipo"] == "boleto"
    assert documento["valor"] == pedido["valor_total"]


def test_segunda_via_nf():
    pedido = services.criar_pedido(id_por_nome("Smartphone Nova 5G"))
    documento = services.gerar_segunda_via(pedido["id"], "nf")
    assert documento["tipo"] == "nota_fiscal"
    assert documento["numero_nf"] == f"NF-{pedido['id']:06d}"


def test_segunda_via_pedido_inexistente_levanta():
    with pytest.raises(exceptions.PedidoNaoEncontrado):
        services.gerar_segunda_via(9999)
