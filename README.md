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

O banco é **PostgreSQL com a extensão pgvector**, que guarda os embeddings
da base de conhecimento. Crie os dois bancos (o segundo é da suíte de
testes, que esvazia as tabelas a cada caso):

```bash
createdb cerebro_lu && createdb cerebro_lu_test
for db in cerebro_lu cerebro_lu_test; do
  psql -d $db -c 'CREATE EXTENSION IF NOT EXISTS vector'
done
```

Quem vem da versão em SQLite traz a conversa e os pedidos antigos com:

```bash
python -m scripts.migrar_sqlite_para_postgres
```

O `cerebro.db` não é apagado, fica como backup.

## Rodando

```bash
uvicorn app.main:app --reload
```

Abra http://localhost:8000 no navegador. A documentação da API fica em
http://localhost:8000/docs.

## Publicando

```bash
cp .env.example .env   # coloque a GROQ_API_KEY
docker compose up --build
```

**O simulador não sobe junto.** A imagem não copia `static/`, e a variável
`SIMULADOR=0` desliga a tela e o endpoint que deixa reivindicar um número:
publicado, ele permitiria a qualquer pessoa digitar o telefone de outra e ler
a conversa dela. A app publicada serve a API, responde 401 no que é do
cliente enquanto não houver o webhook do WhatsApp pra dizer quem está
falando, e mantém catálogo e conhecimento abertos.

O compose sobe dois serviços: a app e um `pgvector/pgvector:pg17`, que é
o Postgres com a extensão já compilada. O banco fica num volume, então
atualizar a imagem não apaga conversa. O modelo de embedding é baixado na
construção da imagem, e não na primeira pergunta, senão o primeiro cliente
esperaria os 470MB.

**Não validado:** o `Dockerfile`, o `docker-compose.yml` e o workflow de CI
foram escritos sem Docker e sem remote git disponíveis, então nunca foram
construídos nem executados. Trate como ponto de partida a conferir.

## Testes

```bash
pytest
```

Rápidos e sem custo: não chamam a Groq nem baixam o modelo de embedding.
Precisam de um PostgreSQL no ar (usam o banco `cerebro_lu_test`).

As funções puras do frontend têm teste próprio, no runner embutido do node:

```bash
node --test tests/frontend/formatacao.test.js
```

O `pytest` também os executa, e pula se não houver node instalado.

## Avaliação

A suíte de testes garante que o código funciona; a de avaliação mede se a
**Lu acerta**, se a busca traz o documento certo e se ela escolhe a
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
| acerto@1 (documento certo em 1º) | 48/52 (92,3%) |
| acerto@3 | 51/52 (98,1%) |
| MRR | 0,949 |
| cobertura do domínio (sobrevive ao corte) | 51/52 (98,1%) |
| rejeição de pergunta fora de escopo | 7/8 |
| ferramenta correta | 18/18 (100%) |
| respondeu sem consultar ferramenta | 0/18 |
| conversa sem disparar ferramenta | 3/3 |

As três primeiras linhas são da execução mais recente, depois de o corpus ir
de 40 pra 52 documentos e passar a cobrir as 39 categorias. O acerto@1 era
94,2% com 40 documentos: cobrir 12 categorias novas custou um caso. As
linhas de ferramenta são da execução anterior, `python -m evals ferramentas`
não foi rodado desde então porque consome cota diária da Groq.

A avaliação de ferramenta varia entre execuções, o modelo não é
determinístico, e alguns casos têm mais de uma escolha defensável. O
retrieval é estável.

Os mínimos ficam logo abaixo do medido, pra que uma regressão trave a
execução em vez de passar despercebida.

## Visão de produto

A Lu é uma vendedora/atendente virtual. O cliente conversa em linguagem
natural e ela usa **tool calling** (function calling da Groq) pra acionar
funções de backend (consulta de catálogo, criação de pedido, rastreio e
outras) em vez de só "conversar". As funções hoje rodam sobre dados mockados
(catálogo fixo, pedidos em PostgreSQL), simulando o que seria uma integração
real com sistemas do Magalu (catálogo, estoque, logística, financeiro).

### O canal é o WhatsApp

O destino da Lu é atender dentro do WhatsApp, e isso muda o produto, não
só a entrega: o cliente é identificado pelo **número**, manda **foto** e
**áudio**, e espera resposta de mensagem, não de site.

