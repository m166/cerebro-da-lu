"""Ponte que faz `pytest` rodar também os testes de frontend.

Sem isto, os testes em `tests/frontend/` seriam um arquivo que ninguém
lembra de executar, e o `static/` continuaria sendo a única camada
verificada só por screenshot. Foi assim que passou despercebido um negrito
que atravessava quebra de linha.

Pula quando não há node na máquina, em vez de falhar: a suíte de Python não
deve depender de outro runtime pra rodar. Quando pula, o aviso diz o que
fazer, senão o pulo vira silêncio.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

TESTES_JS = Path(__file__).resolve().parent / "frontend"

node = shutil.which("node")


@pytest.mark.skipif(node is None, reason="node não encontrado; rode `node --test tests/frontend/`")
def test_suite_de_frontend():
    arquivos = sorted(str(caminho) for caminho in TESTES_JS.glob("*.test.js"))
    assert arquivos, "nenhum teste de frontend encontrado"

    # Os arquivos vão explícitos, não o diretório: o node 24 tenta carregar o
    # diretório como módulo e falha com MODULE_NOT_FOUND.
    resultado = subprocess.run(
        [node, "--test", *arquivos], capture_output=True, text=True
    )
    if resultado.returncode != 0:
        pytest.fail(resultado.stdout + resultado.stderr)
