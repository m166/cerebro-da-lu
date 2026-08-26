# CLAUDE.md

Guia para trabalhar neste repositório. Leia o `README.md` primeiro pra
contexto de produto, este arquivo é sobre como mexer no código.

Antes de propor coisa nova, passe pelo `MELHORIAS.md`: ele guarda o critério
de avaliação, os invariantes que não podem regredir, o que já foi descartado
e por quê, e o checklist do que precisa estar verde antes de dar por pronto.

## Congelamento de gastos (vigente)

**Nada neste projeto pode gerar custo no momento.** Vale pra qualquer coisa
que consuma cota paga ou compartilhada, e a regra é pedir autorização, não
pedir desculpa depois.

Em particular, **não execute sem o usuário mandar, explicitamente, na hora**:

- `python -m evals ferramentas` e `python -m evals` (~26 chamadas à Groq,
  60% a 70% da cota diária de 200 mil tokens numa execução só)
- qualquer script ou teste que chame a Groq de verdade, inclusive validação
  manual de persona, de visão ou de memória contra o modelo real
- transcrição de áudio, geração de imagem ou qualquer outra API paga
- provisionar serviço em nuvem, banco gerenciado ou fila

O que **continua liberado**, porque não gasta nada: `pytest`, o runner do
node, `python -m evals retrieval` (roda local, sem API), leitura de código,
medição de token por contagem de caracteres, e qualquer análise estática.

Consequência prática pro planejamento: passo que gasta cota entra no plano
como **passo de decisão humana**, separado e explícito, nunca embutido numa
sequência que alguém possa rodar inteira sem perceber. O `plan-specialist`
já trabalha assim.

> Este bloco é temporário e vale enquanto estiver escrito aqui. Quando o
> congelamento sair, apague a seção inteira em vez de deixá-la ambígua.

## O que é o projeto

"Cérebro da Lu" (pasta ainda `Cérebro do Matheus` durante a migração): um
assistente de e-commerce que atende via chat e usa **tool calling** pra
consultar catálogo/estoque, criar e rastrear pedidos, comparar e sugerir
produtos e gerar 2ª via de boleto/NF. Tudo hoje roda sobre **dados
mockados** (catálogo fixo em Python, pedidos em PostgreSQL), não há integração
real com sistemas do Magalu.

**O destino é o WhatsApp.** A Lu vai atender lá dentro, e isso não é um
detalhe de entrega, é o que define o produto: o cliente é identificado
pelo número, manda foto e áudio, e espera resposta de mensagem, não de
site. Por isso a tela de teste em `static/` **imita o WhatsApp** de
propósito, e a sessão é o telefone. Quando uma decisão de design tiver
duas saídas defensáveis, a que se parece com o WhatsApp ganha: o valor
desta interface é ensaiar o que o cliente vai ver de verdade.

Estado do caminho: foto já funciona (`app/ai/visao.py`), identidade por
telefone já funciona, as regras do canal já estão no código
(`app/whatsapp.py`: templates, janela de 24h, formatação, limites),
**áudio ainda não existe**, e nenhum canal real está plugado (não há
webhook, o provedor ainda não foi escolhido). O que falta pra ligar é
transporte, não formato.

## Estrutura em camadas

```
app/
  main.py           cria o FastAPI app, monta /static, registra routers
  config.py         env vars, caminhos, limites (tool iterations, busca)
  models.py         DDL das tabelas + constantes de domínio (status, etapas)
  schemas.py        Pydantic: contratos de entrada e saída da API
  database.py       conexão PostgreSQL (psycopg) + init_db e migração
  repositories.py   acesso a dados (mensagens, pedidos, catálogo, RAG)
  services.py       regras de negócio (validação, cálculo, sugestão)
  exceptions.py     erros de domínio
  vectorstore.py    índice do RAG em pgvector (lazy, análogo a database.py)
  whatsapp.py       regras da Cloud API (templates, janela, limites)
  sessao.py         o telefone da requisição (contextvar + cookie)
  telefone.py       normalização e formatação de número
  registro.py       em que tom o cliente escreve (solto, neutro, formal)
  pistas.py         orçamento e recusas lidos da fala do cliente
  abandono.py       se o cliente está desistindo (silêncio x ritmo dele)
  cupom.py          desconto limitado pela margem líquida do produto
  routers/
    views.py        serve o HTML do chat
    identificacao.py /api/sessao + a dependência exigir_identificacao
    chat.py         /api/chat, /api/history, /api/notificacoes
    produtos.py     /api/produtos, /api/categorias, sugestão, comparação,
                    /api/conhecimento
    pedidos.py      /api/pedidos + rastreio, agendamento, 2ª via
  ai/
    client.py       client da Groq (lazy, pra não exigir key nos testes)
    tools.py        TOOL_SCHEMAS + DISPATCH + executar()
    chat.py         loop de tool calling e histórico
    visao.py        descreve a foto que o cliente mandou
  data/
    catalogo.py     184 produtos mockados em 39 categorias
    conhecimento.py 52 documentos que formam o corpus do RAG
static/             simulador do WhatsApp em HTML/CSS/JS, sem framework
  formatacao.js     negrito/itálico/riscado do WhatsApp e data (com teste)
  img/fundo-conversa.svg  ladrilho de rabiscos do fundo da conversa
tests/              suíte pytest espelhando as camadas
evals/              avaliação de qualidade (modelo real + Groq)
```

### Direção das dependências

```
routers → services → repositories → database / vectorstore / data
routers → ai.chat → ai.tools → services
```

Nunca inverta isso. Em particular, `services.py` **não** importa
`ai/`, foi assim que o import circular foi evitado (tools precisa dos
services, então quem orquestra o modelo fica acima de ambos).

## Convenções

- Texto voltado ao usuário (persona, mensagens de erro, docs) em português
  do Brasil. Nomes de domínio (`produto`, `pedido`, `estoque`,
  `avaliacao`) em português; nomes de infra (`get_connection`, `router`,
  `lifespan`) em inglês, seguindo o framework.
