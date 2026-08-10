# Cérebro da Lu

Assistente de IA para atendimento de e-commerce, inspirado no "Cérebro da Lu"
(Magazine Luiza). Nasceu como projeto de estudo pessoal ("Cérebro do
Matheus") e está sendo transformado em um produto: um assistente de compras
que conversa com o cliente, consulta catálogo/estoque, cria e acompanha
pedidos, sugere o melhor produto pra necessidade de cada um, e resolve
burocracia (2ª via de boleto/NF).

> Nota: a pasta/projeto ainda se chama "Cérebro do Matheus" durante a
> migração. O rename para "Cérebro da Lu" acontece depois que o produto
> estiver estável.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edite o `.env` e coloque sua chave da Groq (gere uma grátis, sem cartão de
crédito, em https://console.groq.com/keys).

## Rodando

```bash
uvicorn app.main:app --reload
```

Abra http://localhost:8000 no navegador. A documentação da API fica em
http://localhost:8000/docs.

## Testes

```bash
pytest
```

Rápidos e sem custo: não chamam a Groq nem baixam o modelo de embedding.

## Avaliação

A suíte de testes garante que o código funciona; a de avaliação mede se a
**Lu acerta** — se a busca traz o documento certo e se ela escolhe a
ferramenta certa. Roda contra o modelo real e a Groq, então fica separada:

```bash
python -m evals              # tudo
python -m evals retrieval    # só o RAG (sem custo de API)
python -m evals ferramentas  # só escolha de tool (~21 chamadas à Groq)
```

Sai com código 1 se alguma métrica ficar abaixo do mínimo. Nada é
executado nem gravado: a avaliação de ferramenta só pede a decisão do
modelo, sem rodar o loop, então não cria pedido nem escreve histórico.

Última execução:

| Métrica | Resultado |
| --- | --- |
| acerto@1 (documento certo em 1º) | 49/52 (94,2%) |
| acerto@3 | 52/52 (100%) |
| MRR | 0,968 |
| cobertura do domínio (sobrevive ao corte) | 52/52 (100%) |
| rejeição de pergunta fora de escopo | 7/8 |
| ferramenta correta | 16/18 (88,9%) |
| respondeu sem consultar ferramenta | 1/18 |
| conversa sem disparar ferramenta | 3/3 |

A avaliação de ferramenta varia entre execuções — o modelo não é
determinístico, e alguns casos têm mais de uma escolha defensável. O
retrieval é estável.

Os mínimos ficam logo abaixo do medido, pra que uma regressão trave a
execução em vez de passar despercebida.

## Visão de produto

A Lu é uma vendedora/atendente virtual. O cliente conversa em linguagem
natural e ela usa **tool calling** (function calling da Groq) pra acionar
funções de backend — consulta de catálogo, criação de pedido, rastreio etc.
— em vez de só "conversar". As funções hoje rodam sobre dados mockados
(catálogo fixo, pedidos em SQLite), simulando o que seria uma integração
real com sistemas do Magalu (catálogo, estoque, logística, financeiro).

### Funcionalidades

- **Catálogo de 113 produtos** em 27 categorias, com no mínimo 4 produtos
  por categoria — de propósito, pra que comparar opções faça sentido.
- **Consultar pedidos** (mockados) — status, itens, valor.
- **Gerar pedidos novos** — a partir da conversa ("quero comprar X").
- **Consultar estoque** de um produto.
- **Sugerir o melhor produto** pra uma necessidade, combinando preço, prazo
  de entrega e avaliação — não só o mais barato.
- **Comparar produtos** lado a lado, apontando quem ganha em cada critério.
- **Agendar entrega** pra uma data escolhida pelo cliente.
- **Base de conhecimento (RAG)** com busca semântica sobre tecnologia: o
  que cada especificação significa e o que olhar na hora de escolher. É o
  que permite responder "meu quarto tem 12m² e bate sol" com "9000 BTUs,
  e por isso este modelo" em vez de só listar preço.
- **2ª via de boleto ou nota fiscal** (mockado).
- **Rastreio de pedido** — onde está, etapa atual.
- **Catálogo navegável** — painel com filtro por categoria e busca, onde o
  cliente explora e pede direto, além de conversar pelo chat.
- **Painel de pedidos** — lista os pedidos e permite rastrear, agendar
  entrega e gerar 2ª via de boleto/NF sem passar pelo chat.

## Arquitetura

Estrutura em camadas de projeto FastAPI:

```
app/
  main.py           cria o app, monta /static, registra routers
  config.py         env vars, caminhos e limites
  models.py         DDL das tabelas + constantes de domínio
  schemas.py        Pydantic: contratos de entrada e saída
  database.py       conexão SQLite + init_db
  repositories.py   acesso a dados (mensagens, pedidos, catálogo, RAG)
  services.py       regras de negócio
  exceptions.py     erros de domínio
  vectorstore.py    índice vetorial do RAG (embeddings + similaridade)
  routers/          views.py, chat.py, produtos.py, pedidos.py
  ai/               client.py (Groq), tools.py (function calling), chat.py (loop)
  data/catalogo.py     os 113 produtos mockados
  data/conhecimento.py base de conhecimento do RAG (40 documentos)
persona.md          system prompt da Lu
static/             frontend vanilla (HTML/CSS/JS): chat + catálogo
tests/              suíte pytest espelhando as camadas
```

Dependências fluem numa direção só:
`routers → services → repositories → database/data`, e
`routers → ai.chat → ai.tools → services`.

Sem framework de frontend (React etc.) e sem ORM por enquanto — o objetivo
agora é validar o fluxo de produto.

### Endpoints principais

| Método | Rota | O que faz |
| --- | --- | --- |
| POST | `/api/chat` | conversa com a Lu (com tool calling) |
| GET | `/api/history` | histórico persistido da conversa |
| GET | `/api/categorias` | lista as categorias do catálogo |
| GET | `/api/conhecimento` | busca semântica na base (`pergunta`, `categoria`) |
| GET | `/api/produtos` | lista/busca produtos (`query`, `categoria`, `limite`) |
| GET | `/api/produtos/{id}` | detalhe de um produto |
| GET | `/api/produtos/{id}/estoque` | estoque de um produto |
| GET | `/api/produtos/sugestao` | melhor produto (`categoria`, `criterio`) |
| POST | `/api/produtos/comparacao` | compara por categoria ou por IDs |
| POST | `/api/pedidos` | cria pedido |
| GET | `/api/pedidos` | lista pedidos (mais recentes primeiro) |
| GET | `/api/pedidos/{id}` | consulta pedido |
| GET | `/api/pedidos/{id}/rastreio` | rastreia pedido |
| POST | `/api/pedidos/{id}/agendar-entrega` | agenda entrega |
| GET | `/api/pedidos/{id}/segunda-via` | 2ª via (`tipo=boleto|nf`) |

## Roadmap

1. ~~LLM + persona + interface de chat~~
2. ~~Memória de conversa persistente entre execuções~~
3. ~~**Pivot para "Cérebro da Lu"**~~
   - ~~Catálogo mockado (113 produtos, 27 categorias) + estoque~~
   - ~~Criar/consultar pedidos mockados~~
   - ~~Sugestão de produto (preço/prazo/avaliação)~~
   - ~~Comparação de produtos lado a lado~~
   - ~~Agendamento de entrega~~
   - ~~2ª via de boleto/NF (mockado)~~
   - ~~Rastreio de pedido (mockado)~~
   - ~~Tool calling ligando o chat às funções acima~~
   - ~~Catálogo navegável na UI, com filtro por categoria e busca~~
   - ~~Estrutura em camadas (routers/services/repositories/schemas/models)~~
4. ~~**RAG** — base vetorial de conhecimento sobre produtos/tecnologias pra
   fundamentar as sugestões~~
   - ~~40 documentos cobrindo as categorias do catálogo + temas gerais
     (voltagem, eficiência energética, garantia)~~
   - ~~Busca semântica com embeddings locais (`intfloat/multilingual-e5-small`)~~
   - ~~Tool `buscar_conhecimento` e endpoint `/api/conhecimento`~~
5. Dados reais — trocar mocks por integrações verdadeiras (catálogo,
   estoque, logística, financeiro) quando/se o projeto avançar pra isso.
6. ~~**Avaliação e iteração** — medir qualidade do retrieval e das decisões
   de tool calling~~
   - ~~Suíte `evals/` com 40 casos de retrieval, 8 fora de escopo e 21 de
     escolha de ferramenta~~
   - ~~Métricas com mínimo que trava build (acerto@1, acerto@3, MRR)~~
   - ~~Iteração 1: escolha de ferramenta de 77,8% para 94,4% (descrições
     de tool que empurravam pra `listar_categorias` à toa)~~
   - ~~Iteração 2: acerto@1 do retrieval de 75% para 94,2%, enriquecendo
     os documentos com as perguntas que respondem~~
7. Rename final da pasta/projeto pra "Cérebro da Lu".

## Estado atual

- Chat via navegador com tool calling (Groq, `openai/gpt-oss-120b` por
  padrão, configurável via `GROQ_MODEL` no `.env`).
- 11 ferramentas disponíveis ao modelo: busca de produto, base de
  conhecimento, categorias, estoque, sugestão, comparação,
  criação/consulta/rastreio de pedido, agendamento e 2ª via.
- Histórico persistido em SQLite — sobrevive a refresh e restart.
- Catálogo, pedidos, estoque, rastreio, agendamento e 2ª via são **dados
  mockados**, pensados pra simular as integrações reais que um produto
  como esse teria no Magalu.
- A busca exposta ao modelo devolve no máximo 10 produtos por vez (com o
  total encontrado), pra não estourar o contexto com 113 itens.
- Ainda não há autenticação nem multi-usuário — é single-user, uso local.

### Por que cada documento tem uma lista de perguntas

O corpo dos documentos é escrito em vocabulário de especificação ("air
fryer", "voltagem", "switch azul"), mas o cliente descreve sintoma e usa
sinônimo ("fritadeira", "tomada diferente", "barulho quando digito"). Sem
uma ponte entre os dois, a busca erra justamente nas perguntas mais
naturais — o acerto@1 era de 75%.

Cada documento passou a declarar as perguntas que responde, e elas entram
no texto indexado junto do corpo. O acerto@1 subiu pra 94,2% e o acerto@3
pra 100%.

Pra garantir que isso é generalização e não memorização, as perguntas
indexadas não podem ser cópia dos casos de avaliação — há teste em
`tests/test_rag.py` que falha se alguma passar de 50% de sobreposição de
termos de conteúdo. Doze casos do conjunto foram escritos depois do
enriquecimento, justamente pra medir pergunta inédita.

### Busca híbrida: cada sinal tem um papel

O RAG combina embedding com BM25, mas eles não fazem a mesma coisa:

- **Ordenar é com o embedding.** Foi medido: semântica pura acerta 94,2%
  em 1º lugar, contra 92,3% da fusão por posto recíproco e 88,5% do BM25
  sozinho. A hipótese de que fundir melhoraria o ranking não se sustentou.
- **Filtrar é com os dois, em OU.** Um trecho entra se passar em qualquer
  um dos cortes, porque os sinais falham em casos opostos: pergunta que
  descreve sintoma ("pego ônibus lotado e queria abafar o barulho") tem
  cosseno baixo (0,80) e léxico alto (8,9); pergunta curta e direta
  ("quantos BTU pra um escritório de 25 metros?") é o contrário (0,88 e
  2,8). Exigir os dois barrava as duas famílias.

Com isso a cobertura do domínio vai a 52/52 mantendo 7/8 de rejeição —
antes eram 49/52 e 7/8, ou seja, **3 perguntas legítimas eram respondidas
com "não tenho essa informação"**. Isso passou muito tempo despercebido
porque a avaliação media só a rejeição, nunca a cobertura; hoje mede as
duas, e elas se puxam em direções opostas de propósito.

Nenhum corte é filtro de assunto perfeito — 1 das 8 perguntas fora do
domínio ainda passa. Quem segura resposta inventada continua sendo a
persona, que manda a Lu admitir quando a base não cobre.

## Notas de desenvolvimento

- O venv roda **Python 3.9**, então anotações com `X | None` não funcionam
  em runtime — use `Optional[...]`.
- **`numpy<2` é obrigatório**: o torch disponível pra Python 3.9 (2.2.x) foi
  compilado contra NumPy 1.x e quebra com NumPy 2 ("Numpy is not
  available").
- Na primeira execução o modelo de embedding baixa (~470MB) e fica em
  cache. A carga é lazy: só acontece na primeira busca de conhecimento.
- Os testes nunca chamam a Groq (mockada) nem baixam o modelo de embedding
  (encoder falso na fixture `rag_sem_download`), e sempre usam um SQLite
  temporário.
- Convenções e direção das dependências entre camadas estão no
  `CLAUDE.md`.
