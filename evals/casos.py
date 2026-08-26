"""Casos de avaliação.

São dados, não testes: ficam separados do `tests/` porque rodam contra o
modelo de embedding real e contra a Groq, o que custa tempo e tokens.

As perguntas são escritas como um cliente falaria, com gíria, erro de
acento e contexto implícito. Perguntar usando as palavras do título do
documento mediria o óbvio e daria uma métrica inflada.
"""

# (pergunta, id do documento esperado)
RETRIEVAL = [
    ("meu quarto tem 12 metros quadrados e bate sol a tarde, qual aparelho gela?", 17),
    ("vale a pena pagar mais no ar condicionado que economiza energia?", 18),
    ("quero jogar jogos pesados no pc, o que importa na configuracao?", 3),
    ("to na duvida entre 8 e 16 de memoria pro notebook", 1),
    ("preciso guardar muito arquivo, quanto de espaco pegar?", 2),
    ("carrego o notebook todo dia no metro, qual tamanho compensa?", 4),
    ("celular de 108 megapixels tira foto melhor mesmo?", 5),
    ("meu celular nao dura o dia, o que olhar pra trocar?", 6),
    ("moro no interior, faz diferenca pegar 5g?", 7),
    ("meu sofa fica a 3 metros da parede, que polegada de tv?", 8),
    ("qual a diferenca de oled pra qled?", 9),
    ("comprei videogame novo, a tv precisa de algo especial?", 10),
    ("pego onibus lotado todo dia e queria abafar o barulho", 11),
    ("vou usar na academia, melhor com fio ou sem fio?", 12),
    ("essa caixa diz 300w mas parece fraca, como sei a potencia real?", 13),
    ("somos 4 em casa e fazemos compra do mes, que tamanho de geladeira?", 14),
    ("familia de 5 pessoas, quantos quilos de roupa a maquina precisa?", 15),
    ("somos so eu e minha esposa, que tamanho de fritadeira eletrica?", 16),
    ("quero esquentar marmita e fazer pipoca, que litragem serve?", 19),
    ("to reformando a cozinha, vale trocar gas por eletrico?", 20),
    ("jogo competitivo, o monitor precisa de quantos hertz?", 21),
    ("comprei um monitor de 27 e ficou serrilhado, por que?", 22),
    ("divido sala com minha esposa e ela reclama do barulho quando digito", 23),
    ("sinto dor no punho depois de horas no computador", 24),
    ("imprimo muito documento em preto, o que sai mais barato?", 25),
    ("trabalho sentado 8 horas e minhas costas doem", 26),
    ("somos casal e um acorda o outro quando se mexe na cama", 27),
    ("quero pedalar em trilha, que tipo de bike?", 28),
    ("quero aprender fotografia, ainda vale comprar camera?", 29),
    ("corro na rua e nao quero levar o celular, que relogio?", 30),
    ("vale a pena o console mais barato que nao tem leitor?", 31),
    ("quero fazer sopa e purê batendo direto na panela", 32),
    ("tomo muito cafe e quero economizar no longo prazo", 33),
    ("tenho cachorro e cai muito pelo em casa", 34),
    ("posso trocar meu notebook por um tablet pra faculdade?", 35),
    ("meu ar condicionado nao da conta, o que ajuda a espalhar o frio?", 36),
    ("minha sala e pequena, que tamanho de sofa cabe?", 37),
    ("mudei de cidade e a tomada e diferente, e perigoso?", 38),
    ("qual selo indica que o aparelho gasta menos luz?", 39),
    ("comprei pela internet e me arrependi, posso devolver?", 40),
    # Escritos depois do enriquecimento dos documentos, pra checar se a
    # melhora foi generalização e não memorização das perguntas indexadas.
    ("meu apartamento e 220 e comprei um aparelho 110, o que faco?", 38),
    ("quero um teclado que nao acorde minha esposa de madrugada", 23),
    ("a fritadeira de 3 litros da pra 4 pessoas?", 16),
    ("jogos modernos rodam com video integrado?", 3),
    ("quantos btu pra um escritorio de 25 metros?", 17),
    ("queria abafar o som do aviao numa viagem longa", 11),
    ("gasto muito com capsula de cafe, tem alternativa?", 33),
    ("minha impressora fica meses sem uso e entope", 25),
    ("que bike comprar pra crianca de 6 anos?", 28),
    ("tenho pouco espaco na cozinha, que micro-ondas?", 19),
    ("quero assistir netflix num quarto pequeno, que polegada?", 8),
    ("preciso medir batimento cardiaco durante a corrida", 30),
]

# Perguntas fora do domínio: a base não cobre, então o esperado é não
# devolver nada. Mede se o piso de score segura ruído.
RETRIEVAL_FORA_DE_ESCOPO = [
    "qual a capital da Franca?",
    "me conte uma piada",
    "qual foi o resultado do jogo do Corinthians ontem?",
    "quem descobriu o Brasil?",
    "como faco bolo de cenoura?",
    "vai chover amanha?",
    "quanto e 2 mais 2?",
    "me indica um filme pra assistir hoje",
]

