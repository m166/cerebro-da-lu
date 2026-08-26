"""Regras de negócio.

Os services validam, calculam e orquestram os repositories. Quando algo
não faz sentido no domínio, levantam uma exceção de `app.exceptions`, quem
chama decide como apresentar (HTTP ou mensagem pro modelo).
"""

from datetime import date, datetime, timedelta, timezone
from typing import Callable, List, Optional

from app import (
    abandono,
    config,
    cupom,
    exceptions,
    models,
    pistas,
    repositories,
    sessao,
    telefone,
    whatsapp,
)


# --- Catálogo -------------------------------------------------------------

def buscar_produtos(query: str = "", categoria: str = "", limite: Optional[int] = None) -> List[dict]:
    return repositories.listar_produtos(query=query, categoria=categoria, limite=limite)


def obter_produto(produto_id: int) -> dict:
    produto = repositories.obter_produto(produto_id)
    if produto is None:
        raise exceptions.ProdutoNaoEncontrado(produto_id)
    return produto


def listar_categorias() -> List[str]:
    return repositories.listar_categorias()


def consultar_estoque(produto_id: int) -> dict:
    produto = obter_produto(produto_id)
    return {
        "produto_id": produto_id,
        "nome": produto["nome"],
        "estoque": produto["estoque"],
        "disponivel": produto["estoque"] > 0,
    }


# --- Base de conhecimento (RAG) -------------------------------------------

def buscar_conhecimento(pergunta: str, categoria: str = "", limite: Optional[int] = None) -> dict:
    """Busca semântica na base de conhecimento sobre tecnologia.

    Descarta resultado com similaridade baixa: é melhor a Lu admitir que
    não sabe do que fundamentar a recomendação num trecho irrelevante.
    """
    encontrados = repositories.buscar_conhecimento(
        pergunta, k=limite or config.LIMITE_CONHECIMENTO, categoria=categoria
    )
    relevantes = [
        d
        for d in encontrados
        if d["score"] >= config.SCORE_MINIMO_CONHECIMENTO
        or d["score_lexical"] >= config.SCORE_LEXICAL_MINIMO
    ]

    if not relevantes:
        # O buraco da base, registrado no instante em que aparece. É o sinal
        # mais barato de coletar e o mais acionável que existe aqui: vira uma
        # fila de documentos a escrever, priorizada por quantas pessoas
        # perguntaram de verdade em vez de por palpite de quem edita o corpus.
        repositories.registrar_evento(
            models.EVENTO_RAG_SEM_RESPOSTA,
            {
                "pergunta": pergunta,
                "categoria": categoria or None,
                # O melhor score que mesmo assim não passou, pra distinguir
                # "quase achou" de "não existe nada parecido na base".
                "melhor_score": round(max((d["score"] for d in encontrados), default=0), 3),
            },
        )

    return {
        "pergunta": pergunta,
        "encontrou": bool(relevantes),
        "trechos": [
            {
                "titulo": d["titulo"],
                "categoria": d["categoria"],
                "texto": d["texto"],
                "score": round(d["score"], 3),
            }
            for d in relevantes
        ],
    }


# --- Sugestão e comparação -------------------------------------------------

def _score_custo_beneficio(candidatos: List[dict]) -> Callable[[dict], float]:
    """Score normalizado dentro do conjunto avaliado.

    A normalização é relativa aos candidatos, comparar um mouse com um
    notebook não faria sentido, então o score só é significativo dentro de
    uma mesma categoria.
    """
    precos = [p["preco"] for p in candidatos]
    prazos = [p["prazo_entrega_dias"] for p in candidatos]
    min_preco, max_preco = min(precos), max(precos)
    min_prazo, max_prazo = min(prazos), max(prazos)

    def score(p: dict) -> float:
        preco_norm = 0.0 if max_preco == min_preco else (p["preco"] - min_preco) / (max_preco - min_preco)
        prazo_norm = 0.0 if max_prazo == min_prazo else (p["prazo_entrega_dias"] - min_prazo) / (max_prazo - min_prazo)
        avaliacao_norm = p["avaliacao"] / 5.0
        # preço e prazo menores são melhores, avaliação maior é melhor
        return (1 - preco_norm) * 0.4 + (1 - prazo_norm) * 0.2 + avaliacao_norm * 0.4

    return score


