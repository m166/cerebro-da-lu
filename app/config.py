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


def persona() -> str:
    return PERSONA_PATH.read_text(encoding="utf-8")
