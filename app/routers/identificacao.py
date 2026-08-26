"""Quem está falando: o número do cliente vira a sessão.

No WhatsApp isto não é uma tela, é o envelope da mensagem: o número chega
junto e ninguém "entra" em lugar nenhum. Como o simulador roda no
navegador, alguém precisa dizer de qual celular a conversa está saindo, e
esse alguém é este endpoint. O número fica no cookie, que faz o papel do
aparelho.

Quando o canal real entrar, é aqui que ele encosta: o webhook lê o número
do remetente e chama a mesma normalização, sem tela nenhuma no meio.
"""

from fastapi import APIRouter, HTTPException, Request, Response

from app import database, schemas, services, sessao, telefone

router = APIRouter(prefix="/api", tags=["sessão"])

SEM_IDENTIFICACAO = (
    "Não sei de qual número você está falando. Informe o telefone pra continuar."
)


def exigir_identificacao() -> str:
    """Dependência dos endpoints que leem ou escrevem dado de um cliente.

    Sem isto, uma requisição sem número cairia na sessão `local`, que é a
    dos scripts e testes: todo mundo que chegasse sem se identificar
    conversaria na mesma caixa, que é exatamente o vazamento que as sessões
    resolveram. Catálogo e base de conhecimento ficam de fora, são da loja
    e não de ninguém.
    """
    if not sessao.identificado():
        raise HTTPException(status_code=401, detail=SEM_IDENTIFICACAO)
    return sessao.atual()


def _resposta(numero: str) -> dict:
    dados = services.dados_do_cliente()
    return {
        "telefone": numero,
        "telefone_formatado": telefone.formatar(numero),
        "nome": dados.get("nome"),
        "endereco": dados.get("endereco"),
    }


@router.get("/sessao", response_model=schemas.IdentificacaoOut)
def quem_sou_eu():
    return _resposta(exigir_identificacao())


@router.post("/sessao", response_model=schemas.IdentificacaoOut)
def identificar(dados: schemas.IdentificacaoRequest, request: Request, response: Response):
    try:
        numero = telefone.normalizar(dados.telefone)
    except telefone.TelefoneInvalido as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    cookie_anterior = request.cookies.get(sessao.NOME_DO_COOKIE)

    token = sessao.definir(numero)
    try:
        # Cookie que não é telefone foi gravado por uma versão anterior, e a
        # conversa dele é deste mesmo navegador: pode vir junto. Cookie que
        # já é telefone é outro cliente, e aí trocar de número é trocar de
        # pessoa, não levar o histórico de uma pra outra.
        if cookie_anterior and sessao.do_cookie(cookie_anterior) is None:
            database.transferir_sessao(cookie_anterior, numero)
        database.adotar_dados_orfaos(numero)
        corpo = _resposta(numero)
    finally:
        sessao.restaurar(token)

    response.set_cookie(
        sessao.NOME_DO_COOKIE,
        numero,
        max_age=sessao.VALIDADE_DO_COOKIE,
        httponly=True,
        samesite="lax",
    )
    return corpo


@router.delete("/sessao", status_code=204)
def esquecer(response: Response):
    """Desliga o aparelho do simulador, sem apagar nada.

    A conversa continua no banco esperando o número: quem voltar com ele
    encontra tudo como deixou, que é como o WhatsApp se comporta ao trocar
    de celular.
    """
    response.delete_cookie(sessao.NOME_DO_COOKIE)