- **Nunca use travessão (—) em nenhum texto do projeto**: docs, comentário,
  persona, mensagem de commit, texto de UI. Use vírgula, dois-pontos,
  parênteses ou duas frases. Vale também para o meia-risca (–).
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
- **Erro do modelo não é erro do sistema.** Quando ele chama uma ferramenta
  que não existe (já saiu `buscar_conocimiento`, em espanhol), a Groq
  recusa a geração com 400 `tool_use_failed`. Isso virava 502 na cara do
  cliente. Hoje `ai/chat` avisa o modelo dos nomes válidos e deixa ele
  tentar de novo, gastando uma das rodadas que o loop já limita. Quem lê o
  erro da Groq é `ai/client.ferramenta_inventada`, e só esse 400 é
  absorvido: requisição malformada é bug nosso e precisa estourar.
- **Cuide do orçamento de tokens, e são dois tetos.** A conta free da Groq
  limita **8000 tokens por minuto e 200 mil por dia**. O do dia é o que
  aparece na prática quando se testa muito: ele foi batido depois de uma
  sessão de ajuste de persona com chamadas ao modelo real, e libera só
  horas depois. Cada requisição carrega persona (~2050) mais schemas das
  tools (~1400) antes de qualquer conteúdo, ~3500 fixos por rodada, e uma
  conversa com uma chamada de ferramenta são duas rodadas.
  - Antes de validar comportamento contra o modelo real, **decida quantas
    chamadas o teste merece**: 60 chamadas de ajuste fino consomem o dia
    inteiro e deixam o app sem responder pra quem for usar depois.
  - Se precisar cortar, o freio mais rápido é a persona, o item mais caro.
    O segundo é transformar bloco fixo em injeção condicional, como foi
    feito com o tom e com a apresentação (veja `app/registro.py`). Por isso o histórico enviado
  ao modelo é uma janela (`config.MAX_MENSAGENS_CONTEXTO`), enquanto
  `/api/history` continua devolvendo tudo pra tela. Ao criar tool ou
  aumentar a persona, lembre que o custo é pago em toda rodada de tool
  calling, não uma vez por conversa.
- **Ferramenta que devolve vazio custa caro.** O modelo reformula e chama
  de novo, gastando rodada de tool calling, foi assim que a busca de
  produto, sensível a acento, derrubava a resposta por estourar o limite.
  Prefira degradar (casamento parcial, resultado aproximado) a devolver
  lista vazia.
- Sem comentários explicando o óbvio. Só quando houver decisão não óbvia
  (ex: por que a normalização do score é relativa aos candidatos).
- Sem framework de frontend, mudanças de UI são HTML/CSS/JS direto em
  `static/`.
- No frontend, nunca monte HTML por concatenação com dado vindo da API.
  Use `textContent` e `createElement` (é o padrão já seguido em
  `script.js`).
- **Não formate data com `new Date(...)` no frontend.** Uma string como
  `"2026-09-15"` é lida como UTC e, no fuso do Brasil, exibida um dia
  antes. Use `formatarData()`, que reformata a string.
- **PostgreSQL com SQL puro, sem ORM** (por isso `models.py` guarda DDL,
  não classes). O SQLite saiu porque o destino é publicar: em container o
  disco é efêmero e o arquivo `cerebro.db` ia embora a cada redeploy. Não
  introduza ORM sem necessidade real, o SQL daqui é simples de propósito.
- **O placeholder é `%s`, não `?`.** Vale pra todo parâmetro, inclusive
  `LIMIT %s`. E subconsulta em `FROM` precisa de apelido, coisa que o
  SQLite dispensava.
- Ao adicionar produto no catálogo, mantenha o mínimo de 4 por
  categoria. É o que viabiliza comparação, e há teste garantindo isso.

## Rodando e testando

> **A porta do banco deste projeto ainda não foi decidida, e por isso nada
> roda sem configuração.** Esta máquina usa a **5432 para um container de
> trabalho**, que não tem relação com este repositório e não pode ser tocado.
> O `postgresql@17` do Homebrew existe aqui mas está **parado**, e não deve
> ser ligado na 5432. `DATABASE_URL` e `DATABASE_URL_TEST` não têm valor
> padrão: a app e a suíte falham com um recado explícito se faltarem. Isso é
> trava deliberada, porque a suíte trunca tabelas a cada caso e um padrão
> conveniente apagaria o banco errado.

Precisa de um PostgreSQL com a extensão `vector` no ar, **numa porta que não
seja a 5432**:

```bash
source .venv/bin/activate
export DATABASE_URL=postgresql://localhost:$PORTA/cerebro_lu
export DATABASE_URL_TEST=postgresql://localhost:$PORTA/cerebro_lu_test
uvicorn app.main:app --reload    # app em http://localhost:8000
pytest                            # suíte de testes (usa cerebro_lu_test)
```

Atenção: o entrypoint é `app.main:app` (não `main:app`).

Do zero, em outra máquina:

```bash
createdb cerebro_lu && createdb cerebro_lu_test
for db in cerebro_lu cerebro_lu_test; do
  psql -d $db -c 'CREATE EXTENSION IF NOT EXISTS vector'
done
python -m scripts.migrar_sqlite_para_postgres   # só se houver cerebro.db antigo
```

**O `psql` do Homebrew pode não estar no PATH** (a fórmula é keg-only): os
binários ficam em `/usr/local/opt/postgresql@17/bin`.

Se o pgvector não estiver instalado, `CREATE EXTENSION` falha com "extension
vector is not available". O `brew install pgvector` recusa compilar quando o
Command Line Tools está desatualizado, e a saída daqui foi compilar direto
do fonte, apontando o include na mão porque o `pg_config` da fórmula reporta
um caminho que não existe:

```bash
make PG_CONFIG=/usr/local/opt/postgresql@17/bin/pg_config \
     PG_CPPFLAGS=-I/usr/local/opt/postgresql@17/include/postgresql/server
```

