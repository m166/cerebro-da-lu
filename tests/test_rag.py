"""Testes do RAG.

Rodam com o encoder falso da fixture `rag_sem_download` — verificam a
mecânica (índice, ranking, corte por score, filtro de categoria), não a
qualidade semântica, que depende do modelo real.
"""

from app import config, services, vectorstore
from app.data import conhecimento


# --- Base de conhecimento -------------------------------------------------

def test_base_tem_documentos():
    assert len(conhecimento.DOCUMENTOS) >= 30


def test_ids_unicos_e_sequenciais():
    ids = [d["id"] for d in conhecimento.DOCUMENTOS]
    assert ids == list(range(1, len(ids) + 1))


def test_documentos_tem_titulo_e_texto():
    for documento in conhecimento.DOCUMENTOS:
        assert documento["titulo"].strip()
        assert len(documento["texto"]) > 100


def test_todo_documento_tem_perguntas():
    """As perguntas fazem a ponte entre o vocabulário de especificação do
    corpo e o de sintoma que o cliente usa — sem elas o acerto@1 cai."""
    for documento in conhecimento.DOCUMENTOS:
        assert len(documento["perguntas"]) >= 3, documento["titulo"]


def test_texto_indexavel_inclui_as_perguntas():
    documento = conhecimento.DOCUMENTOS[0]
    indexavel = conhecimento.texto_indexavel(documento)
    for pergunta in documento["perguntas"]:
        assert pergunta in indexavel


def test_categorias_do_conhecimento_existem_no_catalogo():
    """Categoria vazia é permitida (assunto geral), mas se tiver categoria
    ela precisa casar com o catálogo, senão o filtro nunca acha nada."""
    from app.data import catalogo

    for documento in conhecimento.DOCUMENTOS:
        if documento["categoria"]:
            assert documento["categoria"] in catalogo.CATEGORIAS, documento["titulo"]


def test_texto_indexavel_junta_titulo_e_corpo():
    documento = conhecimento.DOCUMENTOS[0]
    indexavel = conhecimento.texto_indexavel(documento)
    assert documento["titulo"] in indexavel
    assert documento["texto"] in indexavel


def test_perguntas_do_doc_nao_copiam_os_casos_do_eval():
    """Se a pergunta indexada for a mesma do caso de avaliação, a métrica
    mede memorização em vez de generalização.

    A comparação ignora palavras estruturais: "qual a diferença de OLED pra
    QLED" e "qual a diferença de SSD pra HD" compartilham a forma da frase,
    não o assunto — isso não é contaminação.
    """
    import re
    import unicodedata

    from evals import casos

    def termos(texto: str) -> set:
        texto = unicodedata.normalize("NFKD", texto.lower())
        texto = "".join(c for c in texto if not unicodedata.combining(c))
        return set(re.findall(r"[a-z0-9]+", texto))

    estruturais = termos(
        "o a os as de do da em pra para por que qual quais e eh um uma no na com "
        "meu minha eu quero preciso tem ter vale pena mais menos muito ou se"
    )

    indexadas = [
        termos(p) - estruturais for d in conhecimento.DOCUMENTOS for p in d["perguntas"]
    ]
    for pergunta, _ in casos.RETRIEVAL:
        do_caso = termos(pergunta) - estruturais
        for da_base in indexadas:
            if not do_caso or not da_base:
                continue
            sobreposicao = len(do_caso & da_base) / len(do_caso | da_base)
            assert sobreposicao < 0.5, (
                f"caso de avaliação quase idêntico a pergunta indexada: {pergunta!r}"
            )


# --- Vectorstore -------------------------------------------------------------

def test_busca_devolve_k_resultados():
    resultados = vectorstore.buscar("quanta memoria RAM", k=3)
    assert len(resultados) == 3


def test_busca_ordena_por_score_decrescente():
    resultados = vectorstore.buscar("geladeira litros familia", k=5)
    scores = [r["score"] for r in resultados]
    assert scores == sorted(scores, reverse=True)


