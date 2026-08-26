"""Ponto de entrada da aplicação: cria o app e registra os routers.

Rode com: uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app import config, sessao
from app.database import init_db
from app.routers import chat, identificacao, pedidos, produtos, qualidade, views


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Cérebro da Lu", lifespan=lifespan)

# O simulador não sobe em produção (veja `config.SIMULADOR_ATIVO`). Some a
# tela e some o arquivo estático junto: deixar o `/static` servindo o JS de
# uma tela que não existe entregaria de graça o mapa da API pra quem só
# encontrasse a URL.
if config.SIMULADOR_ATIVO:
    app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")

@app.middleware("http")
async def sessao_do_visitante(request: Request, call_next):
    """Descobre com qual número esta requisição está falando.

    O middleware só transporta: lê o cookie e coloca o telefone no
    contextvar. Quem exige a identificação é a dependência
    `routers.identificacao.exigir_identificacao`, nos endpoints que mexem
    em dado de cliente. A separação importa porque catálogo e base de
    conhecimento são da loja, e continuam abertos a quem só quer olhar.

    Sem número, nenhuma sessão é inventada: no WhatsApp o remetente sempre
    vem junto da mensagem, e um id anônimo aqui só criaria uma conversa
    órfã que ninguém reencontra.

    Toda requisição define a sessão, inclusive pra dizer que não há: sem
    isso ela herdaria o que estivesse no contextvar da thread, e uma
    requisição sem cookie passaria por identificada de carona numa outra.
    """
    numero = sessao.do_cookie(request.cookies.get(sessao.NOME_DO_COOKIE))

    token = sessao.definir(numero)
    try:
        return await call_next(request)
    finally:
        sessao.restaurar(token)


# `views` serve a tela e `identificacao` deixa dizer "sou este número" por um
# formulário. Os dois são o simulador, e o segundo é o que de fato vaza: sem
# ele a tela seria só uma casca, com ele qualquer um assume qualquer número.
# Tirar só o HTML e deixar o endpoint de pé seria teatro de segurança.
#
# Em produção quem diz o número é o webhook do WhatsApp, no envelope da
# mensagem. Enquanto esse transporte não existir, a app publicada responde
# 401 em tudo que é do cliente, e isso é a resposta correta, não uma falta.
if config.SIMULADOR_ATIVO:
    app.include_router(views.router)
    app.include_router(identificacao.router)
app.include_router(chat.router)
app.include_router(produtos.router)
app.include_router(pedidos.router)
app.include_router(qualidade.router)

# O diagnóstico expõe reclamação de cliente e taxa de abandono, que é dado de
# operação da loja. Enquanto não houver login de operador, ele acompanha o
# simulador em vez de ficar aberto numa URL pública.
if config.SIMULADOR_ATIVO:
    app.include_router(qualidade.interno)