def _escolher(candidatos: List[dict], criterio: str) -> dict:
    if criterio == "melhor_preco":
        return min(candidatos, key=lambda p: p["preco"])
    if criterio == "melhor_prazo":
        return min(candidatos, key=lambda p: p["prazo_entrega_dias"])
    if criterio == "melhor_avaliacao":
        return max(candidatos, key=lambda p: p["avaliacao"])
    return max(candidatos, key=_score_custo_beneficio(candidatos))


def sugerir_produto(categoria: str = "", criterio: str = "melhor_custo_beneficio") -> dict:
    """Sugere o melhor produto de uma categoria (ou de todo o catálogo)."""
    candidatos = [p for p in repositories.listar_produtos(categoria=categoria) if p["estoque"] > 0]
    if not candidatos:
        raise exceptions.SemProdutosDisponiveis()

    return {"criterio": criterio, "produto": _escolher(candidatos, criterio)}


def comparar_produtos(categoria: str = "", produto_ids: Optional[List[int]] = None) -> dict:
    """Compara produtos lado a lado, apontando quem ganha em cada critério."""
    if produto_ids:
        candidatos = [p for p in (repositories.obter_produto(i) for i in produto_ids) if p is not None]
    else:
        candidatos = repositories.listar_produtos(categoria=categoria)

    if len(candidatos) < 2:
        raise exceptions.ComparacaoInvalida()

    return {
        "produtos": candidatos,
        "melhor_preco": _escolher(candidatos, "melhor_preco")["nome"],
        "melhor_prazo": _escolher(candidatos, "melhor_prazo")["nome"],
        "melhor_avaliacao": _escolher(candidatos, "melhor_avaliacao")["nome"],
        "melhor_custo_beneficio": _escolher(candidatos, "melhor_custo_beneficio")["nome"],
    }


# --- Cadastro do cliente ---------------------------------------------------

def telefone_do_cliente() -> Optional[str]:
    """O número de quem está falando, quando a conversa veio pelo canal.

    Vem da sessão, não do cadastro: no WhatsApp o número é o remetente da
    mensagem, e ninguém digita o próprio. Fora de uma requisição a sessão é
    `local`, que não é telefone, e aí não há número a informar.
    """
    atual = sessao.atual()
    return atual if telefone.valido(atual) else None


def dados_do_cliente() -> dict:
    """O que a Lu já sabe sobre quem está conversando.

    O endereço cai pro último pedido quando ainda não foi cadastrado, pra
    que quem já comprou antes desta funcionalidade não precise repetir.
    """
    perfil = repositories.obter_perfil()
    if not perfil.get("endereco"):
        ultimo = repositories.endereco_do_ultimo_pedido()
        if ultimo:
            perfil["endereco"] = ultimo

    dados = {}
    numero = telefone_do_cliente()
    if numero:
        dados["telefone"] = telefone.formatar(numero)
    dados.update(
        {campo: perfil.get(campo) for campo in models.CAMPOS_PERFIL if perfil.get(campo)}
    )
    return dados


def salvar_dado_do_cliente(campo: str, valor: str) -> dict:
    # `telefone` não está em CAMPOS_PERFIL de propósito: ele vem do canal, e
    # deixar o modelo gravar por cima abriria a porta pra um cliente assumir
    # o número (e o histórico) de outro só dizendo que mudou de celular.
    if campo not in models.CAMPOS_PERFIL:
        raise exceptions.CampoDePerfilInvalido(campo, models.CAMPOS_PERFIL)
    if not valor or not valor.strip():
        raise exceptions.CampoDePerfilInvalido(campo, models.CAMPOS_PERFIL)

    repositories.salvar_perfil(campo, valor.strip())
    return dados_do_cliente()


# --- Memória da conversa ---------------------------------------------------