### Regras dos testes

- **Nenhum teste chama a Groq de verdade.** Use a fixture `groq_falso`
  (em `tests/conftest.py`) com os helpers `resposta_do_modelo` e
  `tool_call_falso`.
- A fixture `banco_isolado` é `autouse` e dá `TRUNCATE ... RESTART
  IDENTITY` nas tabelas do visitante antes de cada caso, lendo a lista de
  `database.TABELAS_DO_VISITANTE` em vez de repeti-la. O banco é o
  `cerebro_lu_test`, apontado já no import do `conftest.py` pra que um teste
  que escape da fixture ainda assim não escreva no banco real. Rodar a
  suíte exige um Postgres no ar.
- Não acople testes a IDs fixos de produto, use `id_por_nome("...")`,
  senão inserir um produto no meio do catálogo quebra a suíte.
- **Nenhum teste baixa o modelo de embedding.** A fixture `rag_sem_download`
  é `autouse` e troca o encoder por um saco de palavras determinístico.
  Como ele é léxico e não semântico, **não escreva teste afirmando que a
  pergunta X traz o documento Y**, isso mede o encoder falso, não o
  sistema. Qualidade semântica se verifica manualmente, com o modelo real.

## Imagens dos produtos

`static/img/<categoria>.svg` tem uma ilustração por categoria, e o produto
expõe o caminho em `imagem`. São vetores porque o catálogo é mockado e não
existe foto: pesam pouco, não borram e funcionam offline. **Trocar por foto
real é substituir o arquivo mantendo o nome da categoria**, sem tocar em
código. Categoria nova sem arquivo deixa a imagem quebrada, então crie o
SVG junto.

## Texto da Lu na tela

A tela **não renderiza markdown**: ela imita a formatação do WhatsApp, que
usa **um** marcador de cada lado (`*negrito*`, `_itálico_`, `~riscado~`).
Isso não é detalhe de estilo, é o formato do canal: `**negrito**` não é
negrito no WhatsApp, chega ao cliente com os asteriscos visíveis. A persona
já pede um asterisco, e `comFormatacao` no `script.js` renderiza a regra
real, inclusive deixando o `**` antigo aparecer torto de propósito.

Tabela com barras e lista com `#` aparecem cruas pro cliente, e a persona
proíbe tabela por isso. Os produtos que as ferramentas consultarem viram
cartão com foto e preço automaticamente (`ChatResponse.produtos`), então a
Lu não precisa repetir ficha técnica em texto.

Os ids dos produtos citados ficam gravados na coluna `messages.produtos`.
Sem isso o cartão só existia no envio ao vivo e sumia ao recarregar.

## As regras da Cloud API (app/whatsapp.py)

O canal impõe coisas que não são preferência de estilo, e ignorar qualquer
uma delas não dá bug: dá mensagem recusada pela Meta ou cliente que nunca
recebeu o aviso. Elas moram em `app/whatsapp.py`, que **não fala com a Meta
e não escolhe provedor**, só guarda o formato.

- **Fora da janela de 24 horas, texto livre não passa.** Só template
  aprovado antes. A janela conta da última mensagem **do cliente**, nunca da
  resposta da Lu, senão bastaria a loja falar sozinha pra mantê-la aberta
  pra sempre. Quem responde isso é `services.canal_aceita_texto_livre`, e o
  relógio vem de `repositories.ultima_mensagem_do_cliente`.
- **Por isso o aviso de pedido é template, não f-string.** Ele sai sozinho,
  às vezes dias depois, quase sempre fora da janela.
  `models.TEMPLATES_NOTIFICACAO` guarda os cinco, um por etapa de
  `ETAPAS_RASTREIO`, com os parâmetros posicionais (`{{1}}`) que a Meta
  exige. Se algum dia isso voltar a ser texto formatado em Python, o aviso
  passa a ser recusado em vez de entregue.
- **O texto da tela e o do canal saem do mesmo template.**
  `services._texto_da_notificacao` renderiza o mesmo objeto que
  `notificacao_para_envio` manda pra API. Escrever a frase em dois lugares
  seria a divergência mais cara possível: o cliente recebe uma mensagem
  aprovada meses antes e o histórico mostra outra.
- **Categoria é preço.** Os cinco são UTILITY: seguem uma ação do cliente e
  não vendem nada. Acrescentar "aproveite" ou link de vitrine faz a Meta
  reclassificar como MARKETING, que custa mais e exige opt-in. Desde abril
  de 2025 essa reclassificação é automática.
- **Parâmetro casa por posição, não por nome.** Trocar a ordem da lista em
  `parametros` troca o conteúdo na tela do cliente sem erro nenhum. Por isso
  `Template` valida na definição, e os testes conferem a ordem do payload.
- **Nome de template é minúsculo com underscore**, e o idioma é `pt_BR`.
- Limites que a Meta impõe (todos em constantes no módulo): corpo de
  template 1024, texto livre 4096, cabeçalho e rodapé 60, botão 20, no
  máximo 3 botões de resposta, lista com até 10 linhas de 24 caracteres.

**Um alerta de prazo:** até 30 de setembro de 2026, mensagem livre dentro da
janela de 24h é grátis. **A partir de 1º de outubro de 2026 a Meta passa a
cobrar por mensagem de serviço também**, na mesma tarifa de utility. Isso
muda a conta de operar a Lu, não o código.

## O simulador do WhatsApp

**Ele não vai pro ar junto com a app.** `config.SIMULADOR_ATIVO` (env
`SIMULADOR`, 1 local e 0 publicado) desliga duas coisas de uma vez: a tela e
o `POST /api/sessao`. O segundo é o que importa, porque é ele que deixa
qualquer pessoa dizer "sou este número" e cair na conversa daquele cliente,
sem verificação nenhuma. Tirar só o HTML e deixar o endpoint seria teatro de
segurança, bastaria um curl. O `Dockerfile` nem copia `static/` pra imagem.

