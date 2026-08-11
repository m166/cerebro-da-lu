"""Ponto de entrada da aplicação: cria o app e registra os routers.

Rode com: uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app import config, sessao
from app.database import adotar_dados_orfaos, init_db
from app.routers import chat, pedidos, produtos, views


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Cérebro da Lu", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")

@app.middleware("http")
async def sessao_do_visitante(request: Request, call_next):
    """Cada navegador conversa com a sua própria Lu.

    Sem isto o histórico era global: qualquer pessoa que abrisse o endereço
    via a conversa, o cadastro e os pedidos de quem tinha usado antes. Não
    há login, o id é anônimo e vai num cookie.
    """
    existente = request.cookies.get(sessao.NOME_DO_COOKIE)
    sessao_id = existente or sessao.nova()

    token = sessao.definir(sessao_id)
    try:
        if not existente:
            # Primeiro visitante depois da mudança leva o que já estava
            # gravado, senão a conversa e os pedidos dele sumiriam da tela.
            adotar_dados_orfaos(sessao_id)
        resposta = await call_next(request)
    finally:
        sessao.restaurar(token)

    if not existente:
        resposta.set_cookie(
            sessao.NOME_DO_COOKIE,
            sessao_id,
            max_age=sessao.VALIDADE_DO_COOKIE,
            httponly=True,
            samesite="lax",
        )
    return resposta


app.include_router(views.router)
app.include_router(chat.router)
app.include_router(produtos.router)
app.include_router(pedidos.router)
