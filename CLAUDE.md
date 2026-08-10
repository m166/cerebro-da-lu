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
  repositories.py   acesso a dados (mensagens, pedidos, catálogo, RAG)
  services.py       regras de negócio (validação, cálculo, sugestão)
  exceptions.py     erros de domínio
  vectorstore.py    índice vetorial do RAG (lazy, análogo a database.py)
  routers/
    views.py        serve o HTML do chat
    chat.py         /api/chat, /api/history
    produtos.py     /api/produtos, /api/categorias, sugestão, comparação,
                    /api/conhecimento
    pedidos.py      /api/pedidos + rastreio, agendamento, 2ª via
  ai/
    client.py       client da Groq (lazy, pra não exigir key nos testes)
    tools.py        TOOL_SCHEMAS + DISPATCH + executar()
    chat.py         loop de tool calling e histórico
  data/
    catalogo.py     113 produtos mockados em 27 categorias
    conhecimento.py 40 documentos que formam o corpus do RAG
static/             frontend vanilla (HTML/CSS/JS), sem framework
tests/              suíte pytest espelhando as camadas
evals/              avaliação de qualidade (modelo real + Groq)
```

### Direção das dependências

```
routers → services → repositories → database / vectorstore / data
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
- **Não atualize o NumPy pra 2.x.** O torch disponível pra Python 3.9
  (2.2.x) foi compilado contra NumPy 1.x e o `encode()` do RAG quebra com
  "Numpy is not available". O pin está no `requirements.txt`.
- Erros de negócio são exceções de `app/exceptions.py`. Os routers
  traduzem pra `HTTPException` (o corpo sai como `{"detail": ...}`, que é
  o que o frontend lê); `ai/tools.py` traduz pra `{"erro": ...}`, formato
  que o modelo entende melhor que uma exceção.
- **Ferramenta que devolve vazio custa caro.** O modelo reformula e chama
  de novo, gastando rodada de tool calling — foi assim que a busca de
  produto, sensível a acento, derrubava a resposta por estourar o limite.
  Prefira degradar (casamento parcial, resultado aproximado) a devolver
  lista vazia.
- Sem comentários explicando o óbvio. Só quando houver decisão não óbvia
  (ex: por que a normalização do score é relativa aos candidatos).
- Sem framework de frontend — mudanças de UI são HTML/CSS/JS direto em
  `static/`.
- No frontend, nunca monte HTML por concatenação com dado vindo da API —
  use `textContent` e `createElement` (é o padrão já seguido em
  `script.js`).
- **Não formate data com `new Date(...)` no frontend.** Uma string como
  `"2026-09-15"` é lida como UTC e, no fuso do Brasil, exibida um dia
  antes. Use `formatarData()`, que reformata a string.
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
- **Nenhum teste baixa o modelo de embedding.** A fixture `rag_sem_download`
  é `autouse` e troca o encoder por um saco de palavras determinístico.
  Como ele é léxico e não semântico, **não escreva teste afirmando que a
  pergunta X traz o documento Y** — isso mede o encoder falso, não o
  sistema. Qualidade semântica se verifica manualmente, com o modelo real.

## Validando a UI sem driver de browser

Não há playwright nem node no ambiente, mas o Chrome instalado tira
screenshot em headless — e **olhar a tela pega o que teste de API não
pega** (foi assim que apareceu uma data de entrega exibida um dia antes).

```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless=new --disable-gpu --hide-scrollbars \
  --window-size=980,900 --screenshot=/tmp/lu.png \
  --virtual-time-budget=6000 "http://localhost:8000/#catalogo"
```

Headless não clica, então os painéis são alcançados pela URL:
`#catalogo` e `#pedidos` abrem o painel correspondente no carregamento.
Pra conferir o tema claro, acrescente
`--blink-settings=preferredColorScheme=1`.

## Testes x avaliação

São coisas diferentes e não devem se misturar:

- **`tests/`** verifica que o código funciona. Roda em segundos, é
  determinístico, não chama a Groq nem baixa modelo. Toda mudança de
  código passa por aqui.
- **`evals/`** mede se a Lu **acerta** — retrieval e escolha de
  ferramenta. Usa o modelo real e a Groq, demora e custa token. Rode
  depois de mexer em prompt, persona, descrição de tool ou base de
  conhecimento:

```bash
python -m evals retrieval     # sem custo de API
python -m evals ferramentas   # ~21 chamadas à Groq
```

Regras da avaliação:

- A avaliação de ferramenta **não executa** as tools nem grava histórico:
  só pede a decisão do modelo. Se mudar isso, ela passa a criar pedidos.
- O resultado de `ferramentas` varia entre execuções (o modelo não é
  determinístico). Não trate uma queda de um caso como regressão sem
  rodar de novo.
- Ao adicionar caso, escreva a pergunta **como um cliente falaria**, com
  gíria e sem acento. Usar as palavras do título do documento infla a
  métrica e não mede nada.
- Se um caso falhar, considere que a expectativa pode estar errada antes
  de mexer no sistema — já aconteceu de o caso pedir tool onde a persona
  manda perguntar primeiro.

## Sobre o RAG

- `vectorstore.py` é infraestrutura (o análogo de `database.py`): carrega
  modelo e índice de forma lazy, em duas etapas, porque o modelo tem
  centenas de MB. `bm25.py` é o índice léxico que ele usa junto.
- **Ordenação é semântica; o BM25 filtra.** Medido: semântica pura acerta
  94,2% em 1º contra 92,3% do RRF. Se for mexer nisso, meça de novo — o
  `score_fusao` continua exposto pra facilitar.
- **O corte de relevância é OU, não E.** Os sinais falham em casos
  opostos (sintoma = cosseno baixo e léxico alto; pergunta curta = o
  contrário). Trocar por E derruba a cobertura do domínio.
- O modelo é da família **E5**, que exige os prefixos `query:` e
  `passage:` — sem eles a qualidade cai bastante. Os prefixos estão em
  `config.py` e são aplicados no `vectorstore.py`.
- `SCORE_MINIMO_CONHECIMENTO` é um piso fraco, calibrado empiricamente.
  Com o E5 as distribuições de pergunta no domínio e fora dele se
  sobrepõem, então **ele não é filtro de assunto confiável** — quem segura
  resposta inventada é a persona. Se trocar de modelo, recalibre.
- Documento novo em `conhecimento.py` com `categoria` preenchida precisa
  usar uma categoria que exista no `catalogo.py`, senão o filtro nunca o
  encontra (há teste garantindo isso).
- **Todo documento declara `perguntas`** (mínimo 3), que entram no texto
  indexado. É o que liga o vocabulário de especificação do corpo ao de
  sintoma do cliente — foi o que levou o acerto@1 de 75% pra 94,2%. Ao
  criar documento, escreva as perguntas incluindo sinônimos populares
  ("fritadeira" pra air fryer, "tomada" pra voltagem).
- **Não copie caso do `evals/` pra dentro das `perguntas`.** Isso vira
  memorização e a métrica deixa de significar algo; há teste que falha se
  a sobreposição de termos de conteúdo passar de 50%.

## Agentes especialistas

Subagentes dedicados em `.claude/agents/`:

- **backend-genai-specialist** — camadas `services`/`repositories`/
  `routers`, schema do SQLite, tool calling e prompts.
- **frontend-specialist** — `static/`, UX do chat e do catálogo.
- **test-specialist** — suíte pytest, fixtures e mocks da Groq.
- **git-specialist** — commits, branches, conflitos.

Prefira delegar pro especialista quando a tarefa for claramente da área
dele.
