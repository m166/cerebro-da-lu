"""Leitura do 429 da Groq.

As mensagens aqui são as que a API devolveu de verdade, copiadas na íntegra:
foi assim que apareceu que o teto batido era o do dia, e não o do minuto que
o código supunha.
"""

from unittest.mock import MagicMock

import pytest
from groq import RateLimitError

from app.ai import chat
from app.ai.client import POR_DIA, POR_MINUTO, janela_do_limite, segundos_de_espera

# Capturada da API, com o id da organização trocado por um fictício:
# o formato é o que importa aqui, e identificador de conta não vai pro
# repositório. O prazo vem em "22m2.784s", formato que a primeira versão
# do parser não entendia: ela só lia segundos e devolvia None.
TETO_DO_DIA = (
    "Rate limit reached for model `openai/gpt-oss-120b` in organization "
    "`org_EXEMPLO0000000000000000000` service tier `on_demand` on tokens per "
    "day (TPD): Limit 200000, Used 199743, Requested 3319. Please try again "
    "in 22m2.784s. Need more tokens? Upgrade to Dev Tier today at "
    "https://console.groq.com/settings/billing"
)

TETO_DO_MINUTO = (
    "Rate limit reached for model `openai/gpt-oss-120b` on tokens per minute "
    "(TPM): Limit 8000, Used 7600, Requested 900. Please try again in 3.2s."
)


def _erro(mensagem):
    corpo = {"error": {"message": mensagem, "type": "tokens", "code": "rate_limit_exceeded"}}
    return RateLimitError(
        f"Error code: 429 - {corpo}",
        response=MagicMock(status_code=429, headers={}),
        body=corpo,
    )


# --- Quanto esperar ---------------------------------------------------------

@pytest.mark.parametrize(
    "prazo,segundos",
    [
        ("800ms", 0.8),
        ("4.5s", 4.5),
        ("22m2.784s", 1322.784),
        ("1h2m3s", 3723.0),
        ("2m", 120.0),
    ],
)
def test_entende_os_formatos_de_prazo(prazo, segundos):
    erro = _erro(f"Rate limit reached. Please try again in {prazo}.")
    assert segundos_de_espera(erro) == pytest.approx(segundos)


def test_800ms_nao_vira_800_minutos():
    """"ms" tem que casar antes de "m", senão a espera fica 800x maior."""
    assert segundos_de_espera(_erro("try again in 800ms")) < 1


def test_sem_prazo_nenhum_devolve_none():
    assert segundos_de_espera(_erro("Rate limit reached.")) is None


# --- Qual teto foi batido ---------------------------------------------------

def test_reconhece_o_teto_do_dia():
    assert janela_do_limite(_erro(TETO_DO_DIA)) == POR_DIA


def test_reconhece_o_teto_do_minuto():
    assert janela_do_limite(_erro(TETO_DO_MINUTO)) == POR_MINUTO


def test_teto_desconhecido_nao_chuta():
    assert janela_do_limite(_erro("Rate limit reached.")) is None


# --- O que o cliente lê -----------------------------------------------------

def test_aviso_do_dia_nao_diz_por_minuto():
    """A versão anterior dizia "por minuto" sempre, e quem lia esperava um
    minuto e batia no mesmo erro sem entender."""
    aviso = chat._aviso_de_limite(_erro(TETO_DO_DIA), segundos_de_espera(_erro(TETO_DO_DIA)))

    assert "do dia" in aviso
    assert "por minuto" not in aviso
    assert "23 min" in aviso


def test_aviso_do_minuto_diz_por_minuto():
    erro = _erro(TETO_DO_MINUTO)
    aviso = chat._aviso_de_limite(erro, segundos_de_espera(erro))

    assert "por minuto" in aviso
    assert "4s" in aviso


@pytest.mark.parametrize(
    "segundos,esperado",
    [(45, "45s"), (90, "2 min"), (1322.784, "23 min"), (7200, "2h")],
)
def test_prazo_legivel(segundos, esperado):
    assert chat._quanto_falta(segundos) == esperado


# --- Não insistir no que não adianta ---------------------------------------

def test_nao_espera_pelo_teto_do_dia(groq_falso, monkeypatch):
    """Dormir 22 minutos dentro de uma requisição HTTP prenderia o cliente."""
    dormiu = []
    monkeypatch.setattr("app.ai.chat.time.sleep", dormiu.append)
    groq = groq_falso(_erro(TETO_DO_DIA))

    with pytest.raises(chat.LimiteDeUso):
        chat.responder("oi")

    assert dormiu == []
    assert groq.chat.completions.create.call_count == 1
