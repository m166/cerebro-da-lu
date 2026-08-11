import re
from datetime import datetime, timedelta

import pytest

from app import config, exceptions, models, repositories, services
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
    custo-benefício prefere o Nova 5G, melhor avaliado e entrega em 2 dias."""
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
    assert atualizado["data_entrega_agendada"] == "2026-08-10"


def test_agendar_entrega_nao_tira_o_pedido_da_esteira():
    """Antes o agendamento virava status e sumia com a etapa logística, o
    rastreio passava a devolver uma etapa que nem existe em ETAPAS_RASTREIO."""
    pedido = services.criar_pedido(id_por_nome("Smartphone Nova 5G"))
    services.agendar_entrega(pedido["id"], "2026-08-10")

    rastreio = services.rastrear_pedido(pedido["id"])
    assert rastreio["etapa_atual"] in models.ETAPAS_RASTREIO
    assert rastreio["entrega_agendada"] == "2026-08-10"


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


# --- Progressão de status derivada do tempo --------------------------------

def _prazo_em_segundos(pedido: dict) -> float:
    produto = repositories.obter_produto(pedido["produto_id"])
    return produto["prazo_entrega_dias"] * config.SEGUNDOS_POR_DIA_ENTREGA


def _instante(pedido: dict, fracao_do_prazo: float) -> datetime:
    """Momento em que o pedido terá consumido essa fração do prazo."""
    criacao = datetime.strptime(pedido["data_criacao"], "%Y-%m-%d %H:%M:%S")
    return criacao + timedelta(seconds=_prazo_em_segundos(pedido) * fracao_do_prazo)


def test_status_derivado_percorre_as_cinco_etapas():
    pedido = services.criar_pedido(id_por_nome("Air Fryer 4L Digital"))
    fracoes = (0, 0.1, 0.3, 0.55, 0.8, 1.0)
    assert [services.status_derivado(pedido, _instante(pedido, f)) for f in fracoes] == [
        "confirmado",
        "confirmado",
        "em separação",
        "enviado",
        "saiu para entrega",
        "entregue",
    ]


def test_status_vira_no_instante_exato_da_fatia():
    """A fatia é fechada à esquerda: no instante exato da virada o pedido já
    está na etapa seguinte, não na anterior."""
    pedido = services.criar_pedido(id_por_nome("Air Fryer 4L Digital"))
    fatias = len(models.ETAPAS_RASTREIO) - 1
    viradas = [
        services.status_derivado(pedido, _instante(pedido, k / fatias))
        for k in range(fatias + 1)
    ]
    assert viradas == models.ETAPAS_RASTREIO


def test_ultimo_instante_antes_do_prazo_ainda_nao_e_entregue():
    pedido = services.criar_pedido(id_por_nome("Air Fryer 4L Digital"))
    prazo = _instante(pedido, 1.0)

    assert services.status_derivado(pedido, prazo - timedelta(microseconds=1)) == "saiu para entrega"
    assert services.status_derivado(pedido, prazo) == "entregue"


def test_status_derivado_para_em_entregue():
    pedido = services.criar_pedido(id_por_nome("Air Fryer 4L Digital"))
    assert services.status_derivado(pedido, _instante(pedido, 50)) == "entregue"


def test_relogio_atras_da_criacao_nao_estoura():
    """Ajuste de relógio pra trás daria tempo decorrido negativo, e índice
    negativo em lista Python devolve etapa contada do fim."""
    pedido = services.criar_pedido(id_por_nome("Air Fryer 4L Digital"))
    assert services.status_derivado(pedido, _instante(pedido, -3)) == "confirmado"


def test_status_nunca_anda_pra_tras_conforme_o_tempo_passa():
    posicao = {etapa: i for i, etapa in enumerate(models.ETAPAS_RASTREIO)}
    for nome in ("Air Fryer 4L Digital", "Sofá de Canto 5 Lugares", "Smartphone Nova 5G"):
        pedido = services.criar_pedido(id_por_nome(nome))
        percurso = [
            posicao[services.status_derivado(pedido, _instante(pedido, passo / 40))]
            for passo in range(0, 61)
        ]
        assert percurso == sorted(percurso), nome
        assert percurso[0] == 0 and percurso[-1] == len(models.ETAPAS_RASTREIO) - 1, nome


def test_status_derivado_e_sempre_uma_etapa_de_rastreio():
    pedido = services.criar_pedido(id_por_nome("Air Fryer 4L Digital"))
    for passo in range(0, 25):
        status = services.status_derivado(pedido, _instante(pedido, passo / 20))
        assert status in models.ETAPAS_RASTREIO


def test_prazo_maior_anda_mais_devagar():
    """A régua é o prazo do produto: no mesmo instante, o de entrega rápida
    já está mais adiante que o de entrega lenta."""
    rapido = services.criar_pedido(id_por_nome("Air Fryer 4L Digital"))
    lento = services.criar_pedido(id_por_nome("Air Fryer Oven 12L"))
    momento = _instante(rapido, 1.0)

    assert services.status_derivado(rapido, momento) == "entregue"
    assert services.status_derivado(lento, momento) != "entregue"


def test_escala_de_tempo_e_configuravel(monkeypatch):
    """Com a escala de demo o pedido chega em ~1 minuto; em tempo real, o
    mesmo instante ainda está no começo da esteira."""
    pedido = services.criar_pedido(id_por_nome("Air Fryer 4L Digital"))
    momento = _instante(pedido, 1.0)

    monkeypatch.setattr(config, "SEGUNDOS_POR_DIA_ENTREGA", 86400)
    assert services.status_derivado(pedido, momento) == "confirmado"


def test_status_derivado_sem_data_de_criacao():
    assert services.status_derivado({"id": 1, "produto_id": 1}) == "confirmado"


def test_status_derivado_de_produto_fora_do_catalogo():
    """Pedido antigo apontando pra produto que saiu do catálogo não pode
    estourar o rastreio: cai no prazo padrão."""
    pedido = {"id": 1, "produto_id": 999999, "data_criacao": "2020-01-01 10:00:00"}
    assert services.status_derivado(pedido) == "entregue"


def test_produto_fora_do_catalogo_anda_no_ritmo_do_prazo_padrao():
    criacao = datetime(2026, 1, 1, 12, 0, 0)
    pedido = {"id": 1, "produto_id": 999999, "data_criacao": "2026-01-01 12:00:00"}
    prazo = models.PRAZO_ENTREGA_PADRAO_DIAS * config.SEGUNDOS_POR_DIA_ENTREGA

    assert services.status_derivado(pedido, criacao) == "confirmado"
    assert services.status_derivado(pedido, criacao + timedelta(seconds=prazo - 1)) == "saiu para entrega"
    assert services.status_derivado(pedido, criacao + timedelta(seconds=prazo)) == "entregue"


def test_status_derivado_le_os_formatos_de_data_que_aparecem_no_banco():
    """CURRENT_TIMESTAMP grava "%Y-%m-%d %H:%M:%S", mas linha migrada à mão ou
    vinda de outra ferramenta pode chegar em ISO ou só com a data."""
    for data_criacao in (
        "2020-01-01 10:00:00",
        "2020-01-01T10:00:00.123456",
        "2020-01-01 10:00",
        "2020-01-01",
    ):
        pedido = {"id": 1, "produto_id": id_por_nome("Air Fryer 4L Digital"), "data_criacao": data_criacao}
        assert services.status_derivado(pedido) == "entregue", data_criacao


def test_data_de_criacao_ilegivel_cai_na_primeira_etapa():
    """Sem data confiável não dá pra derivar nada, e "confirmado" é o palpite
    que não promete entrega que não aconteceu."""
    pedido = {"id": 1, "produto_id": 1, "data_criacao": "ontem de manhã"}
    assert services.status_derivado(pedido) == "confirmado"


def test_status_gravado_no_banco_nao_manda_no_que_e_lido():
    """A coluna `status` é cache do último aviso; quem decide a etapa é o
    relógio, senão o pedido congelaria no valor gravado."""
    pedido = services.criar_pedido(id_por_nome("Sofá de Canto 5 Lugares"))
    repositories.marcar_status_notificado(pedido["id"], "entregue")

    assert repositories.obter_pedido(pedido["id"])["status"] == "entregue"
    assert services.obter_pedido(pedido["id"])["status"] == "confirmado"
    assert services.rastrear_pedido(pedido["id"])["etapa_atual"] == "confirmado"


def test_pedido_reflete_o_status_derivado(monkeypatch):
    pedido = services.criar_pedido(id_por_nome("Air Fryer 4L Digital"))
    assert pedido["status"] == "confirmado"

    monkeypatch.setattr(config, "SEGUNDOS_POR_DIA_ENTREGA", 0)
    assert services.obter_pedido(pedido["id"])["status"] == "entregue"
    assert services.listar_pedidos()[0]["status"] == "entregue"
    assert services.rastrear_pedido(pedido["id"])["etapa_atual"] == "entregue"


# --- Código de rastreio -----------------------------------------------------

def test_codigo_de_rastreio_no_formato_dos_correios():
    codigo = services.gerar_codigo_rastreio(1)
    assert re.fullmatch(r"[A-Z]{2}\d{9}BR", codigo), codigo


def test_digito_verificador_e_calculado_de_verdade():
    """Módulo 11 com pesos 8,6,4,2,3,5,9,7, o mesmo dos Correios."""
    for pedido_id in range(1, 200):
        codigo = services.gerar_codigo_rastreio(pedido_id)
        serie, digito = codigo[2:10], int(codigo[10])

        soma = sum(int(d) * p for d, p in zip(serie, (8, 6, 4, 2, 3, 5, 9, 7)))
        resto = soma % 11
        esperado = 5 if resto == 0 else 0 if resto == 1 else 11 - resto
        assert digito == esperado, codigo


def test_digito_verificador_nos_casos_de_excecao_do_modulo_11():
    # série 00000001: 1*7 = 7, resto 7, DV = 11 - 7 = 4
    assert services.gerar_codigo_rastreio(1) == "LU000000014BR"
    # série 00000008: 8*7 = 56, resto 1, DV = 0 (regra de exceção)
    assert services.gerar_codigo_rastreio(8) == "LU000000080BR"
    # série 00000015: 1*9 + 5*7 = 44, resto 0, DV = 5 (regra de exceção)
    assert services.gerar_codigo_rastreio(15) == "LU000000155BR"


def test_digito_verificador_usa_cada_peso_na_sua_posicao():
    """Séries quase todas zeradas só exercitam os dois últimos pesos: trocar
    8,6,4,2,3,5 de lugar passaria batido. Aqui os oito dígitos são diferentes.

    12345678: 1*8+2*6+3*4+4*2+5*3+6*5+7*9+8*7 = 204, resto 6, DV 5.
    87654321: 8*8+7*6+6*4+5*2+4*3+3*5+2*9+1*7 = 192, resto 5, DV 6.
    """
    assert services.gerar_codigo_rastreio(12345678) == "LU123456785BR"
    assert services.gerar_codigo_rastreio(87654321) == "LU876543216BR"


def test_digito_verificador_nunca_passa_de_um_digito():
    """É pra isso que existem as exceções do módulo 11: sem elas o resto 0 e o
    resto 1 dariam DV 11 e 10, e o código sairia com 14 caracteres."""
    for pedido_id in range(1, 3000):
        codigo = services.gerar_codigo_rastreio(pedido_id)
        assert re.fullmatch(r"LU\d{9}BR", codigo), codigo


def test_serie_maior_que_oito_digitos_nao_deforma_o_codigo():
    assert re.fullmatch(r"LU\d{9}BR", services.gerar_codigo_rastreio(1234567890))


def test_codigo_de_rastreio_e_deterministico_por_pedido():
    assert services.gerar_codigo_rastreio(7) == services.gerar_codigo_rastreio(7)
    assert services.gerar_codigo_rastreio(7) != services.gerar_codigo_rastreio(8)


def test_pedido_nasce_com_codigo_persistido():
    pedido = services.criar_pedido(id_por_nome("Air Fryer 4L Digital"))
    esperado = services.gerar_codigo_rastreio(pedido["id"])

    assert pedido["codigo_rastreio"] == esperado
    assert repositories.obter_pedido(pedido["id"])["codigo_rastreio"] == esperado
    assert services.rastrear_pedido(pedido["id"])["codigo_rastreio"] == esperado


def test_pedido_sem_codigo_no_banco_ganha_um_na_leitura():
    """Pedido gravado antes da coluna existir. Como o código é derivado do
    id, dá pra devolver o mesmo valor sem tocar no banco."""
    pedido = repositories.inserir_pedido(
        id_por_nome("Air Fryer 4L Digital"), "Air Fryer 4L Digital", 1, 449.00
    )
    assert pedido["codigo_rastreio"] is None
    assert services.obter_pedido(pedido["id"])["codigo_rastreio"] == (
        services.gerar_codigo_rastreio(pedido["id"])
    )


# --- Notificação automática -------------------------------------------------

def test_pedido_recem_criado_nao_gera_notificacao():
    """O cliente acabou de ver a confirmação, repetir seria eco."""
    services.criar_pedido(id_por_nome("Air Fryer 4L Digital"))
    assert services.sincronizar_notificacoes() == []


def test_notificacao_quando_o_pedido_anda():
    pedido = services.criar_pedido(id_por_nome("Air Fryer 4L Digital"))
    novas = services.sincronizar_notificacoes(_instante(pedido, 0.55))

    assert len(novas) == 1
    assert novas[0]["role"] == "assistant"
    conteudo = novas[0]["content"]
    assert f"#{pedido['id']}" in conteudo
    assert "Air Fryer 4L Digital" in conteudo
    assert pedido["codigo_rastreio"] in conteudo


def test_notificacao_entra_no_historico_do_chat():
    """Compara os campos que importam, não o dicionário inteiro: a mensagem
    ganhou campos de tela (`produtos`) que a notificação não preenche."""
    pedido = services.criar_pedido(id_por_nome("Air Fryer 4L Digital"))
    novas = services.sincronizar_notificacoes(_instante(pedido, 0.55))

    gravadas = repositories.listar_mensagens()
    assert len(gravadas) == len(novas) == 1
    for gravada, nova in zip(gravadas, novas):
        assert gravada["role"] == nova["role"]
        assert gravada["content"] == nova["content"]
        assert gravada["tipo"] == nova["tipo"]


def test_notificacao_e_idempotente():
    pedido = services.criar_pedido(id_por_nome("Air Fryer 4L Digital"))
    momento = _instante(pedido, 0.55)

    assert len(services.sincronizar_notificacoes(momento)) == 1
    assert services.sincronizar_notificacoes(momento) == []
    assert len(repositories.listar_mensagens()) == 1


def test_notificacao_avisa_o_estado_atual_sem_repetir_etapas_puladas():
    """Quem ficou horas sem abrir o chat não merece cinco mensagens de uma
    vez: vale o estado em que o pedido está agora."""
    pedido = services.criar_pedido(id_por_nome("Air Fryer 4L Digital"))
    novas = services.sincronizar_notificacoes(_instante(pedido, 2))

    assert len(novas) == 1
    assert "entregue" in novas[0]["content"]


def test_cada_etapa_nova_rende_uma_mensagem_e_o_historico_nao_duplica():
    pedido = services.criar_pedido(id_por_nome("Air Fryer 4L Digital"))
    for fracao in (0.3, 0.55, 0.8, 1.0):
        momento = _instante(pedido, fracao)
        assert len(services.sincronizar_notificacoes(momento)) == 1
        assert services.sincronizar_notificacoes(momento) == []

    conteudos = [m["content"] for m in repositories.listar_mensagens()]
    assert len(conteudos) == 4
    assert len(set(conteudos)) == 4


def test_notificacao_nao_desanuncia_quando_a_etapa_recua(monkeypatch):
    """A etapa é derivada do relógio e da régua, então pode andar pra trás
    (escala trocada entre execuções, prazo aumentado no catálogo). Avisar
    "foi confirmado" depois de "foi entregue" é pior que não avisar nada."""
    pedido = services.criar_pedido(id_por_nome("Air Fryer 4L Digital"))
    momento = _instante(pedido, 2)
    assert len(services.sincronizar_notificacoes(momento)) == 1

    monkeypatch.setattr(config, "SEGUNDOS_POR_DIA_ENTREGA", 86400)
    assert services.status_derivado(services.obter_pedido(pedido["id"]), momento) == "confirmado"
    assert services.sincronizar_notificacoes(momento) == []
    assert len(repositories.listar_mensagens()) == 1


def test_notificacao_so_menciona_quem_andou():
    """O sofá demora 14 dias e ainda está confirmado quando a air fryer, de 3,
    já chegou: notificar os dois seria inventar movimento."""
    rapido = services.criar_pedido(id_por_nome("Air Fryer 4L Digital"))
    lento = services.criar_pedido(id_por_nome("Sofá de Canto 5 Lugares"))
    novas = services.sincronizar_notificacoes(_instante(rapido, 1.0))

    assert len(novas) == 1
    assert f"#{rapido['id']}" in novas[0]["content"]
    assert f"#{lento['id']}" not in novas[0]["content"]


def test_notificacao_de_varios_pedidos_sai_na_ordem_dos_pedidos():
    primeiro = services.criar_pedido(id_por_nome("Air Fryer 4L Digital"))
    segundo = services.criar_pedido(id_por_nome("Air Fryer 3L Mecânica"))
    novas = services.sincronizar_notificacoes(_instante(primeiro, 5))

    assert [f"#{primeiro['id']}" in n["content"] for n in novas] == [True, False]
    assert f"#{segundo['id']}" in novas[1]["content"]


def test_notificacao_cita_codigo_so_quando_ha_o_que_rastrear():
    pedido = services.criar_pedido(id_por_nome("Air Fryer 4L Digital"))
    codigo = pedido["codigo_rastreio"]

    em_separacao = services.sincronizar_notificacoes(_instante(pedido, 0.3))
    assert codigo not in em_separacao[0]["content"]

    enviado = services.sincronizar_notificacoes(_instante(pedido, 0.55))
    assert codigo in enviado[0]["content"]


def test_toda_etapa_tem_texto_de_notificacao():
    assert set(models.MENSAGENS_NOTIFICACAO) == set(models.ETAPAS_RASTREIO)


def test_entrega_agendada_nao_e_mais_status():
    """O bug era esse: o rastreio devolvia uma etapa que não existia na
    lista de etapas."""
    assert "entrega agendada" not in models.ETAPAS_RASTREIO
    assert "entrega agendada" not in models.LOCALIZACOES_MOCK
    assert set(models.LOCALIZACOES_MOCK) == set(models.ETAPAS_RASTREIO)


def test_notificacao_nao_duplica_quando_duas_abas_sincronizam():
    """Duas abas fazendo poll liam o mesmo estado antigo e gravavam a mesma
    mensagem duas vezes. Quem decide quem avisa é o UPDATE condicional."""
    pedido = services.criar_pedido(id_por_nome("Notebook Titan X15"))
    meio = _instante(pedido, 0.5)

    primeira = services.sincronizar_notificacoes(meio)
    segunda = services.sincronizar_notificacoes(meio)

    assert len(primeira) == 1
    assert segunda == []
    avisos = [m for m in repositories.listar_mensagens() if m["role"] == "assistant"]
    assert len(avisos) == 1


def test_reserva_do_aviso_e_de_quem_chega_primeiro():
    """`marcar_status_notificado` devolve se conseguiu reservar, e é isso que
    o service usa pra decidir se grava a mensagem."""
    pedido = services.criar_pedido(id_por_nome("Notebook Titan X15"))
    assert repositories.marcar_status_notificado(pedido["id"], "enviado") is True
    assert repositories.marcar_status_notificado(pedido["id"], "enviado") is False
    assert repositories.marcar_status_notificado(pedido["id"], "entregue") is True


# --- Cadastro do cliente ---------------------------------------------------

def test_endereco_do_pedido_vira_cadastro():
    """Quem informou o endereço uma vez não pode ser perguntado de novo."""
    services.criar_pedido(id_por_nome("Smartphone Nova 5G"), endereco_entrega="Rua A, 1")
    assert services.dados_do_cliente()["endereco"] == "Rua A, 1"


def test_pedido_sem_endereco_usa_o_cadastrado():
    services.criar_pedido(id_por_nome("Smartphone Nova 5G"), endereco_entrega="Rua A, 1")
    segundo = services.criar_pedido(id_por_nome("Mouse Gamer 16000 DPI"))
    assert segundo["endereco_entrega"] == "Rua A, 1"


def test_endereco_novo_substitui_o_antigo():
    services.criar_pedido(id_por_nome("Smartphone Nova 5G"), endereco_entrega="Rua A, 1")
    services.criar_pedido(id_por_nome("Mouse Gamer 16000 DPI"), endereco_entrega="Rua B, 2")
    assert services.dados_do_cliente()["endereco"] == "Rua B, 2"


def test_cadastro_vazio_nao_inventa_campo():
    assert services.dados_do_cliente() == {}


def test_salvar_e_ler_nome():
    services.salvar_dado_do_cliente("nome", "  Matheus  ")
    assert services.dados_do_cliente()["nome"] == "Matheus"


def test_campo_desconhecido_e_recusado():
    with pytest.raises(exceptions.CampoDePerfilInvalido):
        services.salvar_dado_do_cliente("cpf", "123")


def test_valor_vazio_e_recusado():
    with pytest.raises(exceptions.CampoDePerfilInvalido):
        services.salvar_dado_do_cliente("nome", "   ")
