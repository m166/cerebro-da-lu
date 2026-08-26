import pytest

from app import telefone


# --- Normalização -----------------------------------------------------------

@pytest.mark.parametrize(
    "digitado",
    [
        "11988881234",
        "(11) 98888-1234",
        "11 98888 1234",
        "+55 11 98888-1234",
        "5511988881234",
        " 55 (11) 9 8888-1234 ",
    ],
)
def test_formas_de_digitar_o_mesmo_numero_caem_na_mesma_sessao(digitado):
    """É o ponto do módulo: o cliente digita de qualquer jeito e a conversa
    é uma só. Sem isto, cada formatação viraria um cliente diferente."""
    assert telefone.normalizar(digitado) == "5511988881234"


def test_fixo_de_dez_digitos_tambem_vale():
    assert telefone.normalizar("(11) 3888-1234") == "551138881234"


@pytest.mark.parametrize(
    "digitado",
    ["", "123", "988881234", "abcdefghijk", "0011988881234", "1198888123456789"],
)
def test_o_que_nao_e_telefone_e_recusado(digitado):
    with pytest.raises(telefone.TelefoneInvalido):
        telefone.normalizar(digitado)


@pytest.mark.parametrize("ddd", ["01", "10", "00"])
def test_ddd_inexistente_e_recusado(ddd):
    with pytest.raises(telefone.TelefoneInvalido):
        telefone.normalizar(f"{ddd}988881234")


def test_valido_nao_levanta():
    assert telefone.valido("11988881234") is True
    assert telefone.valido("nada disso") is False


# --- Formatação -------------------------------------------------------------

def test_formatar_celular():
    assert telefone.formatar("5511988881234") == "+55 11 98888-1234"


def test_formatar_fixo():
    assert telefone.formatar("551138881234") == "+55 11 3888-1234"


def test_formatar_devolve_como_veio_o_que_nao_reconhece():
    """A tela e o prompt chamam isto com o que veio do banco. Uma linha
    estranha deve aparecer como está, não derrubar a requisição."""
    assert telefone.formatar("local") == "local"
    assert telefone.formatar("") == ""
