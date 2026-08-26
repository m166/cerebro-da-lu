"""Adequação ao canal WhatsApp.

O que estes testes protegem não é código bonito, é mensagem entregue: erro
de template ou de janela não aparece como bug aqui, aparece como 400 da Meta
ou como cliente que nunca recebeu o aviso de que o pedido saiu pra entrega.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app import models, repositories, services, whatsapp


# --- Templates --------------------------------------------------------------

def test_todo_status_de_rastreio_tem_template():
    """Etapa sem template é etapa que não pode ser avisada fora da janela."""
    assert set(models.TEMPLATES_NOTIFICACAO) == set(models.ETAPAS_RASTREIO)


def test_templates_sao_utility():
    """UTILITY porque seguem a compra e não vendem nada. Se algum virar
    MARKETING, a Meta passa a exigir opt-in e cobra mais caro."""
    for template in models.TEMPLATES_NOTIFICACAO.values():
        assert template.categoria == whatsapp.CATEGORIA_UTILIDADE


def test_templates_cabem_no_limite_da_meta():
    for template in models.TEMPLATES_NOTIFICACAO.values():
        assert len(template.corpo) <= whatsapp.LIMITE_CORPO_TEMPLATE


def test_template_declara_exemplo_para_cada_parametro():
    """A Meta recusa o cadastro sem exemplo, e o erro só aparece na aprovação."""
    for template in models.TEMPLATES_NOTIFICACAO.values():
        assert len(template.exemplo) == len(template.parametros)


def test_nome_de_template_invalido_falha_na_definicao():
    with pytest.raises(whatsapp.TemplateInvalido):
        whatsapp.Template(nome="Pedido Enviado", corpo="oi", parametros=[])


def test_corpo_com_parametro_a_mais_falha_na_definicao():
    """Marcador sem parâmetro declarado chegaria ao cliente como "{{2}}"."""
    with pytest.raises(whatsapp.TemplateInvalido):
        whatsapp.Template(
            nome="teste", corpo="Pedido {{1}} de {{2}}", parametros=["id"]
        )


def test_corpo_grande_demais_falha_na_definicao():
    with pytest.raises(whatsapp.TemplateInvalido):
        whatsapp.Template(
            nome="teste", corpo="x" * (whatsapp.LIMITE_CORPO_TEMPLATE + 1), parametros=[]
        )


def test_renderizar_substitui_na_ordem_declarada():
    template = models.TEMPLATES_NOTIFICACAO["enviado"]
    texto = template.renderizar(id=7, produto="Air Fryer", codigo="LU000000077BR")
    assert texto == "Seu pedido #7 (Air Fryer) foi enviado. Código de rastreio: LU000000077BR"


def test_renderizar_sem_parametro_falha():
    with pytest.raises(whatsapp.TemplateInvalido):
        models.TEMPLATES_NOTIFICACAO["enviado"].renderizar(id=7, produto="Air Fryer")


def test_cadastro_tem_o_formato_que_a_meta_espera():
    cadastro = models.TEMPLATES_NOTIFICACAO["confirmado"].cadastro()
    assert cadastro["name"] == "pedido_confirmado"
    assert cadastro["language"] == "pt_BR"
    assert cadastro["category"] == "UTILITY"
    assert cadastro["components"][0]["type"] == "BODY"
    assert "{{1}}" in cadastro["components"][0]["text"]


# --- O aviso do pedido ------------------------------------------------------

def test_texto_do_aviso_vem_do_template(monkeypatch):
    """A tela e o canal usam a mesma fonte. Se divergirem, o cliente recebe
    uma frase aprovada meses antes e vê outra no histórico."""
    pedido = services.criar_pedido(1)
    texto = services._texto_da_notificacao(pedido, "confirmado")
    assert texto == models.TEMPLATES_NOTIFICACAO["confirmado"].renderizar(
        id=pedido["id"], produto=pedido["produto_nome"]
    )


def test_payload_de_envio_leva_parametros_na_ordem():
    pedido = services.criar_pedido(1)
    payload = services.notificacao_para_envio(pedido, "enviado")

    assert payload["messaging_product"] == "whatsapp"
    assert payload["type"] == "template"
    assert payload["template"]["name"] == "pedido_enviado"
    valores = [p["text"] for p in payload["template"]["components"][0]["parameters"]]
    assert valores == [
        str(pedido["id"]),
        pedido["produto_nome"],
        str(pedido["codigo_rastreio"]),
    ]


def test_payload_endereca_o_numero_da_sessao():
    """O `to` da Cloud API é o wa_id, que é exatamente o formato do sessao_id."""
    pedido = services.criar_pedido(1)
    payload = services.notificacao_para_envio(pedido, "confirmado")
    assert payload["to"] == pedido["sessao_id"]


def test_status_sem_template_nao_vira_envio():
    """Inventar nome de template no envio devolveria erro da Meta, não
    mensagem. Melhor não ter payload do que ter um que falha."""
    pedido = services.criar_pedido(1)
    assert services.notificacao_para_envio(pedido, "entrega agendada") is None


# --- Janela de 24 horas -----------------------------------------------------

def test_sem_mensagem_do_cliente_a_janela_nunca_abriu():
    assert whatsapp.dentro_da_janela(None) is False


def test_janela_aberta_logo_depois_da_mensagem():
    agora = datetime.now(timezone.utc)
    assert whatsapp.dentro_da_janela(agora - timedelta(hours=3), agora=agora) is True


def test_janela_fechada_depois_de_24_horas():
    agora = datetime.now(timezone.utc)
    assert whatsapp.dentro_da_janela(agora - timedelta(hours=25), agora=agora) is False


def test_data_sem_fuso_e_tratada_como_utc():
    """O banco devolve UTC. Comparar ingênuo com ciente estouraria TypeError."""
    agora = datetime.now(timezone.utc)
    ingenua = (agora - timedelta(hours=1)).replace(tzinfo=None)
    assert whatsapp.dentro_da_janela(ingenua, agora=agora) is True


def test_resposta_da_lu_nao_reabre_a_janela():
    """Se a fala da Lu contasse, bastaria a loja falar sozinha pra manter a
    conversa aberta pra sempre, e a Meta cobraria template mesmo assim."""
    repositories.inserir_mensagem("assistant", "oi, tudo bem?")
    assert services.canal_aceita_texto_livre() is False

    repositories.inserir_mensagem("user", "quero um fone")
    assert services.canal_aceita_texto_livre() is True


def test_janela_expira_com_a_conversa_parada():
    repositories.inserir_mensagem("user", "quero um fone")
    daqui_a_dois_dias = datetime.now(timezone.utc) + timedelta(days=2)
    assert services.canal_aceita_texto_livre(agora=daqui_a_dois_dias) is False


# --- Formatação -------------------------------------------------------------

def test_negrito_usa_um_asterisco():
    assert whatsapp.negrito("à vista") == "*à vista*"


def test_persona_nao_pede_negrito_de_markdown():
    """A persona mandava usar `**`, que no WhatsApp aparece como asterisco na
    tela do cliente. Este teste segura a volta do markdown."""
    from app import config

    persona = config.persona()
    assert "**negrito**" not in persona
    assert "um asterisco de cada lado" in persona


def test_resposta_da_lu_cabe_no_texto_livre():
    """O teto da persona (400) é folgado perto do limite do canal (4096), mas
    o limite existe e quem escreve mensagem longa precisa saber onde ele é."""
    assert whatsapp.cabe_em_texto_livre("x" * 4096) is True
    assert whatsapp.cabe_em_texto_livre("x" * 4097) is False
