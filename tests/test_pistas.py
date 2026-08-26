"""Leitura do que o cliente revelou, sem depender do modelo anotar.

A regra que governa tudo aqui: **não achar nada é aceitável, achar errado
não é.** Orçamento inventado faz a Lu esconder produto que o cliente podia
comprar, e recusa inventada faz ela deixar de oferecer o que ele queria.
Por isso quase todo teste abaixo é de falso positivo.
"""

from app import pistas, repositories, services, sessao
from tests.conftest import id_por_nome


# --- Orçamento --------------------------------------------------------------

def test_le_valor_em_mil():
    assert pistas.orcamento(["meu limite eh 2 mil"]) == "até R$ 2.000"


def test_le_valor_com_cifrao():
    assert pistas.orcamento(["posso gastar R$ 1.500"]) == "até R$ 1.500"


def test_le_valor_em_reais_escrito():
    assert pistas.orcamento(["quero gastar no maximo 800 reais"]) == "até R$ 800"


def test_le_giria_de_dinheiro():
    assert pistas.orcamento(["tenho so 300 conto pra gastar"]) == "até R$ 300"


def test_le_com_acento_e_sem_acento():
    assert pistas.orcamento(["meu orçamento é até 2 mil"]) == "até R$ 2.000"
    assert pistas.orcamento(["meu orcamento eh ate 2 mil"]) == "até R$ 2.000"


def test_valor_mais_recente_vence():
    """O cliente muda de ideia, e o teto novo é o que vale."""
    falas = ["meu limite eh 2 mil", "na verdade posso gastar ate 3 mil"]
    assert pistas.orcamento(falas) == "até R$ 3.000"


def test_numero_sem_contexto_de_limite_nao_e_orcamento():
    """"Gastei 2 mil no último" é história, não teto de compra."""
    assert pistas.orcamento(["gastei 2 mil no meu ultimo notebook"]) is None


def test_numero_de_produto_nao_vira_orcamento():
    assert pistas.orcamento(["quero uma tv de 55 polegadas"]) is None
    assert pistas.orcamento(["procuro notebook com 16gb de ram"]) is None


def test_conversa_sem_numero_nao_inventa():
    assert pistas.orcamento(["quero um fone bom", "pra academia"]) is None


def test_limite_sem_valor_nao_inventa():
    """"Não quero gastar muito" não tem número, e chutar seria pior."""
    assert pistas.orcamento(["nao quero gastar muito"]) is None


# --- Recusas ----------------------------------------------------------------

def _produto(nome):
    return next(p for p in repositories.listar_produtos() if p["nome"] == nome)


def _universo():
    """Nomes do catálogo inteiro, que é o que mede se a palavra é específica."""
    return [p["nome"] for p in repositories.listar_produtos()]


def test_le_recusa_de_produto_ja_mostrado():
    mostrados = [_produto("Notebook Chromebook 11")]
    assert pistas.recusas(["nao gostei do chromebook"], mostrados, _universo()) == [
        "Notebook Chromebook 11"
    ]


def test_recusa_so_vale_pro_que_ja_foi_mostrado():
    """Sem candidato, não há o que recusar, e casar contra o catálogo inteiro
    traria produto que nunca esteve na conversa."""
    assert pistas.recusas(["nao gostei do chromebook"], [], _universo()) == []


def test_palavra_generica_nao_conta_como_recusa():
    """"Não quero notebook" é categoria, não um modelo. Sem esse filtro, um
    produto qualquer da categoria seria dado como descartado."""
    mostrados = [_produto("Notebook Titan X15"), _produto("Notebook Essencial 14")]
    assert pistas.recusas(["nao quero notebook"], mostrados, _universo()) == []


def test_elogio_nao_e_recusa():
    mostrados = [_produto("Notebook Chromebook 11")]
    assert pistas.recusas(["gostei do chromebook"], mostrados, _universo()) == []


def test_menciona_sem_negar_nao_e_recusa():
    mostrados = [_produto("Notebook Chromebook 11")]
    assert pistas.recusas(["me fala mais do chromebook"], mostrados, _universo()) == []


def test_nega_sem_citar_produto_nao_recusa_nada():
    mostrados = [_produto("Notebook Chromebook 11")]
    assert pistas.recusas(["nao gostei"], mostrados, _universo()) == []


# --- Integrado com a memória ------------------------------------------------

def test_orcamento_lido_entra_na_memoria_sem_ferramenta():
    """O ponto da existência deste módulo: o modelo não chamou nada, e o
    orçamento aparece do mesmo jeito."""
    repositories.inserir_mensagem("user", "meu limite eh 2 mil, quero um notebook")
    assert services.memoria_da_conversa()["orcamento"] == "até R$ 2.000"


def test_leitura_vence_anotacao_velha():
    """O modelo anota quando lembra, e não reanota quando o cliente muda de
    ideia. A fala mais recente tem que ganhar."""
    services.anotar_da_conversa("orcamento", "até 2 mil")
    repositories.inserir_mensagem("user", "consigo esticar ate 4 mil")
    assert services.memoria_da_conversa()["orcamento"] == "até R$ 4.000"


def test_recusa_lida_soma_com_a_anotada():
    """A leitura pega nome de produto; o modelo pega marca e categoria ("nada
    da Samsung"), que não casa com nome nenhum. Os dois entram."""
    produto_id = id_por_nome("Notebook Chromebook 11")
    repositories.inserir_mensagem("assistant", "olha esse", produtos=[produto_id])
    services.anotar_da_conversa("recusou", "nada da Samsung")
    repositories.inserir_mensagem("user", "nao quero o chromebook")

    recusou = services.memoria_da_conversa()["recusou"]
    assert "Samsung" in recusou
    assert "Chromebook" in recusou
