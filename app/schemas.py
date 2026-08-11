"""Schemas Pydantic: contratos de entrada e saída da API.

Usa `Optional[...]` em vez de `X | None` porque o venv do projeto roda
Python 3.9, onde a sintaxe de união com `|` não existe em runtime.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


# --- Entrada -----------------------------------------------------------

class ChatRequest(BaseModel):
    content: str


class PedidoCreate(BaseModel):
    produto_id: int
    quantidade: int = Field(default=1, ge=1)
    endereco_entrega: str = ""


class AgendamentoRequest(BaseModel):
    data_entrega: str


class ComparacaoRequest(BaseModel):
    categoria: str = ""
    produto_ids: List[int] = []


# --- Saída ---------------------------------------------------------------

class ChatResponse(BaseModel):
    reply: str
    produtos: List["ProdutoOut"] = []


class MensagemOut(BaseModel):
    role: str
    content: str
    tipo: str = "chat"
    produtos: List["ProdutoOut"] = []


class ProdutoOut(BaseModel):
    id: int
    nome: str
    categoria: str
    preco: float
    prazo_entrega_dias: int
    avaliacao: float
    estoque: int
    descricao: str
    imagem: str


class EstoqueOut(BaseModel):
    produto_id: int
    nome: str
    estoque: int
    disponivel: bool


class PedidoOut(BaseModel):
    id: int
    produto_id: int
    produto_nome: str
    quantidade: int
    valor_total: float
    endereco_entrega: Optional[str] = None
    status: str
    codigo_rastreio: str
    data_criacao: str
    data_entrega_agendada: Optional[str] = None


class RastreioOut(BaseModel):
    pedido_id: int
    codigo_rastreio: str
    etapa_atual: str
    localizacao: str
    etapas: List[str]
    entrega_agendada: Optional[str] = None


class NotificacoesOut(BaseModel):
    novas: List[MensagemOut]


class ComparacaoOut(BaseModel):
    produtos: List[ProdutoOut]
    melhor_preco: str
    melhor_prazo: str
    melhor_avaliacao: str
    melhor_custo_beneficio: str
