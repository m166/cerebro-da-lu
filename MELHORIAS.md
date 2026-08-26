# MELHORIAS.md

Onde se decide **o que entra no projeto e o que não entra**. O `README.md`
conta o que o produto é, o `CLAUDE.md` diz como mexer no código, e este
arquivo responde a pergunta anterior a essas duas: vale a pena mexer?

Existe porque um projeto que já funciona tem mais a perder do que a ganhar
com mudança apressada. A régua aqui é dupla: **o que agrega** e **o que não
pode ser quebrado no caminho**.

---

## 1. Como avaliar uma ideia

Toda proposta passa por cinco perguntas, nesta ordem. Reprovar em qualquer
uma basta pra parar, e a ordem importa: as primeiras são baratas de
responder e matam a maioria das ideias antes de custar tempo.

**1. Que problema real isso resolve, e como sabemos que ele existe?**
Problema observado vence problema imaginado. "O RAG não cobre 12 categorias"
é um fato medido. "Seria bom ter cache" é um palpite. Se não houver
evidência, o primeiro trabalho é medir, não construir.

**2. Dá pra medir antes e depois?**
Sem número, não há como saber se melhorou nem como saber se piorou. Este
projeto tem duas réguas prontas: a suíte (`pytest`) e a avaliação
(`python -m evals`). Melhoria que não encosta em nenhuma das duas precisa
trazer a sua própria medição junto.

**3. O que isso pode quebrar?**
Responda antes de escrever código, não depois. A seção 2 lista o que já foi
medido e não pode regredir.

**4. Custa token, latência ou dinheiro por requisição?**
A conta free da Groq dá **8000 tokens por minuto e 200 mil por dia**, e hoje
já se gastam **~4.570 fixos por rodada** (persona ~2.359, ferramentas ~2.163,
tom ~50). Ferramenta nova, bloco novo no prompt e documento novo são pagos em
**toda rodada de tool calling**, não uma vez por conversa.

Esse número vem subindo e merece atenção: era ~3.500 antes das ferramentas de
cupom e satisfação e das regras novas de persona. Com duas rodadas por
mensagem, uma conversa já encosta no teto do minuto. **Meça este valor sempre
que acrescentar ferramenta ou parágrafo de persona**, e trate crescimento sem
contrapartida como regressão:

```bash
python -c "
import json; from app import config; from app.ai import tools
print(len(config.persona())//4 + len(json.dumps(tools.TOOL_SCHEMAS, ensure_ascii=False))//4)"
```

**5. Dá pra desfazer?**
Mudança reversível pode ser tentada com medição e revertida. Irreversível
(migração de dado, mensagem enviada ao cliente, desconto concedido) precisa
de conferência de identidade de linha, não de contagem, e de aprovação
explícita.

### O caso que justifica esse rigor

Doze documentos novos foram acrescentados ao RAG pra cobrir categorias
descobertas. Objetivo legítimo, execução plausível, **e a suíte inteira
passou**. Só a avaliação mostrou que o acerto@1 tinha caído de **94,2% para
80,8%**, porque os documentos eram longos demais e viraram ímãs genéricos.
Enxugar devolveu para 92,3%.

A lição não é "não mexa no RAG". É que **teste verde não é prova de que
melhorou**, e que sem a régua certa a degradação teria ido para produção
sem ninguém perceber.

---

## 2. O que não pode ser comprometido

São os invariantes. Qualquer mudança que encoste neles precisa medir antes
e depois, e o número tem que voltar igual ou melhor.

| Invariante | Onde se mede | Valor atual |
| --- | --- | --- |
| Retrieval acerta em 1º | `python -m evals retrieval` | 92,3% (mínimo 88%) |
| Retrieval acerta em 3 | idem | 98,1% (mínimo 96%) |
| Escolha de ferramenta | `python -m evals ferramentas` | **desatualizado**, veja abaixo |
| Suíte de testes | `pytest` | 392 verdes + ~50 escritos sem rodar |
| Formatação da tela | `node --test tests/frontend/` | 12 casos |

**Dois desses números não valem hoje, e isso é dívida, não detalhe:**

- **A escolha de ferramenta foi medida com 13 ferramentas.** Hoje são 15, e as
  duas novas (`oferecer_cupom`, `registrar_satisfacao`) nunca passaram pela
  régua. Além disso, **4 das 15 não têm nenhum caso de avaliação**:
  `oferecer_cupom`, `registrar_satisfacao`, `anotar_da_conversa` e
  `salvar_dado_do_cliente`. Ferramenta a mais no manual é distração a mais na
  hora de escolher, então acrescentar duas pode ter degradado as outras sem
  ninguém ver. Enquanto `python -m evals ferramentas` não rodar de novo, essa
  linha é ficção.
