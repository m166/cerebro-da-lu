"""Ferramentas expostas ao modelo (function calling).

`TOOL_SCHEMAS` descreve as ferramentas no formato Groq/OpenAI.
`executar(nome, args)` chama o service correspondente e converte erros de
domínio em `{"erro": ...}`, o modelo lida melhor com isso do que com
exceção.
"""

import json
from typing import Any, Dict, List

from app import config, exceptions, models, services


def _opcional(tipo: str, descricao: str, **extra) -> Dict[str, Any]:
    """Parâmetro opcional que também aceita null.

    O modelo costuma preencher opcional que não vai usar com `null`, e a
    Groq valida o argumento contra o schema antes de entregar: sem aceitar
    null aqui, a chamada volta como erro 400 e o chat quebra.
    """
    return {"type": [tipo, "null"], "description": descricao, **extra}


TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "buscar_produtos",
            "description": (
                "Busca produtos no catálogo por texto livre e/ou categoria. É a "
                "ferramenta padrão quando o cliente cita um tipo de produto "
                "('tem notebook?', 'quero um fone'): chame direto, sem listar "
                "categorias antes. O catálogo tem mais de 100 produtos, então a "
                "busca devolve só os primeiros resultados junto com o total."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": _opcional("string", "Termo de busca livre, ex: 'notebook gamer'."),
                    "categoria": _opcional(
                        "string",
                        "Categoria exata. Opções: " + ", ".join(services.listar_categorias()),
                    ),
                    "limite": _opcional("integer", "Quantos produtos devolver. Padrão 10, máximo 30."),
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_categorias",
            "description": (
                "Lista as categorias do catálogo. Use APENAS quando o cliente "
                "perguntar de forma aberta o que a loja vende. Se ele já citou um "
                "tipo de produto, vá direto pra buscar_produtos, sugerir_produto "
                "ou comparar_produtos."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_conhecimento",
            "description": (
                "Consulta a base de conhecimento sobre tecnologia e categorias de produto: "
                "o que cada especificação significa e o que olhar na hora de escolher "
                "(quanta RAM, quantos BTUs, litragem de geladeira, tipo de switch de teclado etc.). "
                "Use SEMPRE que o cliente perguntar 'qual é melhor pra mim', 'o que significa X' "
                "ou descrever uma necessidade em vez de um produto, é o que permite explicar o "
                "porquê da recomendação em vez de só comparar números do catálogo."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pergunta": {
                        "type": "string",
                        "description": "A dúvida ou necessidade do cliente, em linguagem natural.",
                    },
                    "categoria": _opcional(
                        "string", "Restringe a busca a uma categoria do catálogo (opcional)."
                    ),
                },
                "required": ["pergunta"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_estoque",
            "description": "Consulta se um produto tem estoque disponível.",
            "parameters": {
                "type": "object",
                "properties": {"produto_id": {"type": "integer", "description": "ID do produto."}},
                "required": ["produto_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sugerir_produto",
            "description": (
                "Sugere o melhor produto pra necessidade do cliente, combinando "
                "preço, prazo de entrega e avaliação (ou um critério específico). "
                "Use quando o cliente pedir 'o melhor', 'o mais barato' ou 'o que "
                "você indica' de um tipo de produto, chame direto com a categoria, "
                "sem listar categorias antes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "categoria": _opcional("string", "Categoria pra restringir a busca."),
                    "criterio": _opcional(
                        "string",
                        "Critério de escolha. Padrão: melhor_custo_beneficio.",
                        enum=list(models.CRITERIOS_SUGESTAO) + [None],
                    ),
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "comparar_produtos",
            "description": (
                "Compara produtos lado a lado e diz quem ganha em preço, prazo, "
                "avaliação e custo-benefício. Use quando o cliente pedir pra "
                "comparar ou estiver decidindo entre opções de uma mesma "
                "categoria, chame direto com a categoria, sem listar antes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "categoria": _opcional("string", "Compara todos os produtos da categoria."),
                    "produto_ids": _opcional(
                        "array",
                        "IDs específicos pra comparar (alternativa à categoria).",
                        items={"type": "integer"},
                    ),
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "criar_pedido",
            "description": "Cria um novo pedido pra um produto do catálogo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "produto_id": {"type": "integer", "description": "ID do produto."},
                    "quantidade": _opcional("integer", "Quantidade desejada. Padrão: 1."),
                    "endereco_entrega": _opcional(
                        "string", "Endereço de entrega informado pelo cliente."
                    ),
                },
                "required": ["produto_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_pedido",
            "description": "Consulta os dados de um pedido existente (status, itens, valor).",
            "parameters": {
                "type": "object",
                "properties": {"pedido_id": {"type": "integer", "description": "ID do pedido."}},
                "required": ["pedido_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rastrear_pedido",
            "description": (
                "Rastreia um pedido: código de rastreio, etapa atual e "
                "localização. Passe o código pro cliente sempre que ele "
                "perguntar onde está o pedido."
            ),
            "parameters": {
                "type": "object",
                "properties": {"pedido_id": {"type": "integer", "description": "ID do pedido."}},
                "required": ["pedido_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "agendar_entrega",
            "description": "Agenda a entrega de um pedido pra uma data específica.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pedido_id": {"type": "integer", "description": "ID do pedido."},
                    "data_entrega": {"type": "string", "description": "Data desejada, formato YYYY-MM-DD."},
                },
                "required": ["pedido_id", "data_entrega"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gerar_segunda_via",
            "description": "Gera a 2ª via de boleto ou nota fiscal de um pedido.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pedido_id": {"type": "integer", "description": "ID do pedido."},
                    "tipo": _opcional(
                        "string", "Tipo de documento.", enum=["boleto", "nf", None]
                    ),
                },
                "required": ["pedido_id"],
            },
        },
    },
]


def _buscar_produtos(query: str = "", categoria: str = "", limite: int = config.LIMITE_BUSCA_TOOL) -> dict:
    encontrados = services.buscar_produtos(query=query, categoria=categoria)
    limite = max(1, min(int(limite), 30))
    return {
        "total_encontrado": len(encontrados),
        "mostrando": len(encontrados[:limite]),
        "produtos": encontrados[:limite],
    }


DISPATCH = {
    "buscar_produtos": _buscar_produtos,
    "buscar_conhecimento": services.buscar_conhecimento,
    "listar_categorias": lambda: {"categorias": services.listar_categorias()},
    "consultar_estoque": services.consultar_estoque,
    "sugerir_produto": services.sugerir_produto,
    "comparar_produtos": services.comparar_produtos,
    "criar_pedido": services.criar_pedido,
    "consultar_pedido": services.obter_pedido,
    "rastrear_pedido": services.rastrear_pedido,
    "agendar_entrega": services.agendar_entrega,
    "gerar_segunda_via": services.gerar_segunda_via,
}


def executar(nome: str, args: dict) -> dict:
    """Executa uma ferramenta, devolvendo sempre um dict serializável."""
    func = DISPATCH.get(nome)
    if func is None:
        return {"erro": f"Ferramenta desconhecida: {nome}"}

    # O modelo preenche opcional que não vai usar com null; descartar aqui
    # faz o service cair no default dele em vez de receber None.
    args = {chave: valor for chave, valor in args.items() if valor is not None}

    try:
        return func(**args)
    except exceptions.ErroDeDominio as exc:
        return {"erro": str(exc)}
    except TypeError as exc:
        return {"erro": f"Argumentos inválidos pra {nome}: {exc}"}


def executar_json(nome: str, argumentos_json: str) -> str:
    args = json.loads(argumentos_json or "{}")
    return json.dumps(executar(nome, args), ensure_ascii=False)
