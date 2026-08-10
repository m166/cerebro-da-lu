from app.bm25 import IndiceBM25, tokenizar


def test_tokenizar_remove_acento_e_caixa():
    assert tokenizar("Ar-Condicionado INVERTER") == ["ar", "condicionado", "inverter"]


def test_tokenizar_descarta_palavras_funcionais():
    """Sem isso, pergunta fora do domínio pontua só por 'de', 'que', 'para'."""
    assert tokenizar("o que é isso para mim") == []


def test_tokenizar_descarta_token_de_uma_letra():
    assert "a" not in tokenizar("a b geladeira")


def test_pontua_documento_que_contem_o_termo():
    indice = IndiceBM25(["geladeira frost free", "teclado mecanico"])
    scores = indice.pontuar("geladeira")
    assert scores[0] > 0
    assert scores[1] == 0


def test_termo_raro_pesa_mais_que_termo_comum():
    """É o que faz 'inverter' valer mais que 'aparelho' na busca."""
    indice = IndiceBM25(
        [
            "aparelho inverter economico",
            "aparelho comum",
            "aparelho velho",
            "aparelho novo",
        ]
    )
    raro = indice.pontuar("inverter")[0]
    comum = indice.pontuar("aparelho")[0]
    assert raro > comum


def test_pergunta_sem_termo_em_comum_zera():
    indice = IndiceBM25(["geladeira frost free", "teclado mecanico"])
    assert indice.pontuar("capital da franca") == [0.0, 0.0]


def test_indice_vazio_nao_quebra():
    assert IndiceBM25([]).pontuar("qualquer coisa") == []


def test_documento_vazio_nao_quebra():
    indice = IndiceBM25(["", "geladeira"])
    assert indice.pontuar("geladeira")[1] > 0
