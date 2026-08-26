"""Configuração central: variáveis de ambiente e caminhos do projeto."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# Postgres, não mais SQLite. O motivo é deploy: em container o disco é
# efêmero, e o arquivo `cerebro.db` sumia junto com conversa, pedido e
# cadastro a cada redeploy. `DATABASE_URL` é o nome que Render, Railway,
# Neon e Supabase já injetam prontos, então publicar vira só apontar.
#
# Continua configurável por env var pelo mesmo motivo de antes: dá pra subir
# uma instância de demonstração sem encostar no banco de quem está usando o
# app. Já aconteceu de um print gravar pedido no histórico real.
#
# **Não existe valor padrão, e isso é proposital.** Esta máquina usa a porta
# 5432 para um container de trabalho, e um padrão apontando pra
# `localhost:5432` faria a suíte de testes (que dá TRUNCATE nas tabelas) mirar
# no banco errado se alguém rodasse sem configurar. Sem padrão, o erro é
# imediato e explícito em vez de silencioso e destrutivo. A porta definitiva
# deste projeto ainda vai ser escolhida.
DATABASE_URL = os.getenv("DATABASE_URL")
PERSONA_PATH = BASE_DIR / "persona.md"
STATIC_DIR = BASE_DIR / "static"

# O simulador (a tela em `static/`) é andaime de teste, não produto, e **não
# vai pro ar junto com a app**. O motivo é concreto: nele qualquer pessoa
# digita qualquer número e cai na conversa daquele cliente, porque não há
# verificação nenhuma. Isso é aceitável numa ferramenta local, e seria
# vazamento numa URL pública. No WhatsApp o problema não existe: quem diz o
# número é a Meta, no envelope da mensagem, e não um formulário.
#
# Ligado por padrão porque local é onde ele serve. Quem publica desliga, e o
# Dockerfile já desliga.
SIMULADOR_ATIVO = os.getenv("SIMULADOR", "1").lower() not in ("0", "false", "nao", "não")

# Quantas rodadas de tool calling o chat pode fazer antes de desistir.
# Seis, não quatro: uma pergunta que combina conhecimento e catálogo já
# gasta três rodadas no caminho feliz, e qualquer reformulação de busca no
# meio estourava o limite e derrubava a resposta.
MAX_TOOL_ITERATIONS = 6

# Quantos produtos a busca devolve pro modelo por padrão, o catálogo tem
# mais de 100 itens e mandar todos estouraria o contexto sem necessidade.
LIMITE_BUSCA_TOOL = 8

# Quantos cartões de produto acompanham uma resposta no chat. Acima disso a
# conversa vira vitrine e o texto da Lu se perde no meio.
MAX_PRODUTOS_NA_RESPOSTA = 4

# Quantas mensagens do histórico vão pro modelo. O histórico completo
# continua no banco e na tela; o que é enviado precisa ser limitado porque
# a conta free da Groq trabalha com 8000 tokens por minuto, e reenviar a
# conversa inteira a cada rodada de tool calling estourava esse teto depois
# de poucas trocas. Dez mensagens (cinco idas e voltas) preserva o
# "esse aí" e o "o mais barato" da pergunta anterior.
MAX_MENSAGENS_CONTEXTO = 10

# Estourar o teto por minuto é quase sempre questão de ritmo, não de
# excesso: a conversa que gasta 7000 tokens cabe, só não cabe duas vezes no
# mesmo minuto. A Groq informa em quantos segundos dá pra tentar de novo, e
# quando isso é questão de poucos segundos vale esperar, porque o cliente
# prefere uma resposta em 4s a um erro na hora. Acima do teto abaixo ele
# prefere saber, em vez de olhar "digitando..." por meio minuto.
ESPERA_MAXIMA_POR_LIMITE = 12
TENTATIVAS_APOS_LIMITE = 2

# Escala de tempo da entrega mockada: quantos segundos reais valem um dia de
# prazo. O status do pedido é derivado do relógio, então com o padrão de 20
# um produto de prazo 4 dias percorre as 5 etapas e chega em ~80 segundos, o
# que cabe numa demo. Coloque 86400 pra simular tempo real.
SEGUNDOS_POR_DIA_ENTREGA = int(os.getenv("SEGUNDOS_POR_DIA_ENTREGA", "20"))

# RAG: modelo multilíngue treinado pra retrieval. Foi escolhido depois de
# comparar com paraphrase-multilingual-MiniLM, que acertava 1 de 4 buscas
# do smoke test contra 4 de 5 deste. Baixa na primeira execução (~470MB) e
# fica em cache no diretório do Hugging Face.
MODELO_EMBEDDING = os.getenv("MODELO_EMBEDDING", "intfloat/multilingual-e5-small")

# Largura do vetor que o modelo acima produz. Virou constante porque a coluna
# `vector(n)` do pgvector tem dimensão fixa no DDL: trocar de modelo de
# embedding sem mudar este número faz o INSERT falhar com "expected 384
# dimensions". Mudar a dimensão exige recriar a tabela `conhecimento_vetores`,
# porque ALTER de tipo não redimensiona vetor já gravado.
DIMENSOES_EMBEDDING = int(os.getenv("DIMENSOES_EMBEDDING", "384"))

# Visão: o modelo de conversa não aceita imagem, então a foto do cliente
# passa por este antes. Foi o único da conta que aceitou imagem quando
# testado; se trocar, confirme antes que o novo aceita `image_url`.
GROQ_MODEL_VISAO = os.getenv("GROQ_MODEL_VISAO", "qwen/qwen3.6-27b")

# O raciocínio é escondido pela Groq (`reasoning_format="hidden"`), mas ele
# ainda consome tokens antes da resposta: com pouco espaço, a descrição vem
# cortada no meio.
MAX_TOKENS_VISAO = 1600

# Teto do upload. Foto de celular passa fácil disso, e o cliente recebe um
# aviso claro em vez de a requisição morrer sem explicação.
TAMANHO_MAXIMO_IMAGEM = 8 * 1024 * 1024

# --- Cupom de desconto -----------------------------------------------------
#
# Quanto da margem líquida do produto pode virar desconto. É fração da
# MARGEM, não do preço: produto de R$ 2.000 com R$ 400 de margem aceita R$
# 120, que são 6% do preço. Confundir os dois é vender no prejuízo.
#
# 30% deixa dois terços da margem em pé, o que permite uma segunda tentativa
# mais generosa se a primeira não converter, sem nunca zerar o lucro.
PERCENTUAL_MAXIMO_DA_MARGEM = 0.30

# Abaixo disto o desconto não convence ninguém e só queima margem. Produto de
# margem magra simplesmente não recebe cupom, e isso é resposta, não falha.
DESCONTO_MINIMO_RELEVANTE = 10.00

# Quanto tempo o cupom vale. Prazo curto cria urgência e limita a exposição
# se um código vazar.
VALIDADE_CUPOM_HORAS = 48

# Quantos cupons uma mesma conversa pode receber. Sem teto, um cliente que
# aprende a sumir vira uma torneira aberta de desconto.
MAX_CUPONS_POR_SESSAO = 2

# A família E5 espera esses prefixos e perde qualidade sem eles: foi
# treinada com pergunta e documento assimétricos.
PREFIXO_PERGUNTA = "query: "
PREFIXO_DOCUMENTO = "passage: "

# Quantos trechos da base de conhecimento devolver por consulta.
LIMITE_CONHECIMENTO = 3

# Pisos de relevância. Um trecho é aceito quando passa em QUALQUER um dos
# dois, é OU, não E.
#
# O motivo é que os sinais falham em casos opostos. Pergunta que descreve
# sintoma ("pego ônibus lotado e queria abafar o barulho") tem cosseno
# baixo, perto de 0.80, mas casa muitos termos: léxico 8.9. Pergunta curta
# e direta ("quantos BTU pra um escritório de 25 metros?") é o contrário:
# cosseno 0.88 e quase nenhum termo em comum. Exigir os dois barraria as
# duas famílias; exigir um deles aceita ambas.
#
# Calibrados numa grade sobre 52 perguntas do domínio e 8 fora: nesta
# combinação o domínio inteiro passa e 7 das 8 de fora são barradas.
SCORE_MINIMO_CONHECIMENTO = 0.86
SCORE_LEXICAL_MINIMO = 5.0


def persona() -> str:
    return PERSONA_PATH.read_text(encoding="utf-8")
