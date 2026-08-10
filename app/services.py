"""Regras de negócio.

Os services validam, calculam e orquestram os repositories. Quando algo
não faz sentido no domínio, levantam uma exceção de `app.exceptions`, quem
chama decide como apresentar (HTTP ou mensagem pro modelo).
"""

from datetime import date, datetime, timedelta
from typing import Callable, List, Optional

from app import config, exceptions, models, repositories


# --- Catálogo -------------------------------------------------------------

def buscar_produtos(query: str = "", categoria: str = "", limite: Optional[int] = None) -> List[dict]:
    return repositories.listar_produtos(query=query, categoria=categoria, limite=limite)


def obter_produto(produto_id: int) -> dict:
    produto = repositories.obter_produto(produto_id)
    if produto is None:
        raise exceptions.ProdutoNaoEncontrado(produto_id)
    return produto


def listar_categorias() -> List[str]:
    return repositories.listar_categorias()


def consultar_estoque(produto_id: int) -> dict:
    produto = obter_produto(produto_id)
    return {
        "produto_id": produto_id,
        "nome": produto["nome"],
        "estoque": produto["estoque"],
        "disponivel": produto["estoque"] > 0,
    }


# --- Base de conhecimento (RAG) -------------------------------------------

def buscar_conhecimento(pergunta: str, categoria: str = "", limite: Optional[int] = None) -> dict:
    """Busca semântica na base de conhecimento sobre tecnologia.

    Descarta resultado com similaridade baixa: é melhor a Lu admitir que
    não sabe do que fundamentar a recomendação num trecho irrelevante.
    """
    encontrados = repositories.buscar_conhecimento(
        pergunta, k=limite or config.LIMITE_CONHECIMENTO, categoria=categoria
    )
    relevantes = [
        d
        for d in encontrados
        if d["score"] >= config.SCORE_MINIMO_CONHECIMENTO
        or d["score_lexical"] >= config.SCORE_LEXICAL_MINIMO
    ]

    return {
        "pergunta": pergunta,
        "encontrou": bool(relevantes),
        "trechos": [
            {
                "titulo": d["titulo"],
                "categoria": d["categoria"],
                "texto": d["texto"],
                "score": round(d["score"], 3),
            }
            for d in relevantes
        ],
    }


# --- Sugestão e comparação -------------------------------------------------

def _score_custo_beneficio(candidatos: List[dict]) -> Callable[[dict], float]:
    """Score normalizado dentro do conjunto avaliado.

    A normalização é relativa aos candidatos, comparar um mouse com um
    notebook não faria sentido, então o score só é significativo dentro de
    uma mesma categoria.
    """
    precos = [p["preco"] for p in candidatos]
    prazos = [p["prazo_entrega_dias"] for p in candidatos]
    min_preco, max_preco = min(precos), max(precos)
    min_prazo, max_prazo = min(prazos), max(prazos)

    def score(p: dict) -> float:
        preco_norm = 0.0 if max_preco == min_preco else (p["preco"] - min_preco) / (max_preco - min_preco)
        prazo_norm = 0.0 if max_prazo == min_prazo else (p["prazo_entrega_dias"] - min_prazo) / (max_prazo - min_prazo)
        avaliacao_norm = p["avaliacao"] / 5.0
        # preço e prazo menores são melhores, avaliação maior é melhor
        return (1 - preco_norm) * 0.4 + (1 - prazo_norm) * 0.2 + avaliacao_norm * 0.4

    return score


def _escolher(candidatos: List[dict], criterio: str) -> dict:
    if criterio == "melhor_preco":
        return min(candidatos, key=lambda p: p["preco"])
    if criterio == "melhor_prazo":
        return min(candidatos, key=lambda p: p["prazo_entrega_dias"])
    if criterio == "melhor_avaliacao":
        return max(candidatos, key=lambda p: p["avaliacao"])
    return max(candidatos, key=_score_custo_beneficio(candidatos))


def sugerir_produto(categoria: str = "", criterio: str = "melhor_custo_beneficio") -> dict:
    """Sugere o melhor produto de uma categoria (ou de todo o catálogo)."""
    candidatos = [p for p in repositories.listar_produtos(categoria=categoria) if p["estoque"] > 0]
    if not candidatos:
        raise exceptions.SemProdutosDisponiveis()

    return {"criterio": criterio, "produto": _escolher(candidatos, criterio)}


