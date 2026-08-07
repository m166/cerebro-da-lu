"""Regras de negócio.

Os services validam, calculam e orquestram os repositories. Quando algo
não faz sentido no domínio, levantam uma exceção de `app.exceptions` — quem
chama decide como apresentar (HTTP ou mensagem pro modelo).
"""

from datetime import date, timedelta
from typing import Callable, List, Optional

from app import exceptions, models, repositories


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


# --- Sugestão e comparação -------------------------------------------------

def _score_custo_beneficio(candidatos: List[dict]) -> Callable[[dict], float]:
    """Score normalizado dentro do conjunto avaliado.

    A normalização é relativa aos candidatos — comparar um mouse com um
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


# --- Pedidos -------------------------------------------------------------

def criar_pedido(produto_id: int, quantidade: int = 1, endereco_entrega: str = "") -> dict:
    produto = obter_produto(produto_id)
    if produto["estoque"] < quantidade:
        raise exceptions.EstoqueInsuficiente(produto["nome"], produto["estoque"])

    valor_total = round(produto["preco"] * quantidade, 2)
    return repositories.inserir_pedido(
        produto_id=produto_id,
        produto_nome=produto["nome"],
        quantidade=quantidade,
        valor_total=valor_total,
        endereco_entrega=endereco_entrega,
    )


def obter_pedido(pedido_id: int) -> dict:
    pedido = repositories.obter_pedido(pedido_id)
    if pedido is None:
        raise exceptions.PedidoNaoEncontrado(pedido_id)
    return pedido


def rastrear_pedido(pedido_id: int) -> dict:
    pedido = obter_pedido(pedido_id)
    etapa_atual = pedido["status"]
    return {
        "pedido_id": pedido_id,
        "etapa_atual": etapa_atual,
        "localizacao": models.LOCALIZACOES_MOCK.get(etapa_atual, "Desconhecida"),
        "etapas": models.ETAPAS_RASTREIO,
    }


def agendar_entrega(pedido_id: int, data_entrega: str) -> dict:
    obter_pedido(pedido_id)
    return repositories.atualizar_entrega_agendada(pedido_id, data_entrega)


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
