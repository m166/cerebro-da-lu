# ATENÇÃO: este Dockerfile não foi construído nem executado. A máquina onde
# ele foi escrito não tem Docker instalado, então trate como ponto de partida
# a validar com `docker build`, não como algo comprovado.

FROM python:3.11-slim

# curl serve ao healthcheck; o resto do build não precisa de compilador porque
# as dependências têm wheel pronto pra esta imagem.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/modelos

WORKDIR /app

# Dependências antes do código: mudar um .py não invalida a camada pesada.
COPY requirements.txt .

# O pin de numpy<2 existe por causa do torch de Python 3.9. Nesta imagem, com
# 3.11, o torch atual já convive com NumPy 2, e manter o pin só prenderia o
# build a uma versão velha.
RUN sed '/^numpy<2$/d; /^# O torch disponível/,+1d' requirements.txt > /tmp/req.txt \
    && pip install --no-cache-dir -r /tmp/req.txt

# Modelo de embedding baixado no build, e não na primeira pergunta: são ~470MB
# e sem isso o primeiro cliente esperaria o download inteiro.
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('intfloat/multilingual-e5-small')"

COPY app app
COPY static static
COPY persona.md .

# O banco fica em volume separado: sem isso, cada deploy apaga as conversas.
ENV DB_PATH=/dados/cerebro.db
VOLUME /dados

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD curl -fsS http://localhost:8000/api/categorias || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
