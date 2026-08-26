import json

from app import config, models
from app.ai import tools
from tests.conftest import id_por_nome


def test_toda_tool_declarada_tem_implementacao():
    declaradas = {schema["function"]["name"] for schema in tools.TOOL_SCHEMAS}
    assert declaradas == set(tools.DISPATCH)


# Ferramenta que pode ficar sem caso positivo de avaliação, com o motivo.
# A lista existe pra que a exceção seja consciente e escrita, não silenciosa.
SEM_CASO_POSITIVO = {
    # Só deve disparar depois de o cliente sumir por horas, e o harness da
    # avaliação manda uma mensagem sem histórico: nenhuma frase expressa
    # "sumiu ontem". Coberta por caso negativo em FERRAMENTAS_PROIBIDAS e
    # pelos 24 casos de tests/test_cupom.py, que controlam o relógio.
    "oferecer_cupom",
}


def test_toda_tool_tem_caso_de_avaliacao():
    """Ferramenta no manual do modelo sem régua nenhuma é como as três que
    entraram sem medição e deixaram o invariante virar ficção.

    Não chama a Groq: só compara os nomes declarados com os casos escritos.
    """
    from evals import casos

    declaradas = {schema["function"]["name"] for schema in tools.TOOL_SCHEMAS}
    sem_caso = casos.ferramentas_sem_caso(declaradas) - SEM_CASO_POSITIVO
    assert not sem_caso, (
        f"sem caso em evals/casos.py: {sorted(sem_caso)}. Escreva o caso ou "
        f"declare a exceção com motivo em SEM_CASO_POSITIVO."
    )


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


def test_rastrear_pedido_pela_tool_devolve_codigo():
    """Sem o código na resposta, a Lu não tem o que passar pro cliente."""
    pedido = tools.executar("criar_pedido", {"produto_id": id_por_nome("Air Fryer 4L Digital")})
    rastreio = tools.executar("rastrear_pedido", {"pedido_id": pedido["id"]})

    assert rastreio["codigo_rastreio"] == pedido["codigo_rastreio"]
    assert rastreio["etapa_atual"] in rastreio["etapas"]


def test_consultar_pedido_pela_tool_traz_codigo_e_etapa_valida():
    pedido = tools.executar("criar_pedido", {"produto_id": id_por_nome("Air Fryer 4L Digital")})
    consultado = tools.executar("consultar_pedido", {"pedido_id": pedido["id"]})

    assert consultado["codigo_rastreio"] == pedido["codigo_rastreio"]
    assert consultado["status"] in models.ETAPAS_RASTREIO


def test_agendar_entrega_pela_tool_nao_inventa_status():
    """O que a Lu conta pro cliente sai daqui: se o agendamento voltasse a
    virar status, ela anunciaria uma etapa que não existe."""
    pedido = tools.executar("criar_pedido", {"produto_id": id_por_nome("Air Fryer 4L Digital")})
    agendado = tools.executar(
        "agendar_entrega", {"pedido_id": pedido["id"], "data_entrega": "2026-09-15"}
    )

    assert agendado["data_entrega_agendada"] == "2026-09-15"
    assert agendado["status"] in models.ETAPAS_RASTREIO


def test_buscar_conhecimento_pela_tool():
    resultado = tools.executar("buscar_conhecimento", {"pergunta": "quantos BTUs preciso"})
    assert resultado["encontrou"] is True
    assert resultado["trechos"]


def test_buscar_conhecimento_exige_pergunta():
    resultado = tools.executar("buscar_conhecimento", {})
    assert "erro" in resultado


def test_todo_parametro_opcional_aceita_null_no_schema():
    """O modelo preenche opcional que não vai usar com null, e a Groq valida
    o argumento contra o schema antes de entregar: parâmetro opcional que
    só aceita string devolve erro 400 e derruba o chat."""
    for schema in tools.TOOL_SCHEMAS:
        parametros = schema["function"]["parameters"]
        obrigatorios = set(parametros.get("required", []))
        for nome, definicao in parametros.get("properties", {}).items():
            if nome in obrigatorios:
                continue
            tipos = definicao["type"]
            assert "null" in tipos, f"{schema['function']['name']}.{nome} não aceita null"


def test_null_vira_default_do_service():
    """Depois de passar pelo schema, o None precisa sumir antes do service,
    senão vira `categoria=None` onde se esperava string."""
    resultado = tools.executar("buscar_produtos", {"query": "notebook", "categoria": None})
    assert resultado["total_encontrado"] > 0


def test_null_em_todos_os_opcionais_de_uma_vez():
    resultado = tools.executar(
        "sugerir_produto", {"categoria": "notebooks", "criterio": None}
    )
    assert resultado["produto"]["categoria"] == "notebooks"
