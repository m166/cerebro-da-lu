"""Configuração central: variáveis de ambiente e caminhos do projeto."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

DB_PATH = BASE_DIR / "cerebro.db"
PERSONA_PATH = BASE_DIR / "persona.md"
STATIC_DIR = BASE_DIR / "static"

# Quantas rodadas de tool calling o chat pode fazer antes de desistir.
# Seis, não quatro: uma pergunta que combina conhecimento e catálogo já
# gasta três rodadas no caminho feliz, e qualquer reformulação de busca no
# meio estourava o limite e derrubava a resposta.
MAX_TOOL_ITERATIONS = 6

# Quantos produtos a busca devolve pro modelo por padrão, o catálogo tem
# mais de 100 itens e mandar todos estouraria o contexto sem necessidade.
LIMITE_BUSCA_TOOL = 10

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