def anotar_da_conversa(campo: str, valor: str) -> dict:
    """Guarda algo que o cliente revelou e que a janela de histórico apagaria.

    Separado de `salvar_dado_do_cliente` porque a validade é outra: nome e
    endereço valem daqui a meses, orçamento e recusa valem pra esta compra.
    """
    if campo not in models.CAMPOS_MEMORIA:
        raise exceptions.CampoDeMemoriaInvalido(campo, models.CAMPOS_MEMORIA)
    if not valor or not valor.strip():
        raise exceptions.CampoDeMemoriaInvalido(campo, models.CAMPOS_MEMORIA)

    repositories.salvar_memoria(campo, valor.strip())
    return memoria_da_conversa()


def memoria_da_conversa() -> dict:
    """O que a Lu precisa ter em vista, já resolvido, sem depender da janela.

    Combina três origens, e a ordem entre elas foi decidida por medição:

    - **Lido do texto** (`pistas`), pro orçamento e pras recusas. Ganha do
      que o modelo anotou porque é sempre a fala mais recente: ele só chama
      a ferramenta quando a mensagem não disputa com uma busca, então a
      anotação envelhece sem avisar.
    - **Derivado do banco**, pros produtos já mostrados. O dado já existe em
      `messages.produtos`, e derivar não depende de ninguém lembrar.
    - **Anotado pelo modelo**, pro resto (a finalidade da compra, que nenhum
      padrão de texto pega) e como reserva quando a leitura não achou nada.
    """
    anotado = repositories.obter_memoria()
    lembrado = {
        campo: anotado[campo] for campo in models.CAMPOS_MEMORIA if anotado.get(campo)
    }

    falas = [m["content"] for m in repositories.listar_mensagens() if m["role"] == "user"]

    lido = pistas.orcamento(falas)
    if lido:
        lembrado["orcamento"] = lido

    produtos = [
        produto
        for produto in (
            repositories.obter_produto(pid) for pid in repositories.produtos_ja_citados()
        )
        if produto
    ]

    recusados = pistas.recusas(
        falas, produtos, [p["nome"] for p in repositories.listar_produtos()]
    )
    if recusados:
        # O que o modelo anotou entra junto: ele pega recusa de marca e de
        # categoria ("não quero nada da Samsung"), que não casa com nome de
        # produto nenhum e escaparia da leitura.
        anteriores = [p.strip() for p in lembrado.get("recusou", "").split(",") if p.strip()]
        for nome in recusados:
            if nome not in anteriores:
                anteriores.append(nome)
        lembrado["recusou"] = ", ".join(anteriores)

    if produtos:
        lembrado["ja_sugeridos"] = ", ".join(p["nome"] for p in produtos)
    return lembrado


# --- Abandono e cupom de recuperação ---------------------------------------

def situacao_da_conversa(agora: Optional[datetime] = None) -> dict:
    """Se o cliente parece ter desistido da compra, e por quê.

    Junta os três fatos que a decisão precisa: quando ele falou, se chegou a
    demonstrar interesse em algum produto, e se já fechou pedido.
    """
    return abandono.avaliar(
        momentos_do_cliente=repositories.momentos_do_cliente(),
        demonstrou_interesse=bool(repositories.produtos_ja_citados(limite=1)),
        ja_comprou=bool(repositories.listar_pedidos()),
        agora=agora,
    )