def comparar_produtos(categoria: str = "", produto_ids: Optional[List[int]] = None) -> dict:
    """Compara produtos lado a lado, apontando quem ganha em cada critério."""
    if produto_ids:
        candidatos = [p for p in (repositories.obter_produto(i) for i in produto_ids) if p is not None]
    else:
        candidatos = repositories.listar_produtos(categoria=categoria)

    if len(candidatos) < 2:
        raise exceptions.ComparacaoInvalida()

    return {
        "produtos": candidatos,
        "melhor_preco": _escolher(candidatos, "melhor_preco")["nome"],
        "melhor_prazo": _escolher(candidatos, "melhor_prazo")["nome"],
        "melhor_avaliacao": _escolher(candidatos, "melhor_avaliacao")["nome"],
        "melhor_custo_beneficio": _escolher(candidatos, "melhor_custo_beneficio")["nome"],
    }


# --- Rastreio: código e progressão de status ------------------------------

def _digito_verificador(serie: str) -> int:
    """DV de rastreio dos Correios: módulo 11 com pesos 8,6,4,2,3,5,9,7."""
    soma = sum(int(digito) * peso for digito, peso in zip(serie, models.PESOS_DV_RASTREIO))
    resto = soma % 11
    if resto == 0:
        return 5
    if resto == 1:
        return 0
    return 11 - resto


def gerar_codigo_rastreio(pedido_id: int) -> str:
    """Código no formato dos Correios, derivado do id do pedido.

    A série é mockada (o id preenchido com zeros), mas o dígito verificador
    é calculado de verdade, então o código passa em qualquer validador de
    formato. Determinístico de propósito: o mesmo pedido devolve sempre o
    mesmo código, mesmo em banco que ainda não tinha a coluna.
    """
    serie = f"{pedido_id:08d}"[-8:]
    return (
        f"{models.PREFIXO_RASTREIO}{serie}"
        f"{_digito_verificador(serie)}{models.SUFIXO_RASTREIO}"
    )


def _para_datetime(valor: Optional[str]) -> Optional[datetime]:
    """Lê o formato que o SQLite grava em CURRENT_TIMESTAMP (UTC)."""
    if not valor:
        return None
    texto = str(valor).strip().replace("T", " ").split(".")[0]
    for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, formato)
        except ValueError:
            continue
    return None


def _prazo_em_segundos(pedido: dict) -> float:
    produto = repositories.obter_produto(pedido.get("produto_id"))
    dias = produto["prazo_entrega_dias"] if produto else models.PRAZO_ENTREGA_PADRAO_DIAS
    return dias * config.SEGUNDOS_POR_DIA_ENTREGA