- **A suíte não roda desde que o banco foi desligado.** Os ~50 casos de
  cupom, abandono e qualidade estão escritos e nunca foram executados.

Um invariante que não é medido deixa de ser invariante. Restaurar essas duas
medições vem antes de qualquer funcionalidade nova.

Além dos números, cinco regras que já custaram caro pra descobrir:

- **Dado de um cliente nunca aparece pro outro.** Toda consulta às tabelas
  de `database.TABELAS_DO_VISITANTE` filtra por `sessao.atual()`. Tabela
  nova entra naquela tupla ou vaza, e o teste não pega sozinho.
- **O simulador não vai pro ar.** Ele deixa qualquer um assumir qualquer
  número. Publicá-lo é vazar conversa alheia.
- **Desconto nunca ultrapassa a fração da margem.** Não é preferência, é a
  diferença entre lucro e prejuízo por unidade vendida.
- **Aviso de pedido é template aprovado.** Vira f-string e a Meta recusa a
  entrega em vez de o cliente receber.
- **Migração compara identidade de linha, não quantidade.** Duas mensagens
  já foram descartadas em silêncio com a contagem final batendo por
  coincidência.

---

## 3. Candidatas, avaliadas

Ordem de valor por esforço. Cada uma traz o que agrega, o que arrisca e como
medir. Nenhuma está aprovada só por estar listada.

### 3.1 Áudio do cliente (transcrição)

**Agrega:** é o buraco declarado do caminho para o WhatsApp. Foto já
funciona, texto já funciona, áudio não existe, e mensagem de voz é como boa
parte dos clientes brasileiros prefere falar.

**Arrisca:** pouco. Segue o desenho que já provou funcionar na visão: o
áudio vira texto antes de entrar na conversa, e daí pra frente o fluxo é o
de sempre, sem tocar em escolha de ferramenta.

**Medir:** transcrever 20 áudios reais com gíria e ruído, conferir à mão.
Custo de API é da ordem de centavos por hora de áudio.

**Veredito:** melhor candidata. Alto valor, risco baixo, caminho conhecido.

### 3.2 Transporte do WhatsApp (webhook e envio)

**Agrega:** transforma um simulador em produto. O formato já está pronto
(`app/whatsapp.py`: templates, janela de 24h, limites), o `sessao_id` já é o
número no formato `wa_id`, e `notificacao_para_envio` já devolve o payload.
Falta só o transporte.

**Arrisca:** é a primeira vez que o sistema fala com o mundo. Mensagem
enviada não volta atrás. Exige provedor escolhido, verificação de assinatura
do webhook e cadastro dos templates na Meta, que leva dias de aprovação.

**Medir:** ambiente de teste da Meta antes de qualquer número real.

**Veredito:** é o próximo passo de produto, mas depende de decisões que não
são de código (provedor, conta, opt-in). Submeta os templates cedo, porque a
aprovação é o que não dá pra apressar.

### 3.3 Fechar o ciclo do RAG

**Agrega:** o sistema já registra toda pergunta que a base não soube
responder, agrupada por frequência (`perguntas_sem_resposta`). Isso é uma
fila de documentos a escrever priorizada por demanda real. Hoje ela é
coletada e ninguém lê.

**Arrisca:** documento novo mexe no invariante mais sensível do projeto.
Siga as regras já medidas: ~400 caracteres, nunca mais que 500, e perguntas
ancoradas no substantivo do domínio.

**Medir:** `python -m evals retrieval` antes e depois, sempre.

**Veredito:** o melhor retorno por hora de trabalho, e não precisa de código
novo. É hábito, não funcionalidade.

### 3.4 Pool de conexões

**Agrega:** hoje cada operação abre e fecha uma conexão, e montar o system
prompt sozinho já faz várias. Sob concorrência isso vira handshake demais e
esbarra no `max_connections` do Postgres.

**Arrisca:** pouco, mas só compensa quando houver concorrência real. Antes
disso é otimização sem problema.

**Medir:** conexões por requisição e latência sob carga paralela.

**Veredito:** espere o transporte existir. O gargalo hoje é o teto de token
da Groq, não o banco.

### 3.5 Aprender os pesos da recomendação

**Agrega:** `_score_custo_beneficio` usa 40% preço, 20% prazo, 40%
avaliação. Esses números foram calibrados no olho. O sistema já guarda o que
foi sugerido e o que foi comprado, que é exatamente o par necessário pra
ajustá-los com dado.

**Arrisca:** muda o que a Lu recomenda, que é o coração do produto. Precisa
de trava: valores novos só entram se a avaliação continuar dentro dos
mínimos, e sempre com revisão humana.

**Medir:** conversão por sugestão, antes e depois.

**Veredito:** boa ideia, mas depende de volume real. Com dez pedidos
mockados, qualquer ajuste é ruído.

