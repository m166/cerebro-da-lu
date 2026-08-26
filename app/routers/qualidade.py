"""Satisfação do cliente e diagnóstico do que está errando.

São dois públicos diferentes, e por isso dois routers:

- **`/api/satisfacao`** é do cliente, e vai pro ar junto com a app. Exige
  identificação, como tudo que é dado de cliente.
- **`/api/diagnostico`** é da loja, e mostra reclamação, taxa de abandono e
  buraco na base de conhecimento. **Não pode ficar aberto na internet**, e
  como ainda não existe autenticação de operador aqui, ele acompanha o
  simulador: só sobe quando `SIMULADOR_ATIVO`. Quando houver login de
  operador, é essa dependência que entra no lugar da flag.
"""

from fastapi import APIRouter, Depends, HTTPException

from app import exceptions, schemas, services
from app.routers.identificacao import exigir_identificacao

router = APIRouter(
    prefix="/api",
    tags=["qualidade"],
    dependencies=[Depends(exigir_identificacao)],
)

interno = APIRouter(prefix="/api", tags=["diagnóstico"])


@router.post("/satisfacao", response_model=schemas.SatisfacaoOut)
def avaliar(dados: schemas.SatisfacaoRequest):
    try:
        return services.registrar_satisfacao(
            nota=dados.nota, comentario=dados.comentario or "", assunto=dados.assunto or ""
        )
    except exceptions.NotaInvalida as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@interno.get("/diagnostico")
def diagnostico(limite: int = 10):
    """O que o sistema está errando, em ordem de impacto.

    Só aponta e sugere, não corrige nada sozinho. Mudança automática de
    comportamento precisaria de um jeito contínuo de detectar regressão, e a
    régua deste projeto (a pasta `evals/`) roda sob demanda.
    """
    return services.diagnostico(limite=limite)
