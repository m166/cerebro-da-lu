"""Leitura da mensagem do cliente pra ajustar o prompt da rodada.

Duas coisas saem daqui: o **registro** em que ele escreve (solto, neutro,
formal) e se ele **só cumprimentou**. As duas viram frase no system prompt,
e as duas estão aqui pelo mesmo motivo de orçamento: instrução que só serve
a um tipo de mensagem não pode ser paga em todas.

O teto da conta free é 8000 tokens por minuto, e uma conversa com uma
chamada de ferramenta já são duas requisições carregando persona e schemas
inteiros. Cada bloco que sai da persona fixa e vira injeção condicional
desconta desse limite em toda rodada.

## Em que registro o cliente está falando

A Lu deve espelhar o jeito do cliente, e pedir isso na persona não bastou:
o modelo lê a instrução, concorda e responde neutro do mesmo jeito. A
persona é grande e cheia de regra de concisão ("comece pela resposta",
"teto de 400 caracteres"), que disparam em toda mensagem e ganham da
orientação de tom.

Então o registro é detectado aqui, por marcador, e entra no system prompt
como uma frase direta ("o cliente está escrevendo solto, responda assim").
É o mesmo remédio que o cadastro já usa: o que o modelo precisa ter em
vista toda rodada não pode depender de ele inferir sozinho.

Detecção por palavra é grosseira de propósito. Ela não precisa acertar o
sentido, só reconhecer o traje da conversa, e "blz mano" e "gostaria de
saber" se separam bem por vocabulário.
"""

import re
import unicodedata
from typing import List, Optional

INFORMAL = "informal"
NEUTRO = "neutro"
FORMAL = "formal"

# Gíria, abreviação de teclado e marca de riso. Sem acento, porque a
# comparação é feita sobre o texto já normalizado.
MARCAS_INFORMAIS = frozenset(
    """
    eae iae ae salve blz beleza vc vcs pq pqp tbm tb mano cara mlk veio
    brother bro parca sla vlw valeu tmj tlg obg mds po poxa caraca massa
    top maneiro bora partiu firmeza suave tranquilo tranks role rolê
    dahora bagulho parada trampo grana barato caro pra pro to ta tao ne
    num nao_sei kk kkk kkkk kkkkk rs rsrs haha hehe eita nossa
    """.split()
)

# Vocabulário de quem trata a loja por "prezados".
MARCAS_FORMAIS = frozenset(
    """
    prezado prezada prezados senhor senhora sr sra gostaria poderia
    poderiam solicito solicitar informar informacoes gentileza favor
    cordialmente atenciosamente agradeco agradecido desde ja aguardo
    retorno consulta verificar disponibilidade adquirir efetuar realizar
    """.split()
)

# "kkkk" de qualquer comprimento, e alongamento tipo "aaah", "eiii".
_RISADA = re.compile(r"\b(?:k{2,}|(?:ha|he|hi){2,}|rs{1,})\b")

_PALAVRA = re.compile(r"[a-z]+")


def _sem_acento(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", (texto or "").lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def _pontuar(mensagem: str) -> int:
    """Saldo de marcadores: positivo é solto, negativo é formal, 0 é mudo."""
    texto = _sem_acento(mensagem)
    palavras = _PALAVRA.findall(texto)

    soltos = sum(1 for p in palavras if p in MARCAS_INFORMAIS)
    soltos += len(_RISADA.findall(texto))
    formais = sum(1 for p in palavras if p in MARCAS_FORMAIS)

    return soltos - formais


def detectar(mensagens: List[str]) -> str:
    """Registro do cliente, olhando da mensagem mais recente pra trás.

    Recebe as falas dele em ordem cronológica. Uma mensagem sem marcador
    nenhum ("quanto custa?") não zera o registro: a conversa continua no
    tom que já vinha, então a busca segue pra trás até achar sinal.
    """
    for mensagem in reversed(mensagens or []):
        saldo = _pontuar(mensagem)
        if saldo > 0:
            return INFORMAL
        if saldo < 0:
            return FORMAL
    return NEUTRO


_INSTRUCOES = {
    INFORMAL: (
        "O cliente está escrevendo solto, com gíria e abreviação. Responda "
        "no mesmo tom: pode usar gíria, contração e resposta curta de "
        "amigo. Se ele te cumprimentou, devolva o cumprimento do jeito "
        "dele antes de responder."
    ),
    FORMAL: (
        "O cliente está escrevendo de maneira formal. Responda no mesmo "
        "tom: cordial, sem gíria e sem abreviação."
    ),
}


def instrucao(registro: str) -> Optional[str]:
    """Frase que entra no system prompt, ou `None` quando não há o que dizer.

    O registro neutro não gera instrução de propósito: mandar "responda
    neutro" gastaria token pra repetir o que a persona já é por padrão.
    """
    return _INSTRUCOES.get(registro)


# --- Cliente que só bateu na porta -----------------------------------------

# Cumprimento puro, sem pedido junto. Sem acento, como o resto da comparação.
_CUMPRIMENTOS = frozenset(
    """
    oi ola oie oii oiee eae iae ae salve opa opaa bom boa dia tarde noite
    tudo bem bao boa? blz beleza joia jóia certo como vai vc voce ai la
    e ta esta sussa suave firmeza fala falae
    """.split()
)

# Mais que isso já não é só cumprimento, é pergunta com "oi" na frente.
_MAXIMO_DE_PALAVRAS = 7

INSTRUCAO_ABERTURA = (
    "O cliente só cumprimentou, sem pedir nada ainda. Devolva o cumprimento "
    "e, se for o primeiro contato dele, apresente-se em uma frase (seu nome "
    "e que você ajuda a escolher produto, acompanhar pedido e resolver "
    "boleto e nota), terminando com o que ele precisa hoje. Se você já sabe "
    "o nome dele, ou a conversa já vem de antes, não se apresente de novo: "
    "cumprimente pelo nome e pergunte no que ajuda. Não chame ferramenta "
    "nenhuma: cumprimento não é consulta."
)


def so_cumprimentou(mensagem: str) -> bool:
    """Se a mensagem é um "oi" e nada mais.

    A apresentação da Lu é longa demais pra viver na persona, que é paga em
    toda requisição pra servir só à primeira mensagem da conversa. Aqui ela
    é injetada quando faz falta.

    O corte é conservador: na dúvida, não é cumprimento. Errar pra menos
    custa uma abertura mais seca; errar pra mais faria a Lu se apresentar
    no lugar de responder o que foi perguntado.
    """
    palavras = _PALAVRA.findall(_sem_acento(mensagem))
    if not palavras or len(palavras) > _MAXIMO_DE_PALAVRAS:
        return False
    return all(p in _CUMPRIMENTOS for p in palavras)
