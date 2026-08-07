"""Endpoints de catálogo: listagem, detalhe, comparação e sugestão."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app import exceptions, schemas, services

router = APIRouter(prefix="/api", tags=["produtos"])


@router.get("/categorias", response_model=List[str])
def listar_categorias():
    return services.listar_categorias()


@router.get("/produtos", response_model=List[schemas.ProdutoOut])
def listar_produtos(
    query: str = "",
    categoria: str = "",
    limite: Optional[int] = Query(default=None, ge=1),
):
    return services.buscar_produtos(query=query, categoria=categoria, limite=limite)


@router.get("/produtos/sugestao")
def sugerir_produto(categoria: str = "", criterio: str = "melhor_custo_beneficio"):
    try:
        return services.sugerir_produto(categoria=categoria, criterio=criterio)
    except exceptions.ErroDeDominio as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/produtos/comparacao", response_model=schemas.ComparacaoOut)
def comparar_produtos(request: schemas.ComparacaoRequest):
    try:
        return services.comparar_produtos(
            categoria=request.categoria, produto_ids=request.produto_ids
        )
    except exceptions.ComparacaoInvalida as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/produtos/{produto_id}", response_model=schemas.ProdutoOut)
def obter_produto(produto_id: int):
    try:
        return services.obter_produto(produto_id)
    except exceptions.ProdutoNaoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/produtos/{produto_id}/estoque", response_model=schemas.EstoqueOut)
def consultar_estoque(produto_id: int):
    try:
        return services.consultar_estoque(produto_id)
    except exceptions.ProdutoNaoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc))
