"""Configuração central: variáveis de ambiente e caminhos do projeto."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# Configurável por env var pra que dá pra subir uma instância de teste sem
# encostar no banco de quem está usando o app. Já aconteceu de uma demo
# gravar pedido e aviso no histórico real por não existir essa saída.
DB_PATH = Path(os.getenv("DB_PATH", BASE_DIR / "cerebro.db"))
PERSONA_PATH = BASE_DIR / "persona.md"
STATIC_DIR = BASE_DIR / "static"

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
