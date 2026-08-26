"""Testes da leitura de imagem.

Nenhum chama o modelo de visão de verdade: o objetivo é a mecânica (limpeza
do raciocínio, limites, o que vai parar na conversa), não a qualidade da
descrição, que só o modelo real demonstra.
"""

from unittest.mock import MagicMock, patch

import pytest

from app import config
from app.ai import visao


def _resposta(conteudo):
    completion = MagicMock()
    completion.choices = [MagicMock(message=MagicMock(content=conteudo))]
    return completion


def _com_modelo(conteudo):
    client = MagicMock()
    client.chat.completions.create.return_value = _resposta(conteudo)
    return patch("app.ai.visao.get_client", return_value=client), client


def test_remove_o_bloco_de_raciocinio():
    """O modelo pensa antes de responder e entrega o pensamento junto. Isso
    não pode chegar ao cliente."""
    ctx, _ = _com_modelo("<think>vejo formas brancas\ne uma porta</think>\nUma geladeira branca.")
    with ctx:
        assert visao.descrever(b"imagem") == "Uma geladeira branca."


def test_resposta_sem_raciocinio_passa_intacta():
    ctx, _ = _com_modelo("Um notebook prateado.")
    with ctx:
        assert visao.descrever(b"imagem") == "Um notebook prateado."


def test_imagem_vazia_e_recusada():
    with pytest.raises(visao.ImagemNaoLida):
        visao.descrever(b"")


def test_imagem_grande_demais_e_recusada():
    grande = b"x" * (config.TAMANHO_MAXIMO_IMAGEM + 1)
    with pytest.raises(visao.ImagemNaoLida, match="MB"):
        visao.descrever(grande)


def test_resposta_so_com_raciocinio_vira_erro():
    """Sem espaço pra concluir, ele devolve só o pensamento. Melhor avisar do
    que mandar string vazia pra conversa."""
    ctx, _ = _com_modelo("<think>ainda pensando...</think>")
    with ctx, pytest.raises(visao.ImagemNaoLida):
        visao.descrever(b"imagem")


def test_falha_do_modelo_vira_erro_de_dominio():
    client = MagicMock()
    client.chat.completions.create.side_effect = RuntimeError("rede caiu")
    with patch("app.ai.visao.get_client", return_value=client):
        with pytest.raises(visao.ImagemNaoLida):
            visao.descrever(b"imagem")


def test_manda_a_imagem_no_formato_que_a_api_espera():
    ctx, client = _com_modelo("Uma tv.")
    with ctx:
        visao.descrever(b"abc", mime="image/png")

    enviado = client.chat.completions.create.call_args.kwargs
    conteudo = enviado["messages"][0]["content"]
    assert enviado["model"] == config.GROQ_MODEL_VISAO
    assert conteudo[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_reconhecimento_negativo():
    assert visao.reconheceu_produto("Uma geladeira branca.") is True
    assert visao.reconheceu_produto("Nenhum produto reconhecível.") is False


def test_tenta_de_novo_quando_a_resposta_vem_vazia():
    """O modelo às vezes gasta todo o espaço raciocinando e devolve conteúdo
    vazio. É intermitente, então recusar a foto de primeira seria injusto."""
    client = MagicMock()
    client.chat.completions.create.side_effect = [_resposta(""), _resposta("Uma tv.")]
    with patch("app.ai.visao.get_client", return_value=client):
        assert visao.descrever(b"imagem") == "Uma tv."
    assert client.chat.completions.create.call_count == 2


def test_desiste_depois_das_tentativas():
    client = MagicMock()
    client.chat.completions.create.return_value = _resposta("")
    with patch("app.ai.visao.get_client", return_value=client):
        with pytest.raises(visao.ImagemNaoLida):
            visao.descrever(b"imagem", tentativas=2)
    assert client.chat.completions.create.call_count == 2


def test_raciocinio_com_tag_aberta_nao_vaza():
    """Sem espaço pra fechar a tag, um filtro de bloco completo deixaria o
    pensamento inteiro aparecer pro cliente."""
    ctx, _ = _com_modelo("<think>a imagem mostra um retangulo e")
    with ctx, pytest.raises(visao.ImagemNaoLida):
        visao.descrever(b"imagem")


def test_pede_pra_groq_esconder_o_raciocinio():
    ctx, client = _com_modelo("Uma geladeira.")
    with ctx:
        visao.descrever(b"abc")
    assert client.chat.completions.create.call_args.kwargs["reasoning_format"] == "hidden"
