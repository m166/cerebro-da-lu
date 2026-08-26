"""Ilustração de cada produto, gerada a partir da forma da categoria.

Dois notebooks do catálogo têm o mesmo desenho, mas não a mesma cor: o tom
sai do id do produto, então cada item fica visualmente distinto sem exigir
uma arte por item. É desenho porque o catálogo é mockado e não existe foto.

Trocar por foto real não passa por aqui: basta `produto["imagem"]` apontar
pra URL da foto, e este módulo deixa de ser chamado.
"""

import colorsys

from app.data.ilustracoes import FORMAS

# Uma volta inteira no círculo de cores dividida por um número que não tem
# fator comum com 360: ids seguidos caem em tons bem separados em vez de
# variarem de leve.
PASSO_DE_MATIZ = 47


def _hex(r: float, g: float, b: float) -> str:
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def _paleta(categoria: str, produto_id: int):
    """Fundo escuro e acento claro, variando o matiz por produto.

    Parte da cor da categoria pra que a família continue reconhecível: as
    geladeiras seguem azuladas, mas cada modelo tem o seu tom.
    """
    fundo_base, acento_base, _ = FORMAS[categoria]
    matiz_base, _, _ = colorsys.rgb_to_hls(
        *(int(fundo_base[i : i + 2], 16) / 255 for i in (1, 3, 5))
    )

    matiz = (matiz_base + (produto_id * PASSO_DE_MATIZ % 360) / 360 * 0.28) % 1.0
    fundo = _hex(*colorsys.hls_to_rgb(matiz, 0.30, 0.55))
    acento = _hex(*colorsys.hls_to_rgb(matiz, 0.68, 0.72))
    return fundo, acento


def svg_do_produto(produto: dict) -> str:
    categoria = produto["categoria"]
    if categoria not in FORMAS:
        raise KeyError(categoria)

    fundo, acento = _paleta(categoria, produto["id"])
    corpo = FORMAS[categoria][2].format(acento=acento)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" role="img" '
        f'aria-label="{produto["nome"]}">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{fundo}"/>'
        f'<stop offset="1" stop-color="{acento}" stop-opacity=".55"/>'
        "</linearGradient></defs>"
        '<rect width="120" height="120" rx="16" fill="url(#g)"/>'
        f"{corpo}</svg>"
    )
