"""Cálculo do desconto, limitado pela margem do produto.

A regra existe pra que nenhum desconto coma o lucro da venda: o teto é uma
fração da **margem líquida**, nunca do preço. Vender com prejuízo pra fechar
uma venda é o erro que este módulo existe pra impedir.

Um exemplo, que é o do próprio pedido: produto de R$ 2.000 com margem
líquida de R$ 400 aceita, a 30% da margem, no máximo **R$ 120** de desconto.
Isso são 6% do preço, e é exatamente esse descolamento que importa. Quem
raciocina em "porcentagem de desconto" acaba dando 30% do preço, R$ 600, que
é uma venda com R$ 200 de prejuízo.

Notas de implementação que não são estilo:

- **Arredonda pra baixo**, sempre. Meio centavo a mais é meio centavo de
  margem que não existia.
- **O valor nunca vem do modelo.** Ele pode pedir um desconto, não escolher
  quanto. Quem decide é esta função, a partir do preço e da categoria.
"""

import math
import secrets
import string
from typing import Optional

from app import config
from app.data import catalogo

# Cupom curto o bastante pra ser digitado sem erro e comprido o bastante pra
# não ser adivinhado. Sem vogais nem caracteres ambíguos (0/O, 1/I), que é o
# que gera "não funciona" no atendimento.
ALFABETO_DO_CODIGO = "".join(
    c for c in string.ascii_uppercase + string.digits if c not in "AEIOU01ILOS5"
)
TAMANHO_DO_CODIGO = 6
PREFIXO = "LU"


class DescontoInviavel(Exception):
    """A margem não comporta desconto que valha a pena oferecer."""


def desconto_maximo(produto: dict) -> float:
    """Maior desconto em reais que este produto aceita sem furar a margem."""
    margem = catalogo.margem_liquida(produto)
    teto = margem * config.PERCENTUAL_MAXIMO_DA_MARGEM
    # Trunca no centavo, pra baixo. `round` levaria meio centavo pra cima.
    return math.floor(teto * 100) / 100


def calcular(produto: dict, percentual_da_margem: Optional[float] = None) -> dict:
    """Monta a oferta pra um produto, já limitada pela margem.

    `percentual_da_margem` permite oferecer menos que o teto (começar por
    metade e guardar o resto pra uma segunda tentativa, por exemplo). Acima
    do teto configurado, é o teto que vale: este número nunca é ultrapassado,
    venha de onde vier.
    """
    fracao = min(
        percentual_da_margem or config.PERCENTUAL_MAXIMO_DA_MARGEM,
        config.PERCENTUAL_MAXIMO_DA_MARGEM,
    )
    margem = catalogo.margem_liquida(produto)
    valor = math.floor(margem * fracao * 100) / 100

    if valor < config.DESCONTO_MINIMO_RELEVANTE:
        raise DescontoInviavel(
            f"A margem de {produto['nome']} só comporta R$ {valor:.2f} de "
            f"desconto, abaixo do mínimo que faz diferença pro cliente."
        )

    preco_final = round(produto["preco"] - valor, 2)
    return {
        "produto_id": produto["id"],
        "produto_nome": produto["nome"],
        "preco_original": produto["preco"],
        "valor_desconto": valor,
        "preco_final": preco_final,
        # Percentual sobre o preço, que é o que o cliente enxerga. Costuma ser
        # um número pequeno, e é isso mesmo: o desconto é fatia da margem.
        "percentual_no_preco": round(valor / produto["preco"] * 100, 1),
        "margem_liquida": margem,
        "margem_restante": round(margem - valor, 2),
    }


def gerar_codigo() -> str:
    """Código aleatório e não sequencial.

    Sequencial deixaria qualquer cliente adivinhar o cupom do vizinho só
    somando um, e cupom adivinhado é desconto dado a quem não precisava.
    """
    sorteio = "".join(secrets.choice(ALFABETO_DO_CODIGO) for _ in range(TAMANHO_DO_CODIGO))
    return f"{PREFIXO}{sorteio}"


def valida_para_o_produto(cupom: dict, produto_id: int) -> bool:
    """Cupom vale pro produto que motivou a oferta, e só pra ele.

    Sem essa amarra, um desconto calculado sobre a margem gorda de um mouse
    seria usado num notebook, cuja margem não comporta o mesmo valor.
    """
    return cupom["produto_id"] == produto_id