Por isso a interface de teste é um **simulador do WhatsApp**, com a mesma
paleta, o mesmo fundo de rabiscos, o mesmo cabeçalho e os mesmos tiques de
entrega. Uma barra escura no topo, deliberadamente fora do estilo do app,
separa o que o cliente veria do que é andaime: nela fica o número que está
"falando" e o botão de trocar de número.

O que já está de pé desse caminho: identidade por telefone, leitura de foto
e as **regras da Cloud API dentro do código** (`app/whatsapp.py`). O que
falta: áudio e o transporte em si (não há webhook, e o provedor ainda não
foi escolhido).

Estar adequado ao canal significa, na prática:

- **Aviso de pedido é template aprovado, não texto livre.** Mensagem
  espontânea fora da janela de 24 horas contada da última fala do cliente
  não é entregue pelo WhatsApp. Como o aviso de "saiu para entrega" sai
  sozinho dias depois, ele nasce como template UTILITY com parâmetros
  posicionais, pronto pra cadastrar na Meta.
- **A mesma frase serve os dois lados.** O texto que aparece no simulador é
  renderizado do mesmo template que iria pra API, então a tela nunca mostra
  uma coisa e o cliente recebe outra.
- **Formatação é a do WhatsApp, não markdown.** Negrito é `*assim*`, com um
  asterisco. Com dois, o cliente veria os asteriscos.
- Os limites do canal (1024 no corpo do template, 4096 no texto livre, 3
  botões, 10 linhas de lista) são constantes conferidas por teste.

Ligar o canal de verdade passou a ser escrever o transporte: o `sessao_id`
já é o número no formato do `wa_id`, e `services.notificacao_para_envio`
já devolve o payload pronto.

### Funcionalidades

- **Identidade pelo telefone**: a conversa, os pedidos e o cadastro
  pertencem ao número, não ao navegador. Voltar de outro aparelho com o
  mesmo número reencontra tudo; trocar de número é ser outra pessoa.
- **Simulador do WhatsApp** como interface de teste, com troca de número
  pra ensaiar mais de um cliente.
- **Foto do produto**: o cliente fotografa o que procura e a Lu diz se a
  loja tem algo parecido.
- **Catálogo de 184 produtos** em 39 categorias, com no mínimo 4 produtos
  por categoria, de propósito, pra que comparar opções faça sentido.
- **Consultar pedidos** (mockados), status, itens, valor.
- **Gerar pedidos novos**: a partir da conversa ("quero comprar X").
- **Consultar estoque** de um produto.
- **Sugerir o melhor produto** pra uma necessidade, combinando preço, prazo
  de entrega e avaliação, não só o mais barato.
- **Comparar produtos** lado a lado, apontando quem ganha em cada critério.
- **Agendar entrega** pra uma data escolhida pelo cliente.
- **Base de conhecimento (RAG)** com busca semântica sobre tecnologia: o
  que cada especificação significa e o que olhar na hora de escolher. É o
  que permite responder "meu quarto tem 12m² e bate sol" com "9000 BTUs,
  e por isso este modelo" em vez de só listar preço.
- **2ª via de boleto ou nota fiscal** (mockado).
- **Rastreio de pedido**: código no formato dos Correios, etapa atual e
  localização.
- **Pedido que anda sozinho**: o status percorre as cinco etapas
  (confirmado, em separação, enviado, saiu para entrega, entregue) conforme
  o tempo passa, no ritmo do prazo de entrega do produto.
- **Aviso automático no chat** a cada mudança de etapa, com o código de
  rastreio quando já há o que rastrear.
- **Catálogo navegável**: vitrine com imagem, preço e ação de pedir, com
  filtro por categoria e busca.
- **Cartão de produto na conversa**: o que a Lu consultar aparece como
  cartão com ilustração, preço e botão, logo abaixo da resposta dela, em
  vez de virar parágrafo de texto.
- **Painel de pedidos**: lista os pedidos e permite rastrear, agendar
  entrega e gerar 2ª via de boleto/NF sem passar pelo chat.

## Arquitetura

Estrutura em camadas de projeto FastAPI:

