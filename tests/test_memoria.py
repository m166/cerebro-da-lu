"""O que a Lu lembra da conversa depois que a janela de histórico corta.

O modelo só enxerga `MAX_MENSAGENS_CONTEXTO` mensagens. O que ficou pra trás
sumiu, e foi assim que ela pediu o endereço duas vezes. O cadastro resolveu
isso pro que é permanente; esta camada resolve pro que vale só nesta compra:
orçamento, o que foi descartado, pra quem é, e o que ela já mostrou.
"""

import pytest

from app import config, exceptions, models, repositories, services
from app.ai import chat
from tests.conftest import id_por_nome


# --- Anotação ---------------------------------------------------------------

def test_anota_e_devolve_o_que_sabe():
    services.anotar_da_conversa("orcamento", "até 2 mil")
    assert services.memoria_da_conversa()["orcamento"] == "até 2 mil"


def test_anotacao_nova_substitui_a_antiga():
    """O cliente muda de ideia, e o que vale é a última fala dele."""
    services.anotar_da_conversa("orcamento", "até 2 mil")
    services.anotar_da_conversa("orcamento", "posso ir até 3 mil")
    assert services.memoria_da_conversa()["orcamento"] == "posso ir até 3 mil"


def test_campo_inventado_e_recusado():
    """Sem isto, o modelo criaria campo livre e a memória viraria depósito."""
    with pytest.raises(exceptions.CampoDeMemoriaInvalido):
        services.anotar_da_conversa("cor_favorita", "azul")


def test_valor_vazio_e_recusado():
    with pytest.raises(exceptions.CampoDeMemoriaInvalido):
        services.anotar_da_conversa("orcamento", "   ")


def test_memoria_nao_e_cadastro():
    """São tabelas diferentes de propósito: o orçamento desta compra não pode
    virar dado permanente do cliente."""
    services.anotar_da_conversa("orcamento", "até 2 mil")
    assert "orcamento" not in services.dados_do_cliente()

    services.salvar_dado_do_cliente("nome", "Matheus")
    assert "nome" not in services.memoria_da_conversa()


def test_memoria_e_por_sessao():
    """Vazar isso entre clientes seria pior que esquecer."""
    from app import sessao

    token = sessao.definir("5511999990000")
    services.anotar_da_conversa("orcamento", "até 500")
    sessao.restaurar(token)

    token = sessao.definir("5511988881234")
    assert services.memoria_da_conversa() == {}
    sessao.restaurar(token)


# --- O que já foi sugerido, derivado das mensagens --------------------------

def test_produtos_ja_mostrados_saem_do_historico():
    """Não se anota o que dá pra derivar: os ids já estão em
    `messages.produtos`, gravados pra montar os cartões."""
    produto_id = id_por_nome("Air Fryer 4L Digital")
    repositories.inserir_mensagem("assistant", "essa é boa", produtos=[produto_id])

    assert "Air Fryer 4L Digital" in services.memoria_da_conversa()["ja_sugeridos"]


def test_produto_repetido_aparece_uma_vez_so():
    produto_id = id_por_nome("Air Fryer 4L Digital")
    repositories.inserir_mensagem("assistant", "essa", produtos=[produto_id])
    repositories.inserir_mensagem("assistant", "de novo essa", produtos=[produto_id])

    sugeridos = services.memoria_da_conversa()["ja_sugeridos"]
    assert sugeridos.count("Air Fryer 4L Digital") == 1


def test_mensagem_do_cliente_nao_conta_como_sugestao():
    produto_id = id_por_nome("Air Fryer 4L Digital")
    repositories.inserir_mensagem("user", "quero essa", produtos=[produto_id])
    assert "ja_sugeridos" not in services.memoria_da_conversa()


def test_lista_de_sugeridos_tem_teto():
    """Recitar a conversa inteira custaria token em toda rodada."""
    for nome in ("Air Fryer 4L Digital", "Notebook Titan X15"):
        repositories.inserir_mensagem("assistant", "olha", produtos=[id_por_nome(nome)])

    assert len(repositories.produtos_ja_citados(limite=1)) == 1


def test_conversa_sem_produto_nao_inventa_lista():
    repositories.inserir_mensagem("assistant", "oi, tudo bem?")
    assert "ja_sugeridos" not in services.memoria_da_conversa()


# --- Entrada no prompt ------------------------------------------------------

def test_prompt_carrega_o_que_foi_anotado():
    services.anotar_da_conversa("orcamento", "até 2 mil")
    services.anotar_da_conversa("recusou", "não quer o ProSound")

    prompt = chat._instrucoes(["quero um fone"])
    assert "até 2 mil" in prompt
    assert "não quer o ProSound" in prompt


def test_prompt_usa_rotulo_legivel_e_nao_nome_de_coluna():
    services.anotar_da_conversa("proposito", "presente pro filho de 6 anos")
    prompt = chat._instrucoes(["oi"])
    assert models.ROTULOS_MEMORIA["proposito"] in prompt


def test_conversa_sem_memoria_nao_gasta_token():
    """Mesma regra do tom neutro: não existe instrução pra dizer que não se
    sabe nada. Bloco vazio seria custo fixo em toda rodada de tool calling."""
    prompt = chat._instrucoes(["quero um fone"])
    assert "Esta compra, até aqui" not in prompt


def test_memoria_sobrevive_ao_corte_da_janela():
    """O ponto da funcionalidade: o que saiu da janela continua no prompt."""
    services.anotar_da_conversa("orcamento", "até 2 mil")
    for i in range(config.MAX_MENSAGENS_CONTEXTO * 2):
        repositories.inserir_mensagem("user", f"mensagem {i}")

    janela = repositories.listar_mensagens(limite=config.MAX_MENSAGENS_CONTEXTO)
    assert all("2 mil" not in m["content"] for m in janela)
    assert "até 2 mil" in chat._instrucoes(["e aí?"])