def status_derivado(pedido: dict, agora: Optional[datetime] = None) -> str:
    """Etapa em que o pedido está, calculada a partir do relógio.

    Não existe job avançando status no banco: a etapa é uma função do tempo
    decorrido desde a criação sobre o prazo de entrega do produto, o que
    mantém a progressão determinística e sem estado pra manter em dia.

    As quatro etapas de trânsito dividem o prazo em fatias iguais e
    "entregue" começa exatamente quando o prazo vence, ficando assim pra
    sempre. `agora` existe pra testar sem esperar o relógio; o padrão é UTC
    porque é nele que o SQLite grava `data_criacao`.
    """
    etapas = models.ETAPAS_RASTREIO
    criacao = _para_datetime(pedido.get("data_criacao"))
    if criacao is None:
        return etapas[0]

    agora = agora or datetime.utcnow()
    total = _prazo_em_segundos(pedido)
    decorrido = (agora - criacao).total_seconds()

    if total <= 0 or decorrido >= total:
        return etapas[-1]
    if decorrido <= 0:
        return etapas[0]

    fatia = total / (len(etapas) - 1)
    return etapas[min(int(decorrido // fatia), len(etapas) - 1)]


def _com_rastreio(pedido: dict, agora: Optional[datetime] = None) -> dict:
    """Sobrepõe ao registro do banco o que é derivado, não armazenado.

    O código é recalculado quando falta (pedido criado antes da coluna
    existir), e o status vem do tempo, não da coluna.
    """
    pedido = dict(pedido)
    pedido["status"] = status_derivado(pedido, agora)
    pedido["codigo_rastreio"] = pedido.get("codigo_rastreio") or gerar_codigo_rastreio(pedido["id"])
    return pedido


# --- Pedidos -------------------------------------------------------------

def criar_pedido(produto_id: int, quantidade: int = 1, endereco_entrega: str = "") -> dict:
    produto = obter_produto(produto_id)
    if produto["estoque"] < quantidade:
        raise exceptions.EstoqueInsuficiente(produto["nome"], produto["estoque"])

    valor_total = round(produto["preco"] * quantidade, 2)
    pedido = repositories.inserir_pedido(
        produto_id=produto_id,
        produto_nome=produto["nome"],
        quantidade=quantidade,
        valor_total=valor_total,
        endereco_entrega=endereco_entrega,
    )
    # O código depende do id, que só existe depois do INSERT.
    pedido = repositories.definir_codigo_rastreio(
        pedido["id"], gerar_codigo_rastreio(pedido["id"])
    )
    return _com_rastreio(pedido)


def obter_pedido(pedido_id: int) -> dict:
    pedido = repositories.obter_pedido(pedido_id)
    if pedido is None:
        raise exceptions.PedidoNaoEncontrado(pedido_id)
    return _com_rastreio(pedido)


def listar_pedidos() -> List[dict]:
    return [_com_rastreio(pedido) for pedido in repositories.listar_pedidos()]


def rastrear_pedido(pedido_id: int) -> dict:
    pedido = obter_pedido(pedido_id)
    etapa_atual = pedido["status"]
    return {
        "pedido_id": pedido_id,
        "codigo_rastreio": pedido["codigo_rastreio"],
        "etapa_atual": etapa_atual,
        "localizacao": models.LOCALIZACOES_MOCK.get(etapa_atual, "Desconhecida"),
        "etapas": models.ETAPAS_RASTREIO,
        "entrega_agendada": pedido.get("data_entrega_agendada"),
    }


# --- Notificação de mudança de status --------------------------------------

def _texto_da_notificacao(pedido: dict, status: str) -> str:
    modelo = models.MENSAGENS_NOTIFICACAO.get(
        status, "Seu pedido #{id} ({produto}) mudou de status: {status}."
    )
    return modelo.format(
        id=pedido["id"],
        produto=pedido["produto_nome"],
        codigo=pedido["codigo_rastreio"],
        status=status,
    )


def _avancou(status: str, notificado: Optional[str]) -> bool:
    """Só é novidade o que está adiante do que já foi comunicado.

    Comparar por igualdade não bastava: a etapa é derivada do relógio e da
    régua de tempo, então ela pode recuar (a escala de `SEGUNDOS_POR_DIA_ENTREGA`
    muda entre execuções, o prazo do produto aumenta no catálogo), e um pedido
    já anunciado como entregue voltava a ser anunciado como confirmado. Etapa
    desconhecida (nula, de pedido migrado, ou gravada por versão anterior)
    conta como nunca comunicada.
    """
    etapas = models.ETAPAS_RASTREIO
    if notificado not in etapas:
        return True
    return etapas.index(status) > etapas.index(notificado)


def sincronizar_notificacoes(agora: Optional[datetime] = None) -> List[dict]:
    """Avisa no histórico do chat os pedidos que andaram desde o último aviso.

    Idempotente: a etapa comunicada fica gravada em `status_notificado`, então
    chamar duas vezes seguidas não repete mensagem. Em ordem de pedido, pra
    que o histórico fique coerente quando vários avançam de uma vez.
    """
    novas: List[dict] = []
    for registro in sorted(repositories.listar_pedidos(), key=lambda p: p["id"]):
        pedido = _com_rastreio(registro, agora)
        if not _avancou(pedido["status"], registro.get("status_notificado")):
            continue

        # Reserva antes de escrever: se outra aba já avisou esta etapa entre a
        # leitura e agora, o UPDATE não acerta linha nenhuma e a mensagem não
        # é gravada duas vezes.
        if not repositories.marcar_status_notificado(pedido["id"], pedido["status"]):
            continue

        conteudo = _texto_da_notificacao(pedido, pedido["status"])
        repositories.inserir_mensagem("assistant", conteudo, models.TIPO_NOTIFICACAO)
        novas.append(
            {"role": "assistant", "content": conteudo, "tipo": models.TIPO_NOTIFICACAO}
        )

    return novas


def agendar_entrega(pedido_id: int, data_entrega: str) -> dict:
    """Combina a data com o cliente. Não mexe no status: o pedido continua
    andando pela logística, agendado ou não."""
    obter_pedido(pedido_id)
    return _com_rastreio(repositories.atualizar_entrega_agendada(pedido_id, data_entrega))


def gerar_segunda_via(pedido_id: int, tipo: str = "boleto") -> dict:
    pedido = obter_pedido(pedido_id)

    if tipo == "nf":
        return {
            "tipo": "nota_fiscal",
            "pedido_id": pedido_id,
            "numero_nf": f"NF-{pedido_id:06d}",
            "chave_acesso": f"MOCK{pedido_id:044d}",
            "data_emissao": pedido["data_criacao"],
            "valor": pedido["valor_total"],
        }

    vencimento = (date.today() + timedelta(days=7)).isoformat()
    return {
        "tipo": "boleto",
        "pedido_id": pedido_id,
        "linha_digitavel": f"34191.79001 01043.510047 91020.150008 {pedido_id} {int(pedido['valor_total'] * 100):010d}",
        "vencimento": vencimento,
        "valor": pedido["valor_total"],
    }