```
app/
  main.py           cria o app, monta /static, registra routers
  config.py         env vars, caminhos e limites
  models.py         DDL das tabelas + constantes de domínio
  schemas.py        Pydantic: contratos de entrada e saída
  database.py       conexão PostgreSQL (psycopg) + init_db
  repositories.py   acesso a dados (mensagens, pedidos, catálogo, RAG)
  services.py       regras de negócio
  exceptions.py     erros de domínio
  vectorstore.py    índice do RAG em pgvector (embeddings + similaridade)
  routers/          views.py, chat.py, produtos.py, pedidos.py
  ai/               client.py (Groq), tools.py (function calling), chat.py (loop)
  data/catalogo.py     os 184 produtos mockados
  data/conhecimento.py base de conhecimento do RAG (52 documentos)
persona.md          system prompt da Lu
static/             frontend vanilla (HTML/CSS/JS): chat + catálogo
tests/              suíte pytest espelhando as camadas
```

Dependências fluem numa direção só:
`routers → services → repositories → database/data`, e
`routers → ai.chat → ai.tools → services`.

Sem framework de frontend (React etc.) e sem ORM por enquanto, o objetivo
agora é validar o fluxo de produto.

### Endpoints principais

Os endpoints de conversa e de pedido exigem identificação e respondem
**401** sem ela. Catálogo, categorias e base de conhecimento ficam
abertos: são da loja, não de um cliente.

| Método | Rota | O que faz |
| --- | --- | --- |
| POST | `/api/sessao` | identifica o cliente pelo telefone |
| GET | `/api/sessao` | quem está falando (401 se ninguém) |
| DELETE | `/api/sessao` | esquece o número, sem apagar a conversa |
| POST | `/api/chat` | conversa com a Lu (com tool calling) |
| GET | `/api/history` | histórico persistido da conversa |
| GET | `/api/notificacoes` | avanços de status desde a última consulta |
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
   - ~~Catálogo mockado (184 produtos, 39 categorias) + estoque~~
   - ~~Criar/consultar pedidos mockados~~
   - ~~Sugestão de produto (preço/prazo/avaliação)~~
   - ~~Comparação de produtos lado a lado~~
   - ~~Agendamento de entrega~~
   - ~~2ª via de boleto/NF (mockado)~~
   - ~~Rastreio de pedido (mockado)~~
   - ~~Tool calling ligando o chat às funções acima~~
   - ~~Catálogo navegável na UI, com filtro por categoria e busca~~
   - ~~Estrutura em camadas (routers/services/repositories/schemas/models)~~
4. ~~**RAG**, base vetorial de conhecimento sobre produtos/tecnologias pra
   fundamentar as sugestões~~
   - ~~40 documentos cobrindo as categorias do catálogo + temas gerais
     (voltagem, eficiência energética, garantia)~~
   - ~~Busca semântica com embeddings locais (`intfloat/multilingual-e5-small`)~~
   - ~~Tool `buscar_conhecimento` e endpoint `/api/conhecimento`~~
5. Dados reais, trocar mocks por integrações verdadeiras (catálogo,
   estoque, logística, financeiro) quando/se o projeto avançar pra isso.
6. ~~**Avaliação e iteração**, medir qualidade do retrieval e das decisões
   de tool calling~~
   - ~~Suíte `evals/` com 40 casos de retrieval, 8 fora de escopo e 21 de
     escolha de ferramenta~~
   - ~~Métricas com mínimo que trava build (acerto@1, acerto@3, MRR)~~
   - ~~Iteração 1: escolha de ferramenta de 77,8% para 94,4% (descrições
     de tool que empurravam pra `listar_categorias` à toa)~~
   - ~~Iteração 2: acerto@1 do retrieval de 75% para 94,2%, enriquecendo
     os documentos com as perguntas que respondem~~
7. **Levar a Lu pro WhatsApp**
   - ~~Leitura de foto do produto (modelo com visão em duas etapas)~~
   - ~~Identidade pelo telefone: sessão, cadastro e migração de quem já
     usava o app~~
   - ~~Interface de teste simulando o WhatsApp~~
   - Áudio: transcrever o que o cliente falar e responder em texto
   - Canal real: webhook do provedor escolhido, entrega e status de leitura
8. Rename final da pasta/projeto pra "Cérebro da Lu".

## Estado atual

- Chat via navegador com tool calling (Groq, `openai/gpt-oss-120b` por
  padrão, configurável via `GROQ_MODEL` no `.env`).
- 11 ferramentas disponíveis ao modelo: busca de produto, base de
  conhecimento, categorias, estoque, sugestão, comparação,
  criação/consulta/rastreio de pedido, agendamento e 2ª via.
