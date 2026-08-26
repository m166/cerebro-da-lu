"""O que o cliente revelou sem que ninguém perguntasse, detectado em código.

Irmão de `registro.py`, e existe pelo mesmo motivo medido. A ferramenta
`anotar_da_conversa` funciona, mas só quando a mensagem não disputa com
outra coisa: pedindo "meu orçamento é no máximo 2 mil" sozinho, o modelo
anota; dizendo "meu limite é 2 mil, quero um notebook pra faculdade", ele
chama `buscar_produtos` e o orçamento se perde. Recusa ("não gostei do
Chromebook") ele não anotou em nenhuma das tentativas.

A conclusão é a mesma que valeu pro tom: **o que precisa valer em toda
rodada não pode depender de o modelo lembrar de gravar.** O que dá pra ler
do texto é lido aqui, de forma determinística, e a ferramenta fica pro que
só o modelo entende (a finalidade da compra, e o que este módulo não pegar).

Nada aqui inventa: se não houver sinal claro, devolve vazio, porque anotar
orçamento errado é pior que não anotar. A Lu passaria a esconder produto que
o cliente podia comprar.
"""

import re
import unicodedata
from typing import Iterable, List, Optional

# Só conta como orçamento se a frase tiver um destes. "Gastei 2 mil no
# último notebook" não é limite de compra, é história.
MARCADORES_DE_LIMITE = (
    "orcamento",
    "limite",
    "ate ",
    "no maximo",
    "maximo de",
    "gastar",
    "pagar",
    "tenho so",
    "no maximo",
    "cabe ",
    "barato ate",
)

NEGACOES = (
    "nao gostei",
    "nao quero",
    "nao curti",
    "nao serve",
    "nao rolou",
    "descartei",
    "esse nao",
    "esse ai nao",
    "menos esse",
    "tira o",
    "tira esse",
    "sem o",
)

# "2 mil", "R$ 1.500", "500 reais", "300 conto"
_MIL = re.compile(r"(\d+(?:[.,]\d+)?)\s*mil\b")
_REAIS = re.compile(r"r\$\s*(\d[\d.]*(?:,\d{2})?)")
_SOLTO = re.compile(r"\b(\d[\d.]*)\s*(?:reais|conto|contos|pila|pau)\b")


def _sem_acento(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def _numero(bruto: str) -> Optional[float]:
    limpo = bruto.replace(".", "").replace(",", ".")
    try:
        return float(limpo)
    except ValueError:
        return None


def _valor_da_frase(frase: str) -> Optional[float]:
    achado = _MIL.search(frase)
    if achado:
        valor = _numero(achado.group(1))
        return valor * 1000 if valor else None
    for padrao in (_REAIS, _SOLTO):
        achado = padrao.search(frase)
        if achado:
            return _numero(achado.group(1))
    return None


def orcamento(falas: Iterable[str]) -> Optional[str]:
    """Quanto o cliente disse que quer gastar, da fala mais recente pra trás.

    Devolve texto já formatado pro prompt ("até R$ 2.000"), e não número,
    porque quem lê é o modelo. A varredura é de trás pra frente: o cliente
    muda de ideia, e o último valor é o que vale.
    """
    for frase in reversed(list(falas)):
        limpa = _sem_acento(frase)
        if not any(marcador in limpa for marcador in MARCADORES_DE_LIMITE):
            continue
        valor = _valor_da_frase(limpa)
        if valor and valor > 0:
            return f"até R$ {valor:,.0f}".replace(",", ".")
    return None


def _tokens_distintivos(nome: str, universo: List[str]) -> List[str]:
    """Palavras do nome que quase só aparecem neste produto.

    "Notebook Chromebook 11" tem "notebook", que casa com dezenas de itens, e
    "chromebook", que casa com poucos. Sem esse filtro, "não quero notebook"
    é lido como recusa de um modelo específico.

    O `universo` é o catálogo inteiro, e precisa ser mesmo. Medir a
    distintividade só entre os produtos já mostrados dá o contrário do
    esperado: com dois notebooks na tela, "notebook" aparece em 2 de 2 e
    passa por distintiva. Foi assim que o teste de falso positivo quebrou.
    """
    todos = [_sem_acento(n) for n in universo]
    distintivos = []
    for palavra in _sem_acento(nome).split():
        if len(palavra) < 5:
            continue
        aparicoes = sum(1 for outro in todos if palavra in outro)
        if aparicoes <= 3:
            distintivos.append(palavra)
    return distintivos


def recusas(
    falas: Iterable[str], candidatos: List[dict], universo: List[str]
) -> List[str]:
    """Produtos que o cliente descartou, entre os que já foram mostrados.

    Procura só no que a Lu já apresentou, e não no catálogo inteiro: é onde a
    recusa pode acontecer, e restringir evita casar o nome de um produto que
    nunca esteve na conversa. O `universo` entra só pra medir quais palavras
    são específicas o bastante pra valer como menção.
    """
    recusados = []
    for frase in falas:
        limpa = _sem_acento(frase)
        if not any(negacao in limpa for negacao in NEGACOES):
            continue
        for produto in candidatos:
            if produto["nome"] in recusados:
                continue
            if any(token in limpa for token in _tokens_distintivos(produto["nome"], universo)):
                recusados.append(produto["nome"])
    return recusados
