"""Endpoints da conversa com a Lu."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app import schemas, services
from app.ai import chat as chat_service
from app.routers.identificacao import exigir_identificacao

# A conversa inteira é de um número só: histórico, resposta e aviso de
# pedido. Sem identificação não há de quem seja a mensagem.
router = APIRouter(
    prefix="/api",
    tags=["chat"],
    dependencies=[Depends(exigir_identificacao)],
)


@router.get("/history", response_model=List[schemas.MensagemOut])
def history():
    return chat_service.historico()


@router.get("/notificacoes", response_model=schemas.NotificacoesOut)
def notificacoes():
    """Avança a régua de status dos pedidos e devolve o que for novidade.

    A mudança de etapa é derivada do relógio, então é a consulta que descobre
    que o pedido andou. As mensagens novas já entram no histórico, aqui elas
    voltam só pra tela mostrar sem recarregar tudo.
    """
    return {"novas": services.sincronizar_notificacoes()}


@router.post("/chat", response_model=schemas.ChatResponse)
def chat(request: schemas.ChatRequest):
    try:
        return chat_service.responder(request.content, request.imagem)
    except chat_service.ImagemRecusada as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except chat_service.LimiteDeUso as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except chat_service.ChatIncompleto as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erro ao falar com a Groq: {exc}")
