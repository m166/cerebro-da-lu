"""As regras do canal WhatsApp, separadas de quem escreve a mensagem.

Este módulo não fala com a Meta e não escolhe provedor. Ele guarda o que a
Cloud API **exige** da mensagem antes de ela existir, pra que plugar o canal
de verdade seja escrever o transporte, e não descobrir que a conversa toda
está no formato errado.

## As três regras que mudam o produto

1. **Fora da janela de 24 horas, texto livre não passa.** A Cloud API só
   entrega mensagem espontânea se ela for um template aprovado antes. A
   janela reabre a cada mensagem do cliente e vale 24h a partir da última
   que ele mandou, não da última que a Lu respondeu. É por isso que o aviso
   de pedido (que sai sozinho, dias depois) precisa ser template, enquanto a
   resposta no meio da conversa pode ser texto solto.

2. **Negrito é `*um asterisco*`, não `**dois**`.** O WhatsApp não renderiza
   Markdown. `**oferta**` chega ao cliente com os asteriscos visíveis.

3. **Template é aprovado por categoria, e a categoria decide o preço.**
   Desde abril de 2025 a Meta reclassifica sozinha o que ela julgar
   promocional, e UTILITY reclassificado como MARKETING custa mais caro. Os
   avisos daqui são todos UTILITY legítimos: seguem uma ação do cliente (a
   compra) e não vendem nada. Não acrescente "aproveite", "confira nossas
   ofertas" nem link de vitrine no corpo deles.

## O que ainda não está aqui

Webhook, envio e escolha de provedor. O número de telefone já é o
`sessao_id` no formato do `wa_id` (DDI + dígitos, sem símbolos), então
receber a mensagem é ligar o webhook na sessão que já existe.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

# --- Limites da Cloud API ---------------------------------------------------
#
# Estourar qualquer um deles é 400 na hora do envio, não degradação. Os
# números são da documentação da Meta e valem por componente.

LIMITE_TEXTO_LIVRE = 4096
LIMITE_CORPO_TEMPLATE = 1024
LIMITE_CABECALHO = 60
LIMITE_RODAPE = 60
LIMITE_BOTAO = 20
MAX_BOTOES_RESPOSTA = 3
LIMITE_TITULO_LISTA = 24
MAX_LINHAS_LISTA = 10

# A janela de atendimento. Conta da última mensagem **do cliente**: resposta
# da Lu não reabre nada, senão bastaria a loja falar sozinha pra manter a
# conversa aberta pra sempre.
JANELA_ATENDIMENTO = timedelta(hours=24)

IDIOMA = "pt_BR"

CATEGORIA_UTILIDADE = "UTILITY"

# Promocional: oferta, desconto, cupom, vitrine. Custa mais caro por mensagem
# e **exige opt-in do cliente**, ao contrário de UTILITY. Não é uma escolha de
# quem escreve o template: a Meta classifica pelo conteúdo, e desde abril de
# 2025 reclassifica sozinha o que tentar passar por utility.
CATEGORIA_MARKETING = "MARKETING"


class TemplateInvalido(Exception):
    """Template que a Meta recusaria. Falha aqui, não no envio."""


class Template:
    """Um template de mensagem no formato que a Cloud API espera.

    O corpo guarda os parâmetros posicionais da Meta (`{{1}}`, `{{2}}`), que
    é o que vai no cadastro do template. `renderizar` produz o texto final,
    e é o mesmo texto que o simulador mostra: assim a tela de teste e o canal
    real nunca divergem, que era o risco de manter as duas mensagens
    escritas em lugares diferentes.
    """

    def __init__(
        self,
        nome: str,
        corpo: str,
        parametros: List[str],
        categoria: str = CATEGORIA_UTILIDADE,
        exemplo: Optional[List[str]] = None,
    ):
        self.nome = nome
        self.corpo = corpo
        self.parametros = parametros
        self.categoria = categoria
        self.exemplo = exemplo or []
        self._validar()

    def _validar(self) -> None:
        # O nome entra na URL da API e no cadastro: minúsculas, dígitos e
        # underscore, nada mais. Nome com acento ou espaço é recusado.
        if not self.nome.replace("_", "").isalnum() or not self.nome.islower():
            raise TemplateInvalido(
                f"Nome '{self.nome}' inválido: use minúsculas, dígitos e underscore."
            )
        if len(self.corpo) > LIMITE_CORPO_TEMPLATE:
            raise TemplateInvalido(
                f"Corpo de '{self.nome}' tem {len(self.corpo)} caracteres, "
                f"o teto é {LIMITE_CORPO_TEMPLATE}."
            )
        esperados = {f"{{{{{i}}}}}" for i in range(1, len(self.parametros) + 1)}
        faltando = esperados - set(_marcadores(self.corpo))
        sobrando = set(_marcadores(self.corpo)) - esperados
        if faltando or sobrando:
            raise TemplateInvalido(
                f"'{self.nome}' declara {sorted(esperados)} mas o corpo usa "
                f"{sorted(set(_marcadores(self.corpo)))}."
            )
        if self.exemplo and len(self.exemplo) != len(self.parametros):
            raise TemplateInvalido(
                f"'{self.nome}' tem {len(self.parametros)} parâmetros e "
                f"{len(self.exemplo)} exemplos. A Meta exige um exemplo por parâmetro."
            )

    def renderizar(self, **valores) -> str:
        """O texto final, com os parâmetros já substituídos."""
        faltando = [p for p in self.parametros if p not in valores]
        if faltando:
            raise TemplateInvalido(
                f"'{self.nome}' precisa de {faltando} e não recebeu."
            )
        texto = self.corpo
        for posicao, parametro in enumerate(self.parametros, start=1):
            texto = texto.replace(f"{{{{{posicao}}}}}", str(valores[parametro]))
        return texto

    def componentes(self, **valores) -> List[dict]:
        """O bloco `components` do payload de envio, na ordem dos parâmetros.

        A Meta casa parâmetro por posição, não por nome: trocar a ordem da
        lista aqui troca o conteúdo na tela do cliente sem nenhum erro.
        """
        return [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": str(valores[p])} for p in self.parametros
                ],
            }
        ]

    def cadastro(self) -> dict:
        """O corpo do POST que registra o template na Meta, pra aprovação."""
        componente = {"type": "BODY", "text": self.corpo}
        if self.exemplo:
            componente["example"] = {"body_text": [self.exemplo]}
        return {
            "name": self.nome,
            "language": IDIOMA,
            "category": self.categoria,
            "components": [componente],
        }


def _marcadores(corpo: str) -> List[str]:
    import re

    return re.findall(r"\{\{\d+\}\}", corpo)


def negrito(texto: str) -> str:
    """Negrito do WhatsApp: um asterisco de cada lado.

    Existe como função pra que ninguém escreva `**` por reflexo de Markdown.
    """
    return f"*{texto}*"


def dentro_da_janela(ultima_mensagem_do_cliente: Optional[datetime], agora=None) -> bool:
    """Se dá pra mandar texto livre, ou se só passa template aprovado.

    Recebe o instante da última mensagem **do cliente**. `None` significa que
    ele nunca escreveu, e aí a janela nunca abriu.
    """
    if ultima_mensagem_do_cliente is None:
        return False
    agora = agora or datetime.now(timezone.utc)
    if ultima_mensagem_do_cliente.tzinfo is None:
        ultima_mensagem_do_cliente = ultima_mensagem_do_cliente.replace(
            tzinfo=timezone.utc
        )
    return agora - ultima_mensagem_do_cliente <= JANELA_ATENDIMENTO


def cabe_em_texto_livre(texto: str) -> bool:
    return len(texto) <= LIMITE_TEXTO_LIVRE
