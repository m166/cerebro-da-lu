"""Endpoints de pedidos: criação, consulta, rastreio, agendamento e 2ª via."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app import exceptions, schemas, services
from app.routers.identificacao import exigir_identificacao

# Pedido é do cliente, não da loja: sem saber de qual número veio a
# requisição não há o que listar nem em nome de quem comprar.
router = APIRouter(
    prefix="/api/pedidos",
    tags=["pedidos"],
    dependencies=[Depends(exigir_identificacao)],
)


@router.get("", response_model=List[schemas.PedidoOut])
def listar_pedidos():
    return services.listar_pedidos()


@router.post("", response_model=schemas.PedidoOut)
def criar_pedido(request: schemas.PedidoCreate):
    try:
        return services.criar_pedido(
            produto_id=request.produto_id,
            quantidade=request.quantidade,
            endereco_entrega=request.endereco_entrega,
        )
    except exceptions.ProdutoNaoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except exceptions.EstoqueInsuficiente as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/{pedido_id}", response_model=schemas.PedidoOut)
def obter_pedido(pedido_id: int):
    try:
        return services.obter_pedido(pedido_id)
    except exceptions.PedidoNaoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{pedido_id}/rastreio", response_model=schemas.RastreioOut)
def rastrear_pedido(pedido_id: int):
    try:
        return services.rastrear_pedido(pedido_id)
    except exceptions.PedidoNaoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{pedido_id}/agendar-entrega", response_model=schemas.PedidoOut)
def agendar_entrega(pedido_id: int, request: schemas.AgendamentoRequest):
    try:
        return services.agendar_entrega(pedido_id, request.data_entrega)
    except exceptions.PedidoNaoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{pedido_id}/segunda-via")
def segunda_via(pedido_id: int, tipo: str = "boleto"):
    try:
        return services.gerar_segunda_via(pedido_id, tipo)
    except exceptions.PedidoNaoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc))
