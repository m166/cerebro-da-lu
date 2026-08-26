import pytest

from app import registro


# --- Detecção ---------------------------------------------------------------

@pytest.mark.parametrize(
    "mensagem",
    [
        "eae lu, blz?",
        "mano to precisando de um fone bom e barato",
        "salve! qual o mais barato ai",
        "kkkkk esse ai é caro demais",
        "vlw, tmj",
        "pq esse ta mais caro que o outro?",
    ],
)
def test_cliente_solto(mensagem):
    assert registro.detectar([mensagem]) == registro.INFORMAL


@pytest.mark.parametrize(
    "mensagem",
    [
        "Boa tarde. Gostaria de saber o prazo de entrega.",
        "Prezados, solicito informações sobre a garantia.",
        "Poderia verificar a disponibilidade deste produto, por gentileza?",
        "Agradeço o retorno.",
    ],
)
def test_cliente_formal(mensagem):
    assert registro.detectar([mensagem]) == registro.FORMAL


@pytest.mark.parametrize(
    "mensagem",
    ["quanto custa?", "quero um notebook", "oi", ""],
)
def test_sem_marcador_nenhum_e_neutro(mensagem):
    assert registro.detectar([mensagem]) == registro.NEUTRO


def test_sem_mensagem_nenhuma_e_neutro():
    """Primeira mensagem da conversa: não há tom pra ler ainda."""
    assert registro.detectar([]) == registro.NEUTRO


def test_mensagem_muda_nao_zera_o_tom_ja_estabelecido():
    """"Quanto custa?" não tem marcador, mas a conversa continua solta: sem
    olhar pra trás a Lu voltaria a ser neutra no meio do papo."""
    assert registro.detectar(["eae blz mano", "quanto custa?"]) == registro.INFORMAL
    assert (
        registro.detectar(["Prezados, boa tarde.", "quanto custa?"]) == registro.FORMAL
    )


def test_a_mensagem_mais_recente_manda():
    """Cliente que começa formal e relaxa (ou o contrário) é acompanhado."""
    assert registro.detectar(["Boa tarde, gostaria de saber", "blz mano, vlw"]) == (
        registro.INFORMAL
    )
    assert registro.detectar(["eae blz", "Agradeço, poderia confirmar?"]) == (
        registro.FORMAL
    )


def test_acento_nao_atrapalha():
    assert registro.detectar(["vc é rápido, né"]) == registro.INFORMAL


# --- Instrução que entra no prompt -----------------------------------------

def test_neutro_nao_gasta_token_no_prompt():
    """A persona já é neutra por padrão: dizer isso de novo é token à toa."""
    assert registro.instrucao(registro.NEUTRO) is None


def test_informal_e_formal_geram_instrucao():
    assert "gíria" in registro.instrucao(registro.INFORMAL)
    assert "formal" in registro.instrucao(registro.FORMAL)


# --- Cumprimento puro -------------------------------------------------------

@pytest.mark.parametrize(
    "mensagem",
    ["oi", "Oi!", "bom dia", "boa tarde", "oi, tudo bem?", "eae", "salve",
     "opa, blz?", "ola, tudo bem", "e ai, tudo joia?"],
)
def test_reconhece_cumprimento_puro(mensagem):
    assert registro.so_cumprimentou(mensagem) is True


@pytest.mark.parametrize(
    "mensagem",
    [
        "oi, tem air fryer?",
        "bom dia, gostaria de saber o prazo",
        "quero um notebook",
        "cade meu pedido",
        "",
        "oi tudo bem eu queria saber sobre a garantia do meu produto",
    ],
)
def test_pedido_junto_do_oi_nao_e_so_cumprimento(mensagem):
    """Errar pra mais faria a Lu se apresentar em vez de responder."""
    assert registro.so_cumprimentou(mensagem) is False


def test_a_instrucao_de_abertura_proibe_ferramenta():
    """Cumprimento não é consulta, e disparar tool aqui gasta rodada à toa."""
    assert "ferramenta" in registro.INSTRUCAO_ABERTURA