Publicada sem simulador, a app responde 401 em tudo que é do cliente e
continua servindo catálogo e conhecimento, que são da loja. **Isso é o
comportamento correto, não uma falta:** quem vai informar o número é o
webhook do WhatsApp, no envelope da mensagem, e esse transporte ainda não
existe. Testes em `tests/test_simulador_desligado.py`.

`static/` é um clone visual do WhatsApp, e as escolhas seguem o app, não o
gosto de quem mexe. O que já foi decidido assim, e por quê:

- **A moldura é um celular** (`.aparelho`, 480px no máximo, centralizada).
  Abaixo de 560px ela some e a tela vira o aparelho, como no celular.
- **Sem avatar por mensagem.** O WhatsApp só mostra foto ao lado do balão
  em grupo; numa conversa de duas pessoas, avatar em cada balão entrega
  que a tela não é o app.
- **"digitando..." vai no cabeçalho**, no lugar do "online". Balão de três
  pontinhos não existe no WhatsApp.
- **Aviso de pedido é balão comum da Lu**, com um 📦 na frente. A versão
  anterior usava cartão amarelo com rótulo, que o canal real nunca
  mostraria. O campo `tipo` continua separando os dois no banco.
- **Catálogo e pedidos abrem como folha por cima da conversa**, saindo do
  menu `⋮`. Não viram aba no cabeçalho, que é onde o WhatsApp não tem
  nada disso.
- **Rabicho do balão só na primeira mensagem da sequência** (classe
  `abre-sequencia`), como o app faz.
- Ícones de chamada no cabeçalho são `<span>`, não `<button>`: são
  cenário, e botão que não faz nada é pior que enfeite assumido.
- A **barra do simulador** no topo é o contrário disso tudo, escura e sem
  cara de WhatsApp de propósito: é a fronteira entre o que o cliente veria
  e o que é andaime de teste. Nada que o cliente veria pode morar lá.

As cores em `:root` são as do WhatsApp de verdade (`#008069`, `#d9fdd3`,
`#005c4b`, `#0b141a`), não aproximações. Trocar uma delas por "um verde
parecido" corrói o motivo de a tela existir.

## Testando o frontend

São duas coisas, e uma não substitui a outra.

**Lógica pura tem teste automatizado.** `static/formatacao.js` guarda o que
é testável sem navegador (a formatação do WhatsApp e `formatarData`) e roda
no runner embutido do node, sem instalar nada:

```bash
node --test tests/frontend/formatacao.test.js
```

O `pytest` também roda esses testes, via `tests/test_frontend.py`, e pula
quando não há node na máquina. Não deixe essa ponte cair: enquanto o
frontend só era conferido por screenshot, passou despercebido um negrito
que atravessava quebra de linha, porque a guarda perguntava "começa e
termina com o mesmo marcador?" em vez de "casou com a regex?".

**O resto se olha.** Não há playwright, e Chrome headless não clica, mas
tirar screenshot **pega o que teste de API não pega** (foi assim que
apareceu uma data de entrega exibida um dia antes).

```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless=new --disable-gpu --hide-scrollbars \
  --window-size=980,900 --screenshot=/tmp/lu.png \
  --virtual-time-budget=7000 \
  "http://localhost:8000/?telefone=11988881234#catalogo"
```

Headless não clica, então tudo é alcançado pela URL:

- **`?telefone=` identifica a sessão no carregamento.** Sem ele o print sai
  da tela de entrada, porque o navegador limpo não tem cookie. Serve
  também pra abrir dois clientes em abas diferentes sem preencher
  formulário.
- `#catalogo` e `#pedidos` abrem a folha correspondente.
- Pra conferir o tema claro, acrescente
  `--blink-settings=preferredColorScheme=1`.

**Não fotografe a instância que você está usando.** Suba outra com
`DATABASE_URL` apontando pra um banco descartável, senão o print grava
sessão e pedido no banco de verdade:

```bash
createdb -p $PORTA demo_lu && psql -p $PORTA -d demo_lu -c 'CREATE EXTENSION vector'
DATABASE_URL=postgresql://localhost:$PORTA/demo_lu uvicorn app.main:app --port 8020
```

**Cuidado com `--window-size` abaixo de 500.** O Chrome headless tem
largura mínima de 500px e ignora valores menores: o print sai cortado em
390 e parece transbordamento de layout, mas a página nunca foi renderizada
nessa largura. Já perdi tempo "consertando" um bug que não existia. Pra
testar tela estreita de verdade, sirva uma página com a app dentro de um
`<iframe>` da largura desejada e fotografe essa página.

Esse `<iframe>` precisa vir **da mesma origem** da app (por exemplo um
arquivo temporário em `static/`). Servido de `file://`, o Chrome trata o
cookie de sessão como de terceiro e descarta: a app aparece pedindo o
número de novo e parece bug de identificação, quando é só o harness.

## Testes x avaliação

São coisas diferentes e não devem se misturar:

- **`tests/`** verifica que o código funciona. Roda em segundos, é
  determinístico, não chama a Groq nem baixa modelo. Toda mudança de
  código passa por aqui.
- **`evals/`** mede se a Lu **acerta**: retrieval e escolha de
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
- **Ferramenta inventada conta como caso errado, não derruba a execução.**
  O modelo às vezes chama um nome que não existe (já saiu
  `buscar_conocimiento`, em espanhol) e a Groq responde 400
  `tool_use_failed`. Antes isso abortava a avaliação no meio e perdia os
  casos já medidos. Só esse 400 é absorvido: requisição malformada
  continua estourando, senão um erro de schema nosso viraria 21 falhas
  silenciosas.
- Ao adicionar caso, escreva a pergunta **como um cliente falaria**, com
  gíria e sem acento. Usar as palavras do título do documento infla a
  métrica e não mede nada.
- Se um caso falhar, considere que a expectativa pode estar errada antes
  de mexer no sistema, já aconteceu de o caso pedir tool onde a persona
  manda perguntar primeiro.