# (mensagem do cliente, ferramentas aceitáveis como primeira escolha)
#
# Aceita um conjunto porque em vários casos há mais de uma abordagem
# defensável: pra "qual a melhor tv" tanto sugerir quanto comparar
# resolvem. O erro que importa pegar é a Lu responder de cabeça, sem
# chamar ferramenta nenhuma, ou buscar produto quando devia buscar
# conhecimento.
FERRAMENTAS = [
    ("o que voces vendem?", {"listar_categorias", "buscar_produtos"}),
    ("tem notebook ai?", {"buscar_produtos"}),
    ("quanto custa o Notebook Titan X15?", {"buscar_produtos"}),
    ("o produto 3 tem em estoque?", {"consultar_estoque", "buscar_produtos"}),
    ("qual a melhor air fryer de voces?", {"sugerir_produto", "comparar_produtos", "buscar_produtos"}),
    ("me ajuda a comparar os monitores", {"comparar_produtos", "buscar_produtos"}),
    ("quero o celular mais barato", {"sugerir_produto", "buscar_produtos"}),
    ("quantos BTUs eu preciso pra um quarto de 12m2?", {"buscar_conhecimento"}),
    ("o que significa frost free?", {"buscar_conhecimento"}),
    ("qual a diferenca entre oled e qled?", {"buscar_conhecimento"}),
    ("trabalho sentado o dia todo e minhas costas doem, o que voce indica?", {"buscar_conhecimento", "sugerir_produto", "buscar_produtos"}),
    ("8 ou 16 de ram pra faculdade?", {"buscar_conhecimento"}),
    # Com endereço de propósito: sem ele, a persona manda perguntar antes de
    # agir, então não chamar ferramenta seria o comportamento correto e o
    # caso não mediria nada.
    ("quero comprar o produto 1, entregar na Rua das Flores 100", {"criar_pedido", "consultar_estoque", "buscar_produtos"}),
    ("cade meu pedido 1?", {"rastrear_pedido", "consultar_pedido"}),
    ("quero ver os dados do pedido 2", {"consultar_pedido"}),
    ("preciso da segunda via do boleto do pedido 1", {"gerar_segunda_via"}),
    ("me manda a nota fiscal do pedido 3", {"gerar_segunda_via"}),
    ("quero receber o pedido 1 no dia 2026-09-10", {"agendar_entrega"}),
]

# A lista acima é **linha de base histórica e está congelada**. Ela é o que
# sustenta o número registrado como invariante no MELHORIAS.md, e cada caso
# é uma chamada independente ao modelo (persona + schemas + uma mensagem),
# sem estado entre eles. Por isso acrescentar caso numa lista nova não muda
# em nada o resultado desses 18, e por isso mexer num destes mata a
# comparação com toda medição anterior. Caso novo vai nas listas abaixo.

# Ferramentas que entraram depois da última medição e nunca passaram pela
# régua. Vocabulário de cliente de propósito, sem repetir o verbo da
# descrição da ferramenta ("anota aí", "salva meu dado", "registra minha
# satisfação"): copiar a descrição infla a métrica do mesmo jeito que usar o
# título do documento inflava o retrieval.
FERRAMENTAS_COBERTURA = [
    ("pode me chamar de Rafael, e agora moro na Rua Verbo Divino 200", {"salvar_dado_do_cliente"}),
    ("meu limite mesmo e 2 mil, mais que isso nao da", {"anotar_da_conversa"}),
    ("nota 5 pra vc, me ajudou demais hoje", {"registrar_satisfacao"}),
]

# Ferramenta que NÃO pode ser chamada nestas situações.
#
# `oferecer_cupom` entra aqui como caso negativo, e não como caso positivo,
# porque o harness manda uma mensagem sem histórico: nenhuma frase consegue
# expressar "sumiu há oito horas depois de olhar um produto", que é a única
# condição em que a ferramenta deveria disparar. Um caso positivo mediria a
# disposição do modelo de chamar algo que `services.oferecer_cupom` vai
# recusar, ou seja, exatamente o comportamento que não queremos.
#
# A cobertura positiva dela existe onde deve, em `tests/test_cupom.py`, que
# controla o relógio. Aqui o que vale medir é o inverso: pedir desconto não
# pode fazer a Lu sacar a ferramenta.
FERRAMENTAS_PROIBIDAS = [
    ("faz um desconto ai pra mim? ta caro esse preco", {"oferecer_cupom"}),
    ("vou pensar melhor e depois eu volto", {"oferecer_cupom"}),
]


def ferramentas_sem_caso(declaradas) -> set:
    """Ferramentas expostas ao modelo que nenhum caso de avaliação cobre.

    Existe pra que o descompasso apareça sozinho. Foi assim que três
    ferramentas entraram no manual sem régua nenhuma: nada apontava a
    diferença entre o que o modelo enxerga e o que a avaliação mede.
    """
    cobertas = set()
    for _, aceitaveis in list(FERRAMENTAS) + list(FERRAMENTAS_COBERTURA):
        cobertas |= aceitaveis
    for _, proibidas in FERRAMENTAS_PROIBIDAS:
        cobertas |= proibidas
    return set(declaradas) - cobertas


# Mensagens que NÃO deveriam disparar ferramenta: são conversa, não
# consulta. Chamar ferramenta aqui é desperdício de tempo e token.
FERRAMENTAS_SEM_CHAMADA = [
    "oi, tudo bem?",
    "obrigado, era so isso!",
    "bom dia",
]