def test_documento_e_o_primeiro_resultado_do_proprio_texto():
    """Propriedade válida pra qualquer encoder: perguntando com o texto
    exato de um documento, ele tem que vir em primeiro.

    Não dá pra afirmar mais que isso aqui — julgar se 'meu quarto tem 12m2'
    traz o documento de BTUs mede a qualidade semântica do modelo real, que
    esta suíte não carrega de propósito.
    """
    esperado = conhecimento.DOCUMENTOS[10]
    resultados = vectorstore.buscar(conhecimento.texto_indexavel(esperado), k=1)
    assert resultados[0]["id"] == esperado["id"]


def test_busca_filtra_por_categoria():
    resultados = vectorstore.buscar("qual escolher", k=10, categoria="colchoes")
    assert resultados
    assert all(r["categoria"] == "colchoes" for r in resultados)


def test_busca_vazia_nao_quebra():
    assert vectorstore.buscar("", k=3) == []
    assert vectorstore.buscar("   ", k=3) == []


def test_indice_e_reaproveitado_entre_buscas():
    """O índice é caro de montar; deve ser construído uma vez só."""
    from tests.conftest import _encoder_falso

    chamadas = []

    def encoder_contador(textos):
        chamadas.append(len(textos))
        return _encoder_falso(textos)

    vectorstore.definir_encoder(encoder_contador)
    vectorstore.buscar("primeira pergunta", k=1)
    vectorstore.buscar("segunda pergunta", k=1)

    # 1 chamada pra indexar todos os documentos + 1 por pergunta
    assert chamadas[0] == len(conhecimento.DOCUMENTOS)
    assert chamadas[1:] == [1, 1]


def test_definir_encoder_invalida_indice():
    vectorstore.buscar("aquece", k=1)
    assert vectorstore._indice is not None

    vectorstore.definir_encoder(None)
    assert vectorstore._indice is None


# --- Service ---------------------------------------------------------------

def test_service_devolve_trechos_formatados():
    resultado = services.buscar_conhecimento("quantos BTUs preciso")
    assert resultado["encontrou"] is True
    assert resultado["pergunta"] == "quantos BTUs preciso"
    for trecho in resultado["trechos"]:
        assert set(trecho) == {"titulo", "categoria", "texto", "score"}


def test_service_respeita_limite_padrao():
    resultado = services.buscar_conhecimento("geladeira")
    assert len(resultado["trechos"]) <= config.LIMITE_CONHECIMENTO


def test_service_corta_resultado_irrelevante(monkeypatch):
    """Cortes altos demais devem zerar os resultados — é o mecanismo que faz
    a Lu admitir que não sabe em vez de inventar."""
    monkeypatch.setattr(config, "SCORE_MINIMO_CONHECIMENTO", 0.99)
    monkeypatch.setattr(config, "SCORE_LEXICAL_MINIMO", 10_000.0)
    resultado = services.buscar_conhecimento("qualquer pergunta obscura")
    assert resultado["encontrou"] is False
    assert resultado["trechos"] == []


def test_basta_o_sinal_semantico(monkeypatch):
    """Os sinais falham em casos opostos — pergunta que descreve sintoma tem
    cosseno baixo e léxico alto, pergunta curta e direta é o contrário —,
    então passar em um só já aceita o trecho."""
    monkeypatch.setattr(config, "SCORE_MINIMO_CONHECIMENTO", 0.0)
    monkeypatch.setattr(config, "SCORE_LEXICAL_MINIMO", 10_000.0)
    assert services.buscar_conhecimento("geladeira")["encontrou"] is True


def test_basta_o_sinal_lexical(monkeypatch):
    monkeypatch.setattr(config, "SCORE_MINIMO_CONHECIMENTO", 2.0)
    monkeypatch.setattr(config, "SCORE_LEXICAL_MINIMO", 0.0)
    assert services.buscar_conhecimento("geladeira")["encontrou"] is True


def test_busca_devolve_os_dois_sinais():
    for documento in vectorstore.buscar("geladeira", k=2):
        assert "score" in documento
        assert "score_lexical" in documento


def test_service_filtra_por_categoria():
    resultado = services.buscar_conhecimento("como escolher", categoria="bicicletas")
    assert all(t["categoria"] == "bicicletas" for t in resultado["trechos"])