## A sessão é o telefone

`sessao_id` é o número do cliente em forma canônica (`5511988881234`), e
`messages`, `pedidos` e `perfil` são filtrados por ele. Não é um id
inventado: no WhatsApp a identidade **é** o número, é ele que liga a
mensagem de hoje à conversa de três meses atrás, e usar a mesma chave aqui
faz o simulador exercitar o caminho que o canal real vai usar. O formato
com DDI e só dígitos é o mesmo do `wa_id` da Cloud API da Meta.

- O número vive num **contextvar** preenchido por middleware
  (`app/sessao.py`), não passa de camada em camada. As ferramentas são
  chamadas pelo modelo, que não conhece sessão, então o parâmetro
  contaminaria vinte assinaturas com um detalhe de transporte.
- **Toda consulta nova a essas tabelas precisa filtrar por
  `sessao.atual()`.** Esquecer é vazar dado de um cliente pro outro, e o
  teste não pega sozinho: escreva o caso em `test_routers.py` junto.
- **Normalize sempre com `app/telefone.py`.** "(11) 98888-1234" e
  "+5511988881234" são a mesma pessoa; sem normalizar, cada formatação
  vira um cliente diferente com conversa própria.
- Fora de requisição (script, teste de unidade) a sessão é `"local"`, que
  não é telefone de propósito: nada que rode fora do canal cai na conversa
  de um cliente de verdade.
- **O middleware define a sessão em toda requisição, inclusive como
  `None`.** Se não definisse, uma requisição sem cookie herdaria o
  contextvar de outra e passaria por identificada de carona.

### Quem exige identificação, e quem não

O middleware só transporta. Quem barra é a dependência
`routers.identificacao.exigir_identificacao`, aplicada no router inteiro
de `chat` e de `pedidos`. Catálogo, categorias e base de conhecimento
ficam abertos: são da loja, não de um cliente, e pedir telefone pra ver a
vitrine seria cadastro na frente de quem só quer olhar.

Sem identificação a API responde **401**, e o frontend mostra a tela de
entrada. Ao criar endpoint que toque nas tabelas do visitante, ponha
ele num desses routers ou repita a dependência.

### Migrações que exigem cuidado

**Conferir contagem não é conferir migração.** Ao trazer o `cerebro.db` pro
Postgres, o app já tinha gravado duas mensagens novas com id 1 e 2, os
mesmos ids do SQLite. O `ON CONFLICT DO NOTHING` descartou as duas
mensagens antigas em silêncio, e o total final bateu por coincidência (72
migradas + 2 novas = 74, que era exatamente o que a origem tinha). O
`scripts/migrar_sqlite_para_postgres.py` hoje remaneja quem já está no
destino antes de inserir, e confere `origem + o que já havia = destino`.
Ao escrever qualquer migração, **compare identidade de linha, não só
quantidade.**

**Id inserido à mão não avança a sequência.** Preservar o id do pedido é
obrigatório (o cliente já viu "#2" no chat, e a coluna é `GENERATED BY
DEFAULT AS IDENTITY` justamente pra permitir isso), mas depois disso é
preciso `setval(pg_get_serial_sequence(...))`, senão o próximo INSERT
colide. Vale pro script e pra qualquer fixture que finja um banco migrado.

Linhas gravadas antes das sessões ficam com `sessao_id` NULL e são adotadas
por quem se identificar primeiro (`adotar_dados_orfaos`). Acontece uma vez
só, então não teste isso contra o banco real: a adoção é consumida por quem
chegar primeiro, inclusive um `curl` seu.

Cookie gravado antes do telefone guarda um id aleatório. Ele não vale como
sessão, e `database.transferir_sessao` leva a conversa daquele id pro
número no primeiro `POST /api/sessao`. Duas salvaguardas importam:

- **Quem diz de onde transferir é o cookie do próprio navegador**, não uma
  varredura do banco. É a diferença entre mover a conversa certa e
  despejar a de todo mundo no primeiro que digitar um número.
- **Só transfere pra número que ainda não tem nada.** Mesclar dois
  cadastros seria pior que não migrar, e não dá pra desfazer. Por isso
  trocar de número no simulador não leva histórico junto: é outra pessoa.

## Cadastro do cliente x histórico de conversa

Nome e endereço ficam na tabela `perfil`, não na conversa, e entram no
**system prompt** por `ai/chat._instrucoes()`. O motivo é concreto: o
histórico enviado ao modelo é uma janela
(`MAX_MENSAGENS_CONTEXTO`), então o endereço informado vinte mensagens
atrás sai de vista e a Lu pergunta de novo. Já aconteceu.

A regra pra decidir onde guardar: **dado que se repete em todo pedido é
cadastro; o resto é conversa.** Ao acrescentar um campo, coloque em
`models.CAMPOS_PERFIL`, senão `salvar_dado_do_cliente` recusa.

**O telefone é a exceção, e de propósito.** Ele aparece no prompt junto de
nome e endereço, mas vem da sessão (`services.telefone_do_cliente`), não do
`perfil`, e **não está em `CAMPOS_PERFIL`**. É dado do canal: no WhatsApp o
número é o remetente, ninguém digita o próprio. Deixar o modelo gravar por
cima abriria a porta pra um cliente assumir o número, e o histórico, de
outro só dizendo que mudou de celular.

`criar_pedido` grava o endereço informado e usa o cadastrado quando vem
vazio. Pra quem já comprou antes de existir a tabela, `dados_do_cliente`
cai no endereço do último pedido.

## Quando a Groq recusa: 429

`ai/client` lê o corpo do erro e devolve dois fatos: **quanto esperar** e
**qual teto foi batido** (minuto ou dia). Os dois importam:

- **O prazo vem em formatos diferentes**: `800ms`, `4.5s` e `22m2.784s`. A
  primeira versão do parser só entendia segundos, então o limite diário
  devolvia `None` e a mensagem saía sem prazo nenhum. No casamento das
  unidades, `ms` precisa vir antes de `m`, senão "800ms" vira 800 minutos.
