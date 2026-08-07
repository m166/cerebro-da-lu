# CLAUDE.md

Guia para trabalhar neste repositório. Leia o `README.md` primeiro pra
contexto de produto — este arquivo é sobre como mexer no código.

## O que é o projeto

"Cérebro da Lu" (pasta ainda `Cérebro do Matheus` durante a migração): um
assistente de e-commerce que atende via chat e usa **tool calling** pra
consultar catálogo/estoque, criar e rastrear pedidos, comparar e sugerir
produtos e gerar 2ª via de boleto/NF. Tudo hoje roda sobre **dados
mockados** (catálogo fixo em Python, pedidos em SQLite) — não há integração
real com sistemas do Magalu.

## Estrutura em camadas

```
app/
  main.py           cria o FastAPI app, monta /static, registra routers
  config.py         env vars, caminhos, limites (tool iterations, busca)
  models.py         DDL das tabelas + constantes de domínio (status, etapas)
  schemas.py        Pydantic: contratos de entrada e saída da API
  database.py       conexão SQLite + init_db
  repositories.py   acesso a dados (mensagens, pedidos, catálogo)
  services.py       regras de negócio (validação, cálculo, sugestão)
  exceptions.py     erros de domínio
  routers/
    views.py        serve o HTML do chat
    chat.py         /api/chat, /api/history
    produtos.py     /api/produtos, /api/categorias, sugestão, comparação
    pedidos.py      /api/pedidos + rastreio, agendamento, 2ª via
  ai/
    client.py       client da Groq (lazy, pra não exigir key nos testes)
    tools.py        TOOL_SCHEMAS + DISPATCH + executar()
    chat.py         loop de tool calling e histórico
  data/
    catalogo.py     113 produtos mockados em 27 categorias
static/             frontend vanilla (HTML/CSS/JS), sem framework
tests/              suíte pytest espelhando as camadas
```

### Direção das dependências

```
routers → services → repositories → database / data
routers → ai.chat → ai.tools → services
```

Nunca inverta isso. Em particular, `services.py` **não** importa
`ai/` — foi assim que o import circular foi evitado (tools precisa dos
services, então quem orquestra o modelo fica acima de ambos).

## Convenções

- Texto voltado ao usuário (persona, mensagens de erro, docs) em português
  do Brasil. Nomes de domínio (`produto`, `pedido`, `estoque`,
  `avaliacao`) em português; nomes de infra (`get_connection`, `router`,
  `lifespan`) em inglês, seguindo o framework.
- **Python 3.9** no venv: não use `X | None` em anotações avaliadas em
  runtime. Em `schemas.py` (Pydantic) use `Optional[...]`; em módulos
  comuns, `Optional[...]` ou `from __future__ import annotations`.
- Erros de negócio são exceções de `app/exceptions.py`. Os routers
  traduzem pra `HTTPException` (o corpo sai como `{"detail": ...}`, que é
  o que o frontend lê); `ai/tools.py` traduz pra `{"erro": ...}`, formato
  que o modelo entende melhor que uma exceção.
- Sem comentários explicando o óbvio. Só quando houver decisão não óbvia
  (ex: por que a normalização do score é relativa aos candidatos).
- Sem framework de frontend — mudanças de UI são HTML/CSS/JS direto em
  `static/`.
- SQLite é suficiente enquanto for single-user/local. Não introduza
  Postgres ou ORM sem necessidade real (por isso `models.py` guarda DDL,
  não classes de ORM).
- Ao adicionar produto no catálogo, mantenha o mínimo de 4 por categoria
  — é o que viabiliza comparação, e há teste garantindo isso.

## Rodando e testando

```bash
source .venv/bin/activate
uvicorn app.main:app --reload    # app em http://localhost:8000
pytest                            # suíte de testes
```

Atenção: o entrypoint é `app.main:app` (não `main:app`).

### Regras dos testes

- **Nenhum teste chama a Groq de verdade.** Use a fixture `groq_falso`
  (em `tests/conftest.py`) com os helpers `resposta_do_modelo` e
  `tool_call_falso`.
- A fixture `banco_isolado` é `autouse`: cada teste ganha um SQLite
  temporário, nunca o `cerebro.db` do usuário.
- Não acople testes a IDs fixos de produto — use `id_por_nome("...")`,
  senão inserir um produto no meio do catálogo quebra a suíte.

## Agentes especialistas

Subagentes dedicados em `.claude/agents/`:

- **backend-genai-specialist** — camadas `services`/`repositories`/
  `routers`, schema do SQLite, tool calling e prompts.
- **frontend-specialist** — `static/`, UX do chat e do catálogo.
- **test-specialist** — suíte pytest, fixtures e mocks da Groq.
- **git-specialist** — commits, branches, conflitos.

Prefira delegar pro especialista quando a tarefa for claramente da área
dele.