def oferecer_cupom(produto_id: int, agora: Optional[datetime] = None) -> dict:
    """Emite um cupom, **se e somente se** o cliente estiver desistindo.

    A trava mora aqui e não na persona, e isso é deliberado. Este projeto já
    mediu duas vezes que o modelo ignora instrução quando está ocupado com
    outra coisa: foi assim com o tom e com `anotar_da_conversa`. Uma regra
    que custa dinheiro não pode depender de o modelo lembrar dela, então a
    ferramenta pergunta e a resposta pode ser não.

    O valor também não vem do modelo: quem calcula é `cupom.calcular`, a
    partir da margem do produto. Ele decide *se pede*, nunca *quanto*.
    """
    situacao = situacao_da_conversa(agora)
    if not situacao["abandonou"]:
        raise exceptions.CupomAindaNaoCabe(situacao["motivo"])

    ja_emitidos = repositories.cupons_da_sessao()
    if len(ja_emitidos) >= config.MAX_CUPONS_POR_SESSAO:
        raise exceptions.CupomAindaNaoCabe(
            f"esta conversa já recebeu {len(ja_emitidos)} cupons, que é o limite"
        )
    if any(c["produto_id"] == produto_id and not c["usado_em"] for c in ja_emitidos):
        raise exceptions.CupomAindaNaoCabe(
            "já existe um cupom aberto pra este produto nesta conversa"
        )

    produto = obter_produto(produto_id)
    oferta = cupom.calcular(produto)

    codigo = cupom.gerar_codigo()
    expira = (agora or datetime.now(timezone.utc)) + timedelta(
        hours=config.VALIDADE_CUPOM_HORAS
    )
    repositories.salvar_cupom(
        codigo=codigo,
        produto_id=produto_id,
        valor_desconto=oferta["valor_desconto"],
        margem_na_emissao=oferta["margem_liquida"],
        expira_em=expira,
        motivo=situacao["motivo"],
    )
    repositories.registrar_evento(
        models.EVENTO_CUPOM_OFERECIDO,
        {
            "produto_id": produto_id,
            "valor": oferta["valor_desconto"],
            "motivo": situacao["motivo"],
        },
    )

    return {
        **oferta,
        "codigo": codigo,
        "expira_em": expira.strftime("%d/%m às %Hh"),
        "motivo_da_oferta": situacao["motivo"],
    }


def validar_cupom(codigo: str, produto_id: int) -> dict:
    """Confere se o cupom vale, sem consumir. Serve pra mostrar o preço."""
    registro = repositories.obter_cupom(codigo)
    if registro is None:
        raise exceptions.CupomInvalido("não encontrei esse código nesta conversa")
    if registro["usado_em"]:
        raise exceptions.CupomInvalido("esse cupom já foi usado")
    if not cupom.valida_para_o_produto(registro, produto_id):
        raise exceptions.CupomInvalido(
            "esse cupom foi criado pra outro produto e o desconto não se transfere"
        )

    expira = _para_datetime(registro["expira_em"])
    if expira and expira < datetime.utcnow():
        raise exceptions.CupomInvalido("esse cupom expirou")
    return registro


# --- Satisfação e diagnóstico ----------------------------------------------

def registrar_satisfacao(nota: int, comentario: str = "", assunto: str = "") -> dict:
    if not models.NOTA_MINIMA <= nota <= models.NOTA_MAXIMA:
        raise exceptions.NotaInvalida(nota, models.NOTA_MINIMA, models.NOTA_MAXIMA)
    repositories.registrar_satisfacao(nota, comentario, assunto)
    return {"registrado": True, "nota": nota}


def diagnostico(limite: int = 10) -> dict:
    """O que o sistema está errando, em ordem de impacto.

    Não corrige nada sozinho, e isso é escolha. Mudança automática de
    comportamento precisa de um jeito de detectar que piorou, e aqui a régua
    (a pasta `evals/`) roda sob demanda, não continuamente. O sistema aponta,
    o humano decide, e a aplicação passa pelo eval.

    A prioridade é por frequência, porque perguntar "o que mais atrapalha
    mais gente" é a única ordenação que se sustenta sem opinião.
    """
    perguntas = repositories.perguntas_sem_resposta(limite)
    satisfacao = repositories.resumo_da_satisfacao()

    acoes = []
    if perguntas:
        acoes.append(
            {
                "prioridade": "alta" if perguntas[0]["vezes"] >= 3 else "média",
                "onde": "base de conhecimento",
                "o_que_fazer": (
                    f"Escrever documento sobre \"{perguntas[0]['pergunta']}\", "
                    f"perguntado {perguntas[0]['vezes']} vez(es) sem resposta."
                ),
            }
        )
    abandonos = repositories.contar_eventos(models.EVENTO_ABANDONO)
    ofertados = repositories.contar_eventos(models.EVENTO_CUPOM_OFERECIDO)
    usados = repositories.contar_eventos(models.EVENTO_CUPOM_USADO)
    if ofertados and usados / ofertados < 0.2:
        acoes.append(
            {
                "prioridade": "média",
                "onde": "cupom",
                "o_que_fazer": (
                    f"Só {usados} de {ofertados} cupons converteram. Revisar o "
                    "gatilho de abandono ou o tamanho do desconto."
                ),
            }
        )
    if satisfacao.get("insatisfeitos"):
        acoes.append(
            {
                "prioridade": "alta",
                "onde": "atendimento",
                "o_que_fazer": (
                    f"{satisfacao['insatisfeitos']} avaliação(ões) nota 1 ou 2. "
                    "Ler os comentários em `notas_baixas`."
                ),
            }
        )

    return {
        "satisfacao": satisfacao,
        "reclamacoes": repositories.notas_baixas(limite),
        "perguntas_sem_resposta": perguntas,
        "abandonos": abandonos,
        "cupons": {"oferecidos": ofertados, "usados": usados},
        "acoes_sugeridas": acoes,
    }