- Histórico persistido em PostgreSQL, sobrevive a refresh, restart e redeploy.
- Catálogo, pedidos, estoque, rastreio, agendamento e 2ª via são **dados
  mockados**, pensados pra simular as integrações reais que um produto
  como esse teria no Magalu.
- Pedido criado ganha código de rastreio e avança de etapa sozinho, com
  aviso automático no chat a cada mudança.
- A busca exposta ao modelo devolve no máximo 10 produtos por vez (com o
  total encontrado), pra não estourar o contexto com 113 itens.
- Cada telefone tem a própria conversa, os próprios pedidos e o próprio
  cadastro. Não há senha nem verificação por SMS: quem digita o número
  entra, o que é adequado a uma demonstração e **não seria** num canal
  real, onde quem garante o número é o próprio WhatsApp.

### Por que cada documento tem uma lista de perguntas

O corpo dos documentos é escrito em vocabulário de especificação ("air
fryer", "voltagem", "switch azul"), mas o cliente descreve sintoma e usa
sinônimo ("fritadeira", "tomada diferente", "barulho quando digito"). Sem
uma ponte entre os dois, a busca erra justamente nas perguntas mais
naturais, o acerto@1 era de 75%.

Cada documento passou a declarar as perguntas que responde, e elas entram
no texto indexado junto do corpo. O acerto@1 subiu pra 94,2% e o acerto@3
pra 100%.

Pra garantir que isso é generalização e não memorização, as perguntas
indexadas não podem ser cópia dos casos de avaliação, há teste em
`tests/test_rag.py` que falha se alguma passar de 50% de sobreposição de
termos de conteúdo. Doze casos do conjunto foram escritos depois do
enriquecimento, justamente pra medir pergunta inédita.

### O status do pedido é derivado, não gravado

Um pedido precisa andar sozinho pela logística, mas manter isso com um job
que grava status de tempos em tempos exigiria um processo de fundo, e o
banco ficaria desatualizado sempre que o app estivesse parado.

Em vez disso a etapa é **calculada na leitura**, a partir do tempo desde a
criação do pedido sobre o prazo de entrega do produto. As quatro etapas de
trânsito dividem o prazo em fatias iguais e "entregue" começa quando o
prazo vence, ficando assim pra sempre. `SEGUNDOS_POR_DIA_ENTREGA` diz
quantos segundos reais valem um dia: com o padrão de 20, um produto de
prazo 4 percorre tudo em ~80 segundos, o que cabe numa demo; 86400 simula
tempo real. Como é função pura do relógio, `services.status_derivado()` é
testável sem esperar nada, basta passar o instante.

Agendar entrega deixou de ser status. Antes ele sobrescrevia a etapa com
"entrega agendada", que nem existe em `ETAPAS_RASTREIO`, e o rastreio
passava a devolver uma etapa fora da própria lista de etapas. São eixos
diferentes: a data combinada vive em `data_entrega_agendada` e o pedido
continua sendo separado, enviado e entregue.

O aviso no chat sai de `GET /api/notificacoes`, que compara a etapa atual
com a última já comunicada (`status_notificado`) e grava a diferença como
mensagem da Lu no histórico. É idempotente: consultar duas vezes não
duplica mensagem, e quem ficou horas fora recebe só o estado atual, não as
cinco etapas de uma vez.

Novidade é só o que está adiante do que já foi dito. Como a etapa é
derivada, ela pode recuar sem que o pedido tenha andado (a escala de
`SEGUNDOS_POR_DIA_ENTREGA` muda entre execuções, o prazo do produto
aumenta no catálogo). Nesse caso a Lu fica calada, em vez de anunciar
"confirmado" num pedido que ela já deu como entregue.

### Por que existe cadastro separado da conversa

A Lu perguntava o endereço de novo a quem já tinha informado. A causa era a
janela de histórico: o dado estava no banco, mas fora das mensagens
enviadas ao modelo.

Nome e endereço passaram a viver numa tabela `perfil` e entram no system
prompt, então continuam visíveis por quantas mensagens a conversa tiver,
por poucos tokens. A regra é essa: dado que se repete em todo pedido é
cadastro, o resto é conversa.

O telefone é a exceção: ele entra no prompt junto dos outros, mas vem da
sessão, não do cadastro, e o modelo **não pode gravá-lo**. É dado do
canal, e não do cliente: no WhatsApp o número é o remetente, ninguém
digita o próprio. Se a Lu pudesse gravar, bastaria um cliente dizer que
mudou de celular pra assumir o número, e o histórico, de outro.

### Por que a sessão é o telefone

Antes, cada navegador ganhava um id aleatório num cookie. Resolvia o
vazamento de histórico, mas era uma identidade que só existia naquele
navegador: limpar o cookie perdia a conversa, e nada disso se pareceria
com o canal de destino.

No WhatsApp a identidade **é** o número. Adotar a mesma chave aqui fez a
conversa deixar de morar no cookie e passar a morar na pessoa, e alinhou o
simulador com o canal real: o formato gravado (`5511988881234`, só dígitos
com DDI) é o mesmo `wa_id` que a Cloud API da Meta entrega no webhook, e
`app/telefone.py` normaliza qualquer jeito de digitar pra ele.

Quem já usava o app tinha cookie com id aleatório. No primeiro acesso, o
número informado adota a conversa daquele cookie, uma vez só, e só se o
número ainda não tiver dado nenhum: mesclar dois cadastros seria pior do
que não migrar, e não teria volta.

### Limites de tokens da Groq

A conta free tem **dois** tetos: 8000 tokens por minuto e 200 mil por dia.
Vale saber a diferença porque a saída não é a mesma:

- **Por minuto** é questão de ritmo. A Groq diz em quantos segundos dá pra
  tentar de novo, e o chat espera e repete em vez de devolver erro: uma
  resposta em 4 segundos é melhor que um erro imediato.
- **Por dia** é o que aparece quando se testa muito contra o modelo real,
  e libera só horas depois. Aí o cliente é avisado na hora, com o prazo,
  porque não há o que esperar dentro de uma requisição.

A mensagem diz qual dos dois foi batido. Antes ela dizia "por minuto" em
qualquer caso, e quem lia esperava um minuto e batia no mesmo erro.

#### Por que o prompt é montado em partes

A conta free trabalha com 8000 tokens por minuto. Cada requisição de chat
carrega a persona (~920 tokens) e os schemas das ferramentas (~1400) antes
de qualquer conteúdo, e esse custo é pago de novo a cada rodada de tool
calling. Somando o histórico completo, poucas trocas de mensagem bastavam
pra estourar o teto e derrubar a resposta com erro 429.

Por isso o que vai pro modelo é uma janela das últimas
`MAX_MENSAGENS_CONTEXTO` mensagens, hoje 10. O histórico completo continua
no banco e na tela, via `/api/history`. Isso levou o custo por requisição
de ~4900 tokens, crescendo sem limite, pra ~3600 com teto estável.

Quando o limite é atingido mesmo assim, a API responde 429 com uma frase
legível e o tempo de espera, em vez do JSON cru do provedor.

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

Com isso a cobertura do domínio vai a 52/52 mantendo 7/8 de rejeição.
Antes eram 49/52 e 7/8, ou seja, **3 perguntas legítimas eram respondidas
com "não tenho essa informação"**. Isso passou muito tempo despercebido
porque a avaliação media só a rejeição, nunca a cobertura; hoje mede as
duas, e elas se puxam em direções opostas de propósito.

Nenhum corte é filtro de assunto perfeito, 1 das 8 perguntas fora do
domínio ainda passa. Quem segura resposta inventada continua sendo a
persona, que manda a Lu admitir quando a base não cobre.

## Notas de desenvolvimento

- O venv roda **Python 3.9**, então anotações com `X | None` não funcionam
  em runtime, use `Optional[...]`.
- **`numpy<2` é obrigatório**: o torch disponível pra Python 3.9 (2.2.x) foi
  compilado contra NumPy 1.x e quebra com NumPy 2 ("Numpy is not
  available").
- Na primeira execução o modelo de embedding baixa (~470MB) e fica em
  cache. A carga é lazy: só acontece na primeira busca de conhecimento.
- Os testes nunca chamam a Groq (mockada) nem baixam o modelo de embedding
  (encoder falso na fixture `rag_sem_download`), e sempre usam o banco
  `cerebro_lu_test`, nunca o do app.
- Convenções e direção das dependências entre camadas estão no
  `CLAUDE.md`.
- O que ainda pode ser feito, o que já foi descartado e o critério pra
  decidir estão no `MELHORIAS.md`.
