import json

from app import config
from app.ai import tools
from tests.conftest import id_por_nome


def test_toda_tool_declarada_tem_implementacao():
    declaradas = {schema["function"]["name"] for schema in tools.TOOL_SCHEMAS}
    assert declaradas == set(tools.DISPATCH)


def test_busca_limita_resultados_pro_modelo():
    """Mandar 100+ produtos pro modelo estouraria o contexto sem necessidade."""
    resultado = tools.executar("buscar_produtos", {})
    assert resultado["total_encontrado"] >= 100
    assert resultado["mostrando"] == config.LIMITE_BUSCA_TOOL
    assert len(resultado["produtos"]) == config.LIMITE_BUSCA_TOOL


def test_busca_respeita_teto_de_limite():
    resultado = tools.executar("buscar_produtos", {"limite": 500})
    assert resultado["mostrando"] == 30


def test_listar_categorias():
    resultado = tools.executar("listar_categorias", {})
    assert "notebooks" in resultado["categorias"]


def test_erro_de_dominio_vira_campo_erro():
    """O modelo lida melhor com {"erro": ...} do que com exceção."""
    resultado = tools.executar("criar_pedido", {"produto_id": 9999})
    assert "erro" in resultado
    assert "não encontrado" in resultado["erro"]


def test_estoque_insuficiente_vira_campo_erro():
    produto_id = id_por_nome("Geladeira French Door 540L")
    resultado = tools.executar("criar_pedido", {"produto_id": produto_id, "quantidade": 100})
    assert "Estoque insuficiente" in resultado["erro"]


def test_ferramenta_desconhecida():
    resultado = tools.executar("hackear_a_nasa", {})
    assert "desconhecida" in resultado["erro"]


def test_argumentos_invalidos_nao_estouram():
    resultado = tools.executar("consultar_estoque", {"parametro_que_nao_existe": 1})
    assert "erro" in resultado


def test_executar_json_serializa_resposta():
    produto_id = id_por_nome("Smartphone Nova 5G")
    saida = tools.executar_json("consultar_estoque", json.dumps({"produto_id": produto_id}))
    assert json.loads(saida)["nome"] == "Smartphone Nova 5G"


def test_executar_json_aceita_argumentos_vazios():
    saida = tools.executar_json("listar_categorias", "")
    assert "notebooks" in json.loads(saida)["categorias"]


def test_comparar_produtos_pela_tool():
    resultado = tools.executar("comparar_produtos", {"categoria": "audio"})
    assert resultado["melhor_avaliacao"] == "Fone de Ouvido Studio Monitor"