# --- Rastreio: código e progressão de status ------------------------------

def _digito_verificador(serie: str) -> int:
    """DV de rastreio dos Correios: módulo 11 com pesos 8,6,4,2,3,5,9,7."""
    soma = sum(int(digito) * peso for digito, peso in zip(serie, models.PESOS_DV_RASTREIO))
    resto = soma % 11
    if resto == 0:
        return 5
    if resto == 1:
        return 0
    return 11 - resto


def gerar_codigo_rastreio(pedido_id: int) -> str:
    """Código no formato dos Correios, derivado do id do pedido.

    A série é mockada (o id preenchido com zeros), mas o dígito verificador
    é calculado de verdade, então o código passa em qualquer validador de
    formato. Determinístico de propósito: o mesmo pedido devolve sempre o
    mesmo código, mesmo em banco que ainda não tinha a coluna.
    """
    serie = f"{pedido_id:08d}"[-8:]
    return (
        f"{models.PREFIXO_RASTREIO}{serie}"
        f"{_digito_verificador(serie)}{models.SUFIXO_RASTREIO}"
    )


def _para_datetime(valor: Optional[str]) -> Optional[datetime]:
    """Lê o formato que o SQLite grava em CURRENT_TIMESTAMP (UTC)."""
    if not valor:
        return None
    texto = str(valor).strip().replace("T", " ").split(".")[0]
    for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, formato)
        except ValueError:
            continue
    return None


def _prazo_em_segundos(pedido: dict) -> float:
    produto = repositories.obter_produto(pedido.get("produto_id"))
    dias = produto["prazo_entrega_dias"] if produto else models.PRAZO_ENTREGA_PADRAO_DIAS
    return dias * config.SEGUNDOS_POR_DIA_ENTREGA