### 3.6 Cache de prompt

**Agrega:** os ~3.500 tokens fixos por rodada se repetem em toda chamada.
Provedores cobram bem menos por prefixo repetido, e o teto por minuto é a
restrição que mais molda o projeto.

**Arrisca:** baixo, é otimização de custo sem mudança de comportamento.
Exige que a parte fixa venha primeiro no prompt, o que já acontece.

**Medir:** tokens cobrados por conversa, antes e depois.

**Veredito:** vale quando o volume subir. Hoje o custo é de centavos.

### 3.7 Índice ANN no pgvector

**Agrega:** nada, hoje. Com 52 documentos o planejador varre tudo de
qualquer jeito.

**Veredito:** **não faça agora.** O gatilho é o corpus passar de alguns
milhares de documentos. Antes disso, um HNSW só perde recall, porque ANN é
aproximado por definição.

### 3.8 Fila de processamento

**Agrega:** quando o webhook existir, a Meta espera resposta rápida e tenta
de novo se demorar, enquanto a Lu leva de 1 a 5 segundos pra responder.
Segurar o webhook aberto esse tempo gera mensagem duplicada. E o aviso de
pedido, que hoje só sai quando alguém consulta `/api/notificacoes`, vai
precisar de um trabalhador agendado, porque no WhatsApp ninguém está com a
tela aberta.

**Veredito:** necessária **depois** do transporte, não antes. E comece pelo
mais simples: `SELECT ... FOR UPDATE SKIP LOCKED` no Postgres que já existe
resolve esse volume. Kafka se paga com múltiplos consumidores independentes
ou replay de evento, e colocá-lo antes disso é currículo, não arquitetura.

---

## 4. Descartadas, e por quê

Registradas pra não voltarem à mesa sem argumento novo.

| Ideia | Por que não |
| --- | --- |
| ORM | O SQL de cinco tabelas é simples de propósito. Ganharia abstração e perderia controle. |
| Kafka agora | Uma aplicação só, sem evento entre serviços. O status do pedido é função do tempo, não de evento. |
| Índice HNSW | 52 documentos. O planejador ignora, e ANN perderia recall. |
| Auto-adaptação sem revisão | A régua roda sob demanda. Sem detecção contínua de regressão, o sistema degradaria em silêncio. Já quase aconteceu. |
| Fine-tuning do modelo | Caro, retorno incerto, e resolve o problema errado: a qualidade hoje depende de recuperação e prompt, não dos pesos. |
| Framework no frontend | Traria build e dependências pra uma tela que é um clone visual do WhatsApp. |
| Manter SQLite | O disco de container é efêmero, o arquivo sumia a cada redeploy. |

---

## 5. Decisões pendentes

Coisas que dependem de escolha humana e travam trabalho.

- **A porta do Postgres deste projeto.** A 5432 desta máquina é de um
  container de trabalho, e o projeto está sem banco por isso. Nem a app nem
  a suíte rodam até isso ser definido.
- **O provedor do canal.** Cloud API direta da Meta ou intermediário.
  Decide o formato do webhook e o custo por mensagem.
- **Opt-in de marketing.** O cupom de recuperação é template MARKETING e
  exige consentimento do cliente. Sem definir onde esse consentimento é
  coletado e guardado, o cupom não pode ser enviado de verdade.

---

## 6. Antes de dar por pronto

Checklist do que precisa estar verde. Não é burocracia: cada linha aqui
existe porque a ausência dela já custou alguma coisa.

- [ ] `pytest` passa inteiro
- [ ] `node --test tests/frontend/formatacao.test.js` passa
- [ ] Mexeu em prompt, persona, descrição de ferramenta ou corpus?
      `python -m evals` e comparar com os números da seção 2
- [ ] Tabela nova de cliente entrou em `TABELAS_DO_VISITANTE`?
- [ ] Consulta nova filtra por `sessao.atual()`, com teste junto?
- [ ] Custo por rodada de tool calling foi medido?
- [ ] Migração de dado conferiu identidade de linha, e não só contagem?
- [ ] Mudança irreversível (envio, desconto, migração) foi aprovada
      explicitamente?
- [ ] O que mudou de decisão está registrado no `CLAUDE.md`, com o porquê

---

## 7. Como registrar uma decisão nova

O valor deste repositório não está só no código, está no **porquê** de cada
escolha estranha. Comentário que explica o óbvio é ruído; comentário que
explica uma decisão contraintuitiva economiza a próxima pessoa de refazer o
erro.

Ao decidir algo não óbvio, registre três coisas: **o que foi feito, o que
foi descartado e o que fez a diferença.** De preferência com o número que
sustentou a decisão. "Ordenação é semântica porque acerta 94,2% contra
92,3% da fusão" vale mais que "usamos busca semântica".