- **O teto do minuto merece espera; o do dia, não.** Passar do teto por
  minuto é questão de ritmo, e a Groq costuma pedir poucos segundos:
  `ai/chat._completar` dorme e tenta de novo, porque devolver erro ali joga
  fora uma resposta que estava a quatro segundos de existir. Teto do dia
  libera em horas, então vira aviso na hora.
- **A mensagem tem que dizer qual teto foi.** Ela dizia "limite por minuto"
  em qualquer caso, e o que apareceu de verdade foi o do dia: quem lia
  esperava um minuto e batia no mesmo erro sem entender.

As mensagens reais da API estão copiadas em `tests/test_limite_da_groq.py`,
que é o lugar de acrescentar formato novo se a Groq mudar o texto.

## O tom da Lu é decidido em código, não pedido na persona

A Lu espelha o jeito do cliente: gíria com quem escreve solto, formal com
quem escreve formal. **Isso não funcionou como instrução de persona.**
Foram três rodadas reforçando o texto (regra, exemplo dos dois extremos,
declaração no primeiro parágrafo) e o modelo continuou respondendo neutro
a "eae lu, blz? mano to precisando de um fone".

O que resolveu foi `app/registro.py`: detectar o registro por marcador de
vocabulário e injetar uma frase resolvida no system prompt ("o cliente está
escrevendo solto, responda no mesmo tom"). Na primeira tentativa a resposta
veio "Eae! Pra academia um fone in-ear...".

A lição vale além do tom: **a persona é grande e cheia de regra que dispara
em toda mensagem** (comece pela resposta, teto de 400 caracteres, uma ideia
por mensagem). Orientação de estilo enterrada no meio disso perde. Quando o
modelo precisa ter algo em vista toda rodada, entregue resolvido no prompt,
como já é feito com o cadastro do cliente.

Detalhes que importam:

- **O tom é lido só das falas do cliente**, nunca das da Lu. Incluir as
  dela criaria eco: responderia solto porque respondeu solto antes, mesmo
  depois de o cliente mudar de tom.
- **Mensagem sem marcador não zera o registro.** "Quanto custa?" no meio de
  uma conversa solta continua solta, então a detecção olha pra trás na
  janela até achar sinal.
- **Neutro não gera instrução**, de propósito: mandar "responda neutro"
  gastaria token pra repetir o padrão da persona.
- O system prompt é montado em partes por `ai/chat._instrucoes()`: persona,
  tom, cadastro. Ao acrescentar um bloco, lembre que ele é pago em toda
  rodada de tool calling.

## O que a Lu lembra da conversa

A janela de histórico (`MAX_MENSAGENS_CONTEXTO`) corta, e o que saiu de vista
some pro modelo. O cadastro resolveu isso pro que é permanente. A tabela
`memoria` resolve pro que vale só nesta compra: orçamento, o que foi
descartado e pra quem é. São tabelas separadas de propósito, porque o "meu
limite é 2 mil" de março não pode valer em setembro.

O bloco entra no system prompt por `ai/chat._o_que_ja_rolou`, e **só quando
há algo**, pela mesma regra do tom neutro: não se gasta token dizendo que não
se sabe nada.

O conteúdo vem de três origens, e a ordem entre elas foi decidida medindo:

- **Lido do texto** (`app/pistas.py`), pro orçamento e pras recusas. Ganha do
  que o modelo anotou, porque é sempre a fala mais recente.
- **Derivado do banco**, pros produtos já mostrados: os ids já estão em
  `messages.produtos`. Dado que dá pra derivar não deve depender de o modelo
  lembrar de gravar.
- **Anotado pelo modelo** (`anotar_da_conversa`), pra finalidade da compra e
  pra recusa de marca ("nada da Samsung"), que nenhum padrão de texto pega.

**Por que existe leitura em código se já existe a ferramenta.** Foi medido
com o modelo real: pedindo "meu orçamento é no máximo 2 mil" sozinho, ele
anota; dizendo "meu limite é 2 mil, quero um notebook pra faculdade", ele
chama `buscar_produtos` e o orçamento se perde. Recusa ele não anotou em
nenhuma tentativa. É a mesma lição do tom: **o que precisa valer em toda
rodada não pode depender de o modelo lembrar.**

Em `pistas.py` a regra é **não achar nada é aceitável, achar errado não é**.
Orçamento inventado faz a Lu esconder produto que o cliente podia comprar.
Por isso número só conta com marcador de limite perto ("gastei 2 mil no
último" não é teto), e recusa só casa com palavra específica do produto
medida contra o catálogo inteiro ("não quero notebook" é categoria, não
modelo).

## Cupom de desconto, e por que ele quase nunca sai

O desconto é **fatia da margem líquida, nunca do preço**. Produto de R$ 2.000
com margem de R$ 400 aceita, a 30% da margem, R$ 120. Quem raciocina em
"porcentagem de desconto" daria 30% do preço, R$ 600, numa venda que só tem
R$ 400 de lucro: R$ 200 de prejuízo por unidade. `app/cupom.py` existe pra
que essa conta não seja feita à mão nunca mais.

- **A margem mora em `catalogo.MARGEM_POR_CATEGORIA`**, por categoria e não
  por produto, porque o catálogo é mockado. Numa integração real ela vem do
  ERP por SKU. Categoria sem percentual cai num padrão conservador em vez de
  estourar.
- **Consequência que surpreende:** em eletrônico caro o desconto possível é
  pequeno em percentual. O notebook de R$ 4.899 aceita R$ 102 (2,1%), o mouse
  de R$ 249 aceita 9%. Cupom converte melhor onde a margem é gorda.
- **Margem magra não gera cupom**, e isso é resposta e não falha:
  `DESCONTO_MINIMO_RELEVANTE` barra oferta que não convence ninguém.
- **Arredonda pra baixo**, sempre.

### A trava está em código, não na persona

`services.oferecer_cupom` **verifica o abandono ele mesmo e recusa**. A regra
"nunca antes de o cliente estar desistindo" não pode viver na persona: este
projeto já mediu duas vezes que o modelo ignora instrução quando está ocupado
(foi assim com o tom e com `anotar_da_conversa`). O modelo decide *se pede*,
nunca *quanto*, e a persona só o proíbe de mencionar desconto antes de ter um
código na mão.

Outras travas, todas testadas: teto de cupons por conversa, um cupom aberto
por produto, cupom que não vale pra outro produto, resgate único (o UPDATE
condicional decide quem chegou primeiro), e validade curta.

### Como o abandono é detectado

`app/abandono.py` compara o silêncio atual com o **ritmo daquela pessoa**,
medido pela mediana dos intervalos dela. Limiar fixo erraria nos dois
sentidos: quem responde uma vez por dia não abandonou nada em 8 horas, e quem
respondia em 5 minutos e sumiu há 8 horas provavelmente desistiu. Mediana e
não média, senão uma pausa pra dormir mascara todo silêncio depois.

Há piso (6h) e teto (2 dias) absolutos, e duas travas: conversa sem interesse
demonstrado não abandona nada, e quem já comprou não abandonou.

**No WhatsApp o cupom é template MARKETING**, não UTILITY. Ele sai dias depois
da última fala, ou seja, fora da janela de 24h, e oferecer desconto é
promocional por definição. Isso custa mais por mensagem e exige opt-in.

## Medir o que está errando

O sistema **aponta, não conserta sozinho**, e a escolha está registrada:
mudança automática de comportamento precisa de uma régua contínua pra
detectar regressão, e a deste projeto (`evals/`) roda sob demanda. Foi ela
que pegou 12 documentos derrubando o retrieval em 14 pontos sem nenhum teste
falhar.

- **`satisfacao`** guarda o que o cliente declarou (nota de 1 a 5).
- **`eventos`** guarda o que o sistema observou: pergunta que o RAG não
  respondeu, abandono, cupom oferecido e usado. Uma tabela só com `tipo`,
  porque são todos "aconteceu isto, nesta conversa, nesta hora".
- **O sinal mais barato e mais acionável** é a pergunta sem resposta:
  `buscar_conhecimento` registra toda vez que nada passa do corte, e
  `perguntas_sem_resposta` devolve isso agrupado por frequência. É a fila de
  documentos a escrever, priorizada por demanda real em vez de palpite.
- `services.diagnostico` transforma isso em ações ordenadas por impacto.
- **Telemetria falha em silêncio** (`registrar_evento` engole exceção): se o
  banco recusar a escrita, o cliente ainda recebe a resposta dele.

`/api/diagnostico` mostra reclamação e taxa de abandono, que é dado de
operação. Como não existe login de operador, ele acompanha o simulador e não
sobe em produção. Quando houver autenticação, é ela que entra no lugar da
flag.

## Status do pedido é derivado, não guardado

O pedido percorre sozinho as cinco etapas de `models.ETAPAS_RASTREIO`, e
isso funciona sem nenhum job em segundo plano: `services.status_derivado`
calcula a etapa a partir de `data_criacao`, do `prazo_entrega_dias` do
produto e de `config.SEGUNDOS_POR_DIA_ENTREGA`. Consequências práticas:

- **A coluna `status` é cache, não fonte da verdade.** Quem manda é o
  cálculo. Não escreva regra que leia `status` do banco esperando que
  esteja em dia.
- `SEGUNDOS_POR_DIA_ENTREGA` vale 20 por padrão pra que a demo mostre um
  pedido chegando em cerca de um minuto. Coloque 86400 pra tempo real.
- `status_derivado` aceita `agora` justamente pra que teste não precise de
  `time.sleep`. Use isso, teste com relógio real fica lento e instável.
- **Agendar entrega não mexe no status.** São coisas diferentes: uma é a
  etapa da logística, a outra é a data combinada. Já houve bug por
  misturar as duas, com a etapa atual caindo fora de `ETAPAS_RASTREIO`.

`services.sincronizar_notificacoes` compara a etapa calculada com
`status_notificado` e escreve no histórico do chat quando mudou. É
idempotente por causa dessa coluna. Note que ela avisa a etapa **atual**:
se o cliente ficou fora e o pedido pulou de "confirmado" pra "entregue",
sai um aviso só, não quatro.

Quem dispara a sincronização é a consulta a `/api/notificacoes`, feita
pelo frontend. Sem alguém consultando, ninguém percebe que o pedido andou.

## Migração de schema

`CREATE TABLE IF NOT EXISTS` não adiciona coluna em banco que já existe.
Coluna nova entra em `models.COLUNAS_ADICIONADAS` e o
`database._migrar_colunas` aplica com `ALTER TABLE ... ADD COLUMN IF NOT
EXISTS`. É idempotente e roda no `init_db`. Sem isso, um banco já publicado
quebra depois de atualizar o código.

## O que o Postgres mudou no schema

Três pontos onde a tradução do SQLite não foi mecânica, e que estão
comentados no `models.py`:

- **`perfil` usa `UNIQUE NULLS NOT DISTINCT`, não PRIMARY KEY.** O SQLite
  aceitava NULL em coluna de PK (peculiaridade dele), e a linha órfã, de
  antes das sessões, depende disso. O Postgres impõe NOT NULL em toda PK,
  então a restrição virou UNIQUE, que aceita o NULL e ainda serve de alvo
  pro `ON CONFLICT` do upsert de cadastro.
- **Data é `TIMESTAMPTZ`, e o app continua falando string.** Quem converte
  é `repositories._linha`, na fronteira. Ao gravar data direto por SQL
  (teste, script, psql), **passe datetime com fuso**: string sem fuso é
  lida no fuso da sessão e, no Brasil, desloca o pedido em três horas, o
  que faz o rastreio pular etapa.
- **`messages.produtos` é JSONB.** O driver devolve a lista pronta, então
  não existe mais `json.loads` na leitura.

## Sobre o RAG

- `vectorstore.py` é infraestrutura (o análogo de `database.py`): carrega
  o modelo de forma lazy, porque ele tem centenas de MB. `bm25.py` é o
  índice léxico que ele usa junto.
- **O vetor mora no pgvector, o documento mora no código.**
  `data/conhecimento.py` continua sendo a fonte da verdade, e
  `conhecimento_vetores` é cache derivado dele: cada linha guarda uma
  impressão (hash) do texto indexado, e `_garantir_indice` reencoda só o
  que mudou. Editar um documento basta, não há passo manual de reindexar.
- **Trocar o encoder obriga a reindexar, e isso é código, não disciplina.**
  A impressão do texto não muda quando o modelo muda, então
  `definir_encoder` marca o índice pra refazer. Sem isso a busca compararia
  pergunta de um modelo com documento de outro, devolvendo vizinho aleatório
  sem erro nenhum.
- **Não há índice HNSW nem IVFFlat, de propósito.** Com 52 documentos o
  planejador faz varredura sequencial de qualquer jeito, e ANN é
  aproximado: criar um só perderia recall. O gatilho pra criar é o corpus
  passar de alguns milhares.
- **O `LIMIT k` não está no SQL**, também de propósito: o `score_fusao`
  compara posições nos dois rankings, e posição só existe olhando o corpus
  inteiro. Quando o corpus crescer, é aí que o LIMIT entra e o `score_fusao`
  sai.
- A troca de numpy por pgvector foi conferida: os scores batem até 1,6e-07
  (precisão de float32) e a ordenação é idêntica. Os 94,2% medidos valem.
- **Ordenação é semântica; o BM25 filtra.** Medido: semântica pura acerta
  94,2% em 1º contra 92,3% do RRF. Se for mexer nisso, meça de novo, o
  `score_fusao` continua exposto pra facilitar.
- **O corte de relevância é OU, não E.** Os sinais falham em casos
  opostos (sintoma = cosseno baixo e léxico alto; pergunta curta = o
  contrário). Trocar por E derruba a cobertura do domínio.
- O modelo é da família **E5**, que exige os prefixos `query:` e
  `passage:`, sem eles a qualidade cai bastante. Os prefixos estão em
  `config.py` e são aplicados no `vectorstore.py`.
- `SCORE_MINIMO_CONHECIMENTO` é um piso fraco, calibrado empiricamente.
  Com o E5 as distribuições de pergunta no domínio e fora dele se
  sobrepõem, então **ele não é filtro de assunto confiável**, quem segura
  resposta inventada é a persona. Se trocar de modelo, recalibre.
- Documento novo em `conhecimento.py` com `categoria` preenchida precisa
  usar uma categoria que exista no `catalogo.py`, senão o filtro nunca o
  encontra (há teste garantindo isso).
- **Documento novo tem que ter o tamanho dos que já existem** (~400
  caracteres, nunca mais que ~500). Isto foi medido, não é estilo: ao
  acrescentar 12 documentos com ~820 caracteres cada, o acerto@1 caiu de
  94,2% pra **80,8%**. Texto longo cobre vocabulário demais, o vetor deixa
  de apontar pro assunto e o documento vira ímã genérico. Enxugar os mesmos
  12 pra ~400 devolveu a métrica pra 92,3%.
- **Pergunta indexada precisa do substantivo do domínio.** Sintoma puro em
  primeira pessoa ("vivo perdendo a chave de casa") faz o E5 casar pela
  forma da frase, e o documento passa a vencer qualquer queixa pessoal: o de
  segurança roubou casos de bateria de celular, teclado silencioso e
  relógio de corrida. "fechadura que abre com digital em vez de chave"
  mantém a voz do cliente e ancora o assunto.
- **Todo documento declara `perguntas`** (mínimo 3), que entram no texto
  indexado. É o que liga o vocabulário de especificação do corpo ao de
  sintoma do cliente, foi o que levou o acerto@1 de 75% pra 94,2%. Ao
  criar documento, escreva as perguntas incluindo sinônimos populares
  ("fritadeira" pra air fryer, "tomada" pra voltagem).
- **Não copie caso do `evals/` pra dentro das `perguntas`.** Isso vira
  memorização e a métrica deixa de significar algo; há teste que falha se
  a sobreposição de termos de conteúdo passar de 50%.

## Agentes especialistas

Subagentes dedicados em `.claude/agents/`:

- **software-engineer**: a pilha inteira. `app/` (services, repositories,
  routers, schema do PostgreSQL, tool calling e prompts) e `static/` (chat,
  catálogo, formatação do WhatsApp). Nasceu da fusão de dois agentes
  separados, `backend-genai-specialist` e `frontend-specialist`: a divisão
  não se sustentava, porque quase toda mudança de produto aqui atravessa as
  duas pontas (o cartão de produto é `ChatResponse.produtos` no backend e
  `criarBalao` no frontend, e a formatação do WhatsApp mora na persona e no
  `formatacao.js` ao mesmo tempo).
- **plan-specialist**: transforma um item do `MELHORIAS.md` em plano de
  execução, com ordem, riscos, medição e critério de pronto. **Não
  implementa**, entrega o plano que o `software-engineer` executa.
- **test-specialist**: suíte pytest, fixtures e mocks da Groq.
- **git-specialist**: commits, branches, conflitos.

Prefira delegar pro especialista quando a tarefa for claramente da área
dele.

**Subagente não invoca subagente nesta configuração** (nenhum deles tem a
ferramenta `Agent`). Por isso o `plan-specialist` marca o responsável em
cada passo do plano, e quem coordena a sessão é que delega. O caminho normal
é: escolher o item no `MELHORIAS.md`, pedir o plano ao `plan-specialist`,
revisar, e só então mandar os passos pro `software-engineer` e pro
`test-specialist`.
