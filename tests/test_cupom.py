"""Cupom de desconto limitado pela margem.

Estes testes protegem dinheiro, então a maior parte deles verifica o que o
sistema **se recusa** a fazer. Um cupom generoso demais não dá erro, não
aparece em log e não quebra teste nenhum: ele só some do lucro, uma venda
por vez.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app import abandono, config, cupom, exceptions, models, repositories, services
from app.data import catalogo
from tests.conftest import id_por_nome


# --- A conta, que é o núcleo -----------------------------------------------

def _produto_do_exemplo():
    """O caso do enunciado: R$ 2.000 de preço, R$ 400 de margem líquida."""
    return {
        "id": 999,
        "nome": "Produto do exemplo",
        "categoria": "exemplo-margem-20",
        "preco": 2000.00,
    }


@pytest.fixture(autouse=True)
def margem_do_exemplo(monkeypatch):
    monkeypatch.setitem(catalogo.MARGEM_POR_CATEGORIA, "exemplo-margem-20", 0.20)


def test_desconto_e_fracao_da_margem_nao_do_preco():
    """R$ 2.000 com margem de R$ 400, a 30% da margem, dá R$ 120.

    O erro que este teste existe pra impedir é dar 30% do preço, R$ 600,
    numa venda que só tem R$ 400 de lucro: prejuízo de R$ 200.
    """
    oferta = cupom.calcular(_produto_do_exemplo())
    assert oferta["margem_liquida"] == 400.00
    assert oferta["valor_desconto"] == 120.00
    assert oferta["preco_final"] == 1880.00


def test_desconto_em_percentual_do_preco_e_pequeno():
    """E isso é esperado: 120 em 2000 são 6%, não 30%."""
    assert cupom.calcular(_produto_do_exemplo())["percentual_no_preco"] == 6.0


def test_margem_sobra_positiva_sempre():
    for produto in catalogo.PRODUTOS:
        try:
            oferta = cupom.calcular(produto)
        except cupom.DescontoInviavel:
            continue
        assert oferta["margem_restante"] > 0, produto["nome"]
        assert oferta["valor_desconto"] < oferta["margem_liquida"], produto["nome"]


def test_pedir_mais_que_o_teto_nao_ultrapassa_o_teto():
    """A fração é parâmetro, mas o teto é lei. Se algum dia alguém passar um
    número maior, o teto continua valendo."""
    abusivo = cupom.calcular(_produto_do_exemplo(), percentual_da_margem=0.95)
    assert abusivo["valor_desconto"] == 120.00


def test_pedir_menos_que_o_teto_e_permitido():
    """Serve pra começar com uma oferta menor e guardar margem pra depois."""
    metade = cupom.calcular(_produto_do_exemplo(), percentual_da_margem=0.15)
    assert metade["valor_desconto"] == 60.00


def test_arredonda_para_baixo():
    """Meio centavo a mais é meio centavo de margem que não existia."""
    produto = {**_produto_do_exemplo(), "preco": 999.99}
    oferta = cupom.calcular(produto)
    bruto = catalogo.margem_liquida(produto) * config.PERCENTUAL_MAXIMO_DA_MARGEM
    assert oferta["valor_desconto"] <= bruto


def test_margem_magra_nao_gera_cupom_ridiculo():
    """Desconto de R$ 2 não convence ninguém e queima margem à toa."""
    magro = {**_produto_do_exemplo(), "preco": 100.00}
    with pytest.raises(cupom.DescontoInviavel):
        cupom.calcular(magro)


def test_todo_produto_do_catalogo_tem_margem():
    for produto in catalogo.PRODUTOS:
        assert catalogo.margem_liquida(produto) > 0, produto["nome"]


def test_categoria_nova_cai_no_padrao_em_vez_de_estourar():
    orfao = {"id": 0, "nome": "Categoria Inédita", "categoria": "nao-existe", "preco": 500.0}
    assert catalogo.margem_liquida(orfao) == round(500.0 * catalogo.MARGEM_PADRAO, 2)


def test_codigo_nao_e_sequencial():
    """Código adivinhável é desconto dado a quem não precisava."""
    codigos = {cupom.gerar_codigo() for _ in range(200)}
    assert len(codigos) == 200


def test_codigo_evita_caracteres_ambiguos():
    """0/O e 1/I geram "o cupom não funciona" no atendimento."""
    for _ in range(50):
        assert not set(cupom.gerar_codigo()[2:]) & set("O0I1S5")


# --- A trava: nunca antes do abandono --------------------------------------

def _conversa_com_interesse():
    produto_id = id_por_nome("Air Fryer 4L Digital")
    repositories.inserir_mensagem("user", "quero uma air fryer")
    repositories.inserir_mensagem("assistant", "essa aqui", produtos=[produto_id])
    return produto_id


def test_nao_oferece_cupom_com_a_conversa_quente():
    """O pedido foi explícito: nunca antes de o cliente estar desistindo."""
    produto_id = _conversa_com_interesse()
    with pytest.raises(exceptions.CupomAindaNaoCabe):
        services.oferecer_cupom(produto_id)


def test_nao_oferece_cupom_sem_interesse_demonstrado():
    """Quem só perguntou o horário da loja não abandonou compra nenhuma."""
    repositories.inserir_mensagem("user", "vocês abrem sábado?")
    with pytest.raises(exceptions.CupomAindaNaoCabe):
        services.oferecer_cupom(id_por_nome("Air Fryer 4L Digital"))


def test_oferece_cupom_depois_de_dias_de_silencio():
    produto_id = _conversa_com_interesse()
    daqui_a_tres_dias = datetime.now(timezone.utc) + timedelta(days=3)

    oferta = services.oferecer_cupom(produto_id, agora=daqui_a_tres_dias)
    assert oferta["valor_desconto"] > 0
    assert oferta["codigo"].startswith("LU")
    assert "sumiu há" in oferta["motivo_da_oferta"]


def test_cupom_nao_sai_pra_quem_ja_comprou():
    """Silêncio depois da compra é cliente satisfeito, não carrinho largado."""
    produto_id = id_por_nome("Air Fryer 4L Digital")
    repositories.inserir_mensagem("assistant", "essa aqui", produtos=[produto_id])
    repositories.inserir_mensagem("user", "quero essa")
    services.criar_pedido(produto_id)

    daqui_a_tres_dias = datetime.now(timezone.utc) + timedelta(days=3)
    with pytest.raises(exceptions.CupomAindaNaoCabe):
        services.oferecer_cupom(produto_id, agora=daqui_a_tres_dias)


def test_limite_de_cupons_por_conversa():
    """Sem teto, quem aprende a sumir vira torneira aberta de desconto."""
    produto_id = _conversa_com_interesse()
    outro = id_por_nome("Notebook Titan X15")
    depois = datetime.now(timezone.utc) + timedelta(days=3)

    for produto in [produto_id, outro][: config.MAX_CUPONS_POR_SESSAO]:
        services.oferecer_cupom(produto, agora=depois)

    with pytest.raises(exceptions.CupomAindaNaoCabe):
        services.oferecer_cupom(id_por_nome("Notebook Essencial 14"), agora=depois)


def test_nao_emite_dois_cupons_abertos_pro_mesmo_produto():
    produto_id = _conversa_com_interesse()
    depois = datetime.now(timezone.utc) + timedelta(days=3)
    services.oferecer_cupom(produto_id, agora=depois)

    with pytest.raises(exceptions.CupomAindaNaoCabe):
        services.oferecer_cupom(produto_id, agora=depois)


# --- Resgate ----------------------------------------------------------------

def test_cupom_nao_vale_pra_outro_produto():
    """A margem do mouse não sustenta o desconto do mouse num notebook."""
    produto_id = _conversa_com_interesse()
    depois = datetime.now(timezone.utc) + timedelta(days=3)
    oferta = services.oferecer_cupom(produto_id, agora=depois)

    with pytest.raises(exceptions.CupomInvalido):
        services.validar_cupom(oferta["codigo"], id_por_nome("Notebook Titan X15"))


def test_cupom_so_pode_ser_usado_uma_vez():
    produto_id = _conversa_com_interesse()
    depois = datetime.now(timezone.utc) + timedelta(days=3)
    oferta = services.oferecer_cupom(produto_id, agora=depois)

    assert repositories.marcar_cupom_usado(oferta["codigo"]) is True
    assert repositories.marcar_cupom_usado(oferta["codigo"]) is False


def test_codigo_inexistente_e_recusado():
    with pytest.raises(exceptions.CupomInvalido):
        services.validar_cupom("LUZZZZZ", 1)


def test_cupom_de_outra_sessao_nao_e_encontrado():
    """Desconto não atravessa cliente."""
    from app import sessao

    produto_id = _conversa_com_interesse()
    depois = datetime.now(timezone.utc) + timedelta(days=3)
    oferta = services.oferecer_cupom(produto_id, agora=depois)

    token = sessao.definir("5511900002222")
    try:
        with pytest.raises(exceptions.CupomInvalido):
            services.validar_cupom(oferta["codigo"], produto_id)
    finally:
        sessao.restaurar(token)


# --- O template do canal ----------------------------------------------------

def test_cupom_e_template_marketing_e_nao_utility():
    """Não é escolha: oferecer desconto é promocional, e a Meta reclassifica
    sozinha quem declarar utility. Reclassificado custa mais e exige opt-in."""
    assert models.TEMPLATE_CUPOM.categoria == whatsapp_categoria_marketing()


def whatsapp_categoria_marketing():
    from app import whatsapp

    return whatsapp.CATEGORIA_MARKETING


def test_template_do_cupom_cabe_no_limite():
    from app import whatsapp

    assert len(models.TEMPLATE_CUPOM.corpo) <= whatsapp.LIMITE_CORPO_TEMPLATE


def test_template_do_cupom_renderiza_com_todos_os_parametros():
    texto = models.TEMPLATE_CUPOM.renderizar(
        nome="Matheus",
        produto="Air Fryer 4L Digital",
        desconto="45,00",
        codigo="LUX7K2M",
        validade="16/08",
        preco_final="404,00",
    )
    assert "LUX7K2M" in texto and "45,00" in texto
