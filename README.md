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
6. Avaliação e iteração — medir qualidade das respostas e das decisões de
   tool calling.
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

### Limitação conhecida do RAG

O corte por score (`SCORE_MINIMO_CONHECIMENTO`) derruba o ruído pior, mas
**não é um filtro confiável de assunto**. O E5 comprime as similaridades
numa faixa alta e as distribuições se sobrepõem: medindo 16 perguntas do
domínio contra 8 fora dele, as do domínio ficaram entre 0.842 e 0.92 e as
de fora chegaram a 0.863. Quem de fato segura resposta inventada é a
persona, que manda a Lu admitir quando a base não cobre o assunto.

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
