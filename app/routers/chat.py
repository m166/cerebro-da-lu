"""Endpoints da conversa com a Lu."""

from typing import List

from fastapi import APIRouter, HTTPException

from app import schemas
from app.ai import chat as chat_service

router = APIRouter(prefix="/api", tags=["chat"])


@router.get("/history", response_model=List[schemas.MensagemOut])
def history():
    return chat_service.historico()


@router.post("/chat", response_model=schemas.ChatResponse)
def chat(request: schemas.ChatRequest):
    try:
        return {"reply": chat_service.responder(request.content)}
    except chat_service.ChatIncompleto as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erro ao falar com a Groq: {exc}")
