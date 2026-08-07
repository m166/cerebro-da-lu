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
MAX_TOOL_ITERATIONS = 4

# Quantos produtos a busca devolve pro modelo por padrão — o catálogo tem
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

# Piso de similaridade. Atenção: com o E5 os scores são comprimidos numa
# faixa alta e as distribuições se sobrepõem — medindo 16 perguntas do
# domínio contra 8 fora dele, as do domínio ficaram entre 0.842 e 0.92 e as
# de fora chegaram a 0.863. Ou seja, este corte derruba o pior ruído mas
# NÃO é um filtro confiável de assunto. Quem de fato segura resposta
# inventada é a persona, que manda a Lu admitir quando a base não cobre.
SCORE_MINIMO_CONHECIMENTO = 0.83


def persona() -> str:
    return PERSONA_PATH.read_text(encoding="utf-8")
