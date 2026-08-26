"""Satisfação declarada, sinais observados e o diagnóstico que sai deles.

O sistema não se conserta sozinho, e isso é escolha registrada: ele mede,
aponta e sugere, e a mudança passa por uma pessoa. Mudança automática de
comportamento precisaria de uma régua rodando continuamente, e a deste
projeto (`evals/`) roda sob demanda. Esta suíte cobre a medição e o
diagnóstico, não uma adaptação automática que de propósito não existe.
"""

import pytest

from app import config, exceptions, models, repositories, services
from tests.conftest import id_por_nome


# --- Satisfação -------------------------------------------------------------

def test_registra_nota_e_comentario():
    services.registrar_satisfacao(5, "me ajudou demais", "escolha de notebook")
    resumo = repositories.resumo_da_satisfacao()
    assert resumo["respostas"] == 1
    assert resumo["media"] == 5.0


def test_nota_fora_da_escala_e_recusada():
    for nota in (0, 6, -1):
        with pytest.raises(exceptions.NotaInvalida):
            services.registrar_satisfacao(nota)


def test_separa_satisfeitos_de_insatisfeitos():
    for nota in (1, 2, 4, 5, 5):
        services.registrar_satisfacao(nota)
    resumo = repositories.resumo_da_satisfacao()
    assert resumo["insatisfeitos"] == 2
    assert resumo["satisfeitos"] == 3


def test_reclamacoes_trazem_o_comentario():
    """A nota diz que foi ruim; o comentário diz o que consertar."""
    services.registrar_satisfacao(1, "não achou o que eu queria", "busca")
    services.registrar_satisfacao(5, "ótima")

    baixas = repositories.notas_baixas()
    assert len(baixas) == 1
    assert baixas[0]["comentario"] == "não achou o que eu queria"


# --- O sinal mais valioso: o que a base não sabe ----------------------------

def test_pergunta_sem_resposta_do_rag_vira_evento(monkeypatch):
    """É a fila de trabalho pra escrever documento novo, priorizada por
    demanda real em vez de palpite de quem edita o corpus."""
    monkeypatch.setattr(config, "SCORE_MINIMO_CONHECIMENTO", 2.0)
    monkeypatch.setattr(config, "SCORE_LEXICAL_MINIMO", 999.0)

    services.buscar_conhecimento("como funciona o consórcio de imóvel?")

    perguntas = repositories.perguntas_sem_resposta()
    assert perguntas[0]["pergunta"] == "como funciona o consórcio de imóvel?"
    assert perguntas[0]["vezes"] == 1


def test_pergunta_repetida_sobe_na_fila(monkeypatch):
    monkeypatch.setattr(config, "SCORE_MINIMO_CONHECIMENTO", 2.0)
    monkeypatch.setattr(config, "SCORE_LEXICAL_MINIMO", 999.0)

    for _ in range(3):
        services.buscar_conhecimento("vocês têm consórcio?")
    services.buscar_conhecimento("aceitam pix parcelado?")

    perguntas = repositories.perguntas_sem_resposta()
    assert perguntas[0]["pergunta"] == "vocês têm consórcio?"
    assert perguntas[0]["vezes"] == 3


def test_busca_bem_sucedida_nao_gera_evento():
    """Só o buraco interessa. Registrar acerto encheria a tabela de ruído."""
    services.buscar_conhecimento("quanta memória RAM um notebook precisa")
    assert repositories.perguntas_sem_resposta() == []


def test_telemetria_nao_derruba_atendimento(monkeypatch):
    """Se o registro falhar, o cliente ainda recebe a resposta dele."""
    def explode(*a, **k):
        raise RuntimeError("banco fora")

    monkeypatch.setattr(repositories, "get_connection", explode)
    repositories.registrar_evento(models.EVENTO_RAG_SEM_RESPOSTA, {"pergunta": "x"})


# --- Diagnóstico ------------------------------------------------------------

def test_diagnostico_prioriza_o_que_mais_gente_perguntou(monkeypatch):
    monkeypatch.setattr(config, "SCORE_MINIMO_CONHECIMENTO", 2.0)
    monkeypatch.setattr(config, "SCORE_LEXICAL_MINIMO", 999.0)
    for _ in range(4):
        services.buscar_conhecimento("vocês instalam ar condicionado?")

    relatorio = services.diagnostico()
    acao = relatorio["acoes_sugeridas"][0]
    assert acao["onde"] == "base de conhecimento"
    assert acao["prioridade"] == "alta"
    assert "instalam ar condicionado" in acao["o_que_fazer"]


def test_diagnostico_aponta_insatisfacao():
    services.registrar_satisfacao(1, "demorou demais")
    acoes = services.diagnostico()["acoes_sugeridas"]
    assert any(a["onde"] == "atendimento" for a in acoes)


def test_diagnostico_de_sistema_saudavel_nao_inventa_problema():
    relatorio = services.diagnostico()
    assert relatorio["acoes_sugeridas"] == []
    assert relatorio["perguntas_sem_resposta"] == []


def test_diagnostico_mede_conversao_do_cupom():
    """Cupom que não converte é margem queimada, e precisa aparecer."""
    for _ in range(5):
        repositories.registrar_evento(models.EVENTO_CUPOM_OFERECIDO, {"valor": 50})

    relatorio = services.diagnostico()
    assert relatorio["cupons"]["oferecidos"] == 5
    assert relatorio["cupons"]["usados"] == 0
    assert any(a["onde"] == "cupom" for a in relatorio["acoes_sugeridas"])


def test_diagnostico_nao_altera_nada_sozinho():
    """A garantia de que ele só aponta. Se algum dia ele passar a corrigir,
    este teste falha e obriga a decisão a ser consciente."""
    antes = config.PERCENTUAL_MAXIMO_DA_MARGEM
    services.registrar_satisfacao(1, "ruim")
    services.diagnostico()
    assert config.PERCENTUAL_MAXIMO_DA_MARGEM == antes
