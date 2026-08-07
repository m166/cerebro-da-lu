"""Ponto de entrada da aplicação: cria o app e registra os routers.

Rode com: uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import config
from app.database import init_db
from app.routers import chat, pedidos, produtos, views


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Cérebro da Lu", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")

app.include_router(views.router)
app.include_router(chat.router)
app.include_router(produtos.router)
app.include_router(pedidos.router)
