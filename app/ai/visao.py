"""Leitura de imagem enviada pelo cliente.

Serve pra ele fotografar um produto e perguntar se a loja tem. O modelo de
conversa (`GROQ_MODEL`) não aceita imagem, então a foto passa antes por um
modelo com visão, que devolve em texto o que está vendo. Esse texto entra
na conversa como contexto, e daí pra frente o fluxo é o de sempre, com as
mesmas ferramentas de catálogo.

Separar em duas etapas foi de propósito: trocar o modelo principal por um
multimodal mexeria na escolha de ferramenta, que hoje acerta 100% na
avaliação, e não há motivo pra arriscar isso por causa da foto.
"""

import base64
import re
from typing import Optional

from groq import RateLimitError

from app import config
from app.ai.client import get_client

# O modelo raciocina antes de responder. A Groq consegue esconder isso no
# servidor (`reasoning_format`), que é o caminho certo. A limpeza por texto
# fica como rede de segurança pra outro modelo que não aceite o parâmetro,
# e cobre também a tag que ficou aberta por falta de espaço, caso em que um
# filtro de bloco fechado deixaria o pensamento inteiro vazar pro cliente.
_RACIOCINIO = re.compile(r"<think>.*?</think>", re.S)
_RACIOCINIO_ABERTO = re.compile(r"<think>.*", re.S)

INSTRUCAO = (
    "Um cliente de loja online mandou esta imagem pra saber se a loja vende "
    "algo parecido. Diga em uma frase curta, em português, que tipo de "
    "produto aparece, com a cor ou o tamanho se der pra ver.\n"
    "Vale qualquer imagem: foto, captura de tela de um anúncio, desenho ou "
    "ícone. O que importa é o tipo de produto representado, não se a imagem "
    "é uma fotografia de verdade.\n"
    "Não invente marca nem modelo. Responda exatamente 'nenhum produto "
    "reconhecível' apenas quando não houver objeto algum que possa ser "
    "vendido numa loja."
)

SEM_PRODUTO = "nenhum produto reconhecível"


class ImagemNaoLida(Exception):
    """Não deu pra descrever a imagem, e a conversa segue sem ela."""


def _limpar(resposta: Optional[str]) -> str:
    texto = _RACIOCINIO.sub("", resposta or "")
    return _RACIOCINIO_ABERTO.sub("", texto).strip()


def descrever(imagem: bytes, mime: str = "image/jpeg", tentativas: int = 2) -> str:
    """Devolve, em uma frase, o produto que aparece na foto.

    Tenta mais de uma vez porque o modelo às vezes gasta todo o espaço
    raciocinando e devolve conteúdo vazio. É intermitente, e recusar a foto
    de primeira por isso seria injusto com quem mandou uma foto boa.
    """
    if not imagem:
        raise ImagemNaoLida("Imagem vazia.")
    if len(imagem) > config.TAMANHO_MAXIMO_IMAGEM:
        raise ImagemNaoLida(
            f"Imagem maior que {config.TAMANHO_MAXIMO_IMAGEM // (1024 * 1024)}MB."
        )

    dados = base64.b64encode(imagem).decode()
    for tentativa in range(tentativas):
        descricao = _uma_tentativa(dados, mime)
        if descricao:
            return descricao
    raise ImagemNaoLida("O modelo não descreveu a imagem.")


def _uma_tentativa(dados: str, mime: str) -> str:
    try:
        completion = get_client().chat.completions.create(
            model=config.GROQ_MODEL_VISAO,
            # Folga pro raciocínio: com pouco espaço ele gasta tudo pensando
            # e devolve a resposta cortada no meio.
            max_tokens=config.MAX_TOKENS_VISAO,
            reasoning_format="hidden",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": INSTRUCAO},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{dados}"},
                        },
                    ],
                }
            ],
        )
    except RateLimitError as exc:
        raise ImagemNaoLida("A conta da Groq atingiu o limite de uso.") from exc
    except Exception as exc:
        raise ImagemNaoLida(f"Não consegui ler a imagem: {exc}") from exc

    return _limpar(completion.choices[0].message.content)


def reconheceu_produto(descricao: str) -> bool:
    return SEM_PRODUTO not in descricao.lower()