def status_derivado(pedido: dict, agora: Optional[datetime] = None) -> str:
    """Etapa em que o pedido está, calculada a partir do relógio.

    Não existe job avançando status no banco: a etapa é uma função do tempo
    decorrido desde a criação sobre o prazo de entrega do produto, o que
    mantém a progressão determinística e sem estado pra manter em dia.

    As quatro etapas de trânsito dividem o prazo em fatias iguais e
    "entregue" começa exatamente quando o prazo vence, ficando assim pra
    sempre. `agora` existe pra testar sem esperar o relógio; o padrão é UTC
    porque é nele que o SQLite grava `data_criacao`.
    """
    etapas = models.ETAPAS_RASTREIO
    criacao = _para_datetime(pedido.get("data_criacao"))
    if criacao is None:
        return etapas[0]

    agora = agora or datetime.utcnow()
    total = _prazo_em_segundos(pedido)
    decorrido = (agora - criacao).total_seconds()

    if total <= 0 or decorrido >= total:
        return etapas[-1]
    if decorrido <= 0:
        return etapas[0]

    fatia = total / (len(etapas) - 1)
    return etapas[min(int(decorrido // fatia), len(etapas) - 1)]


def _com_rastreio(pedido: dict, agora: Optional[datetime] = None) -> dict:
    """Sobrepõe ao registro do banco o que é derivado, não armazenado.

    O código é recalculado quando falta (pedido criado antes da coluna
    existir), e o status vem do tempo, não da coluna.
    """
    pedido = dict(pedido)
    pedido["status"] = status_derivado(pedido, agora)
    pedido["codigo_rastreio"] = pedido.get("codigo_rastreio") or gerar_codigo_rastreio(pedido["id"])
    return pedido


# --- Pedidos -------------------------------------------------------------

def criar_pedido(produto_id: int, quantidade: int = 1, endereco_entrega: str = "") -> dict:
    produto = obter_produto(produto_id)
    if produto["estoque"] < quantidade:
        raise exceptions.EstoqueInsuficiente(produto["nome"], produto["estoque"])

    # Endereço informado vira cadastro; endereço omitido usa o cadastrado.
    # É o que evita perguntar de novo a quem já respondeu uma vez.
    if endereco_entrega and endereco_entrega.strip():
        repositories.salvar_perfil("endereco", endereco_entrega.strip())
    else:
        endereco_entrega = dados_do_cliente().get("endereco", "")

    valor_total = round(produto["preco"] * quantidade, 2)
    pedido = repositories.inserir_pedido(
        produto_id=produto_id,
        produto_nome=produto["nome"],
        quantidade=quantidade,
        valor_total=valor_total,
        endereco_entrega=endereco_entrega,
    )
    # O código depende do id, que só existe depois do INSERT.
    pedido = repositories.definir_codigo_rastreio(
        pedido["id"], gerar_codigo_rastreio(pedido["id"])
    )
    return _com_rastreio(pedido)


def obter_pedido(pedido_id: int) -> dict:
    pedido = repositories.obter_pedido(pedido_id)
    if pedido is None:
        raise exceptions.PedidoNaoEncontrado(pedido_id)
    return _com_rastreio(pedido)


def listar_pedidos() -> List[dict]:
    return [_com_rastreio(pedido) for pedido in repositories.listar_pedidos()]


def rastrear_pedido(pedido_id: int) -> dict:
    pedido = obter_pedido(pedido_id)
    etapa_atual = pedido["status"]
    return {
        "pedido_id": pedido_id,
        "codigo_rastreio": pedido["codigo_rastreio"],
        "etapa_atual": etapa_atual,
        "localizacao": models.LOCALIZACOES_MOCK.get(etapa_atual, "Desconhecida"),
        "etapas": models.ETAPAS_RASTREIO,
        "entrega_agendada": pedido.get("data_entrega_agendada"),
    }


# --- Notificação de mudança de status --------------------------------------

def _texto_da_notificacao(pedido: dict, status: str) -> str:
    """O texto do aviso, renderizado a partir do template do canal.

    É o mesmo template que seria enviado pela Cloud API, com os parâmetros já
    substituídos. Manter uma fonte só evita o pior tipo de divergência aqui:
    a tela mostrar uma frase e o cliente receber outra, aprovada meses antes.
    """
    template = models.TEMPLATES_NOTIFICACAO.get(status)
    if template is None:
        return models.TEMPLATE_GENERICO.format(
            id=pedido["id"], produto=pedido["produto_nome"], status=status
        )
    valores = {"id": pedido["id"], "produto": pedido["produto_nome"]}
    if "codigo" in template.parametros:
        valores["codigo"] = pedido["codigo_rastreio"]
    return template.renderizar(**valores)


def canal_aceita_texto_livre(agora: Optional[datetime] = None) -> bool:
    """Se a Cloud API entregaria uma mensagem espontânea agora, ou só template.

    A janela é de 24 horas contadas da última mensagem do cliente. Resposta
    dentro de uma conversa está sempre dentro dela (ele acabou de escrever),
    então quem precisa perguntar isto é o que sai sozinho: aviso de pedido,
    lembrete, retomada de carrinho.

    `agora` é aceito pra testar sem depender do relógio, como no
    `status_derivado`.
    """
    return whatsapp.dentro_da_janela(
        repositories.ultima_mensagem_do_cliente(), agora=agora
    )


def notificacao_para_envio(pedido: dict, status: str) -> Optional[dict]:
    """O que o transporte precisa mandar pra Cloud API, quando ele existir.

    Devolve `None` na etapa sem template aprovado, que é o caso em que a
    mensagem só pode aparecer no simulador: inventar um nome de template no
    envio devolveria erro da Meta, não a mensagem.

    Não faz requisição nenhuma. O provedor ainda não foi escolhido, e o que
    faltava pra escolher era justamente ter a mensagem neste formato.
    """
    template = models.TEMPLATES_NOTIFICACAO.get(status)
    if template is None:
        return None
    valores = {"id": pedido["id"], "produto": pedido["produto_nome"]}
    if "codigo" in template.parametros:
        valores["codigo"] = pedido["codigo_rastreio"]
    return {
        "messaging_product": "whatsapp",
        "to": pedido.get("sessao_id"),
        "type": "template",
        "template": {
            "name": template.nome,
            "language": {"code": whatsapp.IDIOMA},
            "components": template.componentes(**valores),
        },
    }


def _avancou(status: str, notificado: Optional[str]) -> bool:
    """Só é novidade o que está adiante do que já foi comunicado.

    Comparar por igualdade não bastava: a etapa é derivada do relógio e da
    régua de tempo, então ela pode recuar (a escala de `SEGUNDOS_POR_DIA_ENTREGA`
    muda entre execuções, o prazo do produto aumenta no catálogo), e um pedido
    já anunciado como entregue voltava a ser anunciado como confirmado. Etapa
    desconhecida (nula, de pedido migrado, ou gravada por versão anterior)
    conta como nunca comunicada.
    """
    etapas = models.ETAPAS_RASTREIO
    if notificado not in etapas:
        return True
    return etapas.index(status) > etapas.index(notificado)


def sincronizar_notificacoes(agora: Optional[datetime] = None) -> List[dict]:
    """Avisa no histórico do chat os pedidos que andaram desde o último aviso.

    Idempotente: a etapa comunicada fica gravada em `status_notificado`, então
    chamar duas vezes seguidas não repete mensagem. Em ordem de pedido, pra
    que o histórico fique coerente quando vários avançam de uma vez.
    """
    novas: List[dict] = []
    for registro in sorted(repositories.listar_pedidos(), key=lambda p: p["id"]):
        pedido = _com_rastreio(registro, agora)
        if not _avancou(pedido["status"], registro.get("status_notificado")):
            continue

        # Reserva antes de escrever: se outra aba já avisou esta etapa entre a
        # leitura e agora, o UPDATE não acerta linha nenhuma e a mensagem não
        # é gravada duas vezes.
        if not repositories.marcar_status_notificado(pedido["id"], pedido["status"]):
            continue

        conteudo = _texto_da_notificacao(pedido, pedido["status"])
        repositories.inserir_mensagem("assistant", conteudo, models.TIPO_NOTIFICACAO)
        novas.append(
            {"role": "assistant", "content": conteudo, "tipo": models.TIPO_NOTIFICACAO}
        )

    return novas


def agendar_entrega(pedido_id: int, data_entrega: str) -> dict:
    """Combina a data com o cliente. Não mexe no status: o pedido continua
    andando pela logística, agendado ou não."""
    obter_pedido(pedido_id)
    return _com_rastreio(repositories.atualizar_entrega_agendada(pedido_id, data_entrega))


def gerar_segunda_via(pedido_id: int, tipo: str = "boleto") -> dict:
    pedido = obter_pedido(pedido_id)

    if tipo == "nf":
        return {
            "tipo": "nota_fiscal",
            "pedido_id": pedido_id,
            "numero_nf": f"NF-{pedido_id:06d}",
            "chave_acesso": f"MOCK{pedido_id:044d}",
            "data_emissao": pedido["data_criacao"],
            "valor": pedido["valor_total"],
        }

    vencimento = (date.today() + timedelta(days=7)).isoformat()
    return {
        "tipo": "boleto",
        "pedido_id": pedido_id,
        "linha_digitavel": f"34191.79001 01043.510047 91020.150008 {pedido_id} {int(pedido['valor_total'] * 100):010d}",
        "vencimento": vencimento,
        "valor": pedido["valor_total"],
    }
