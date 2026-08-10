const messagesEl = document.getElementById("messages");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("chat-input");
const enviarEl = document.getElementById("chat-enviar");
const digitandoEl = document.getElementById("digitando");

const catalogoToggleEl = document.getElementById("catalogo-toggle");
const catalogoPanelEl = document.getElementById("catalogo-panel");
const catalogoListaEl = document.getElementById("catalogo-lista");
const categoriaEl = document.getElementById("catalogo-categoria");
const buscaEl = document.getElementById("catalogo-busca");
const compararEl = document.getElementById("catalogo-comparar");
const catalogoContagemEl = document.getElementById("catalogo-contagem");

const pedidosToggleEl = document.getElementById("pedidos-toggle");
const pedidosPanelEl = document.getElementById("pedidos-panel");
const pedidosListaEl = document.getElementById("pedidos-lista");
const pedidosContagemEl = document.getElementById("pedidos-contagem");
const pedidosAtualizarEl = document.getElementById("pedidos-atualizar");
const conexaoAvisoEl = document.getElementById("conexao-aviso");

const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

function formatarData(valor) {
  if (!valor) return "";
  // Reformata a string em vez de usar Date: "2026-09-15" seria lido como
  // UTC e, no fuso do Brasil, exibido como 14/09, um dia antes do que o
  // cliente agendou.
  const [ano, mes, dia] = String(valor).slice(0, 10).split("-");
  return dia ? `${dia}/${mes}/${ano}` : String(valor);
}

async function pedirJson(url, opcoes) {
  const resposta = await fetch(url, opcoes);
  const dados = await resposta.json().catch(() => ({}));
  if (!resposta.ok) {
    throw new Error(dados.detail || "Não foi possível completar a operação.");
  }
  return dados;
}

// --- Chat -----------------------------------------------------------------

function anexarBolha(bolha, sempreRolar = true) {
  const acompanhar =
    sempreRolar ||
    messagesEl.scrollHeight - messagesEl.scrollTop - messagesEl.clientHeight < 80;
  messagesEl.appendChild(bolha);
  if (acompanhar) messagesEl.scrollTop = messagesEl.scrollHeight;
}

function renderMessage(role, content) {
  const bubble = document.createElement("div");
  bubble.className = `bubble ${role}`;
  bubble.textContent = content;
  anexarBolha(bubble);
}

function renderError(text) {
  renderMessage("error", text);
}

// O aviso de status e a resposta da Lu são os dois "assistant", porque os
// dois foram ditos por ela. Quem separa é o campo `tipo`, que a API manda
// junto. Antes isso era adivinhado por regex no texto, e mudar a frase no
// backend fazia o aviso voltar a parecer resposta comum, sem erro nenhum.
function ehNotificacao(mensagem) {
  return mensagem.tipo === "notificacao";
}

function renderNotificacao(content) {
  const bubble = document.createElement("div");
  bubble.className = "bubble notificacao";

  const rotulo = document.createElement("span");
  rotulo.className = "notificacao-rotulo";
  rotulo.textContent = "Atualização do pedido";

  const texto = document.createElement("span");
  texto.textContent = content;

  bubble.append(rotulo, texto);
  // Chega sozinha, sem o usuário ter pedido: só puxa a rolagem se ele já
  // estiver no fim da conversa, pra não tirar da tela o que ele está lendo.
  anexarBolha(bubble, false);
}

function definirCarregando(carregando) {
  digitandoEl.hidden = !carregando;
  inputEl.disabled = carregando;
  enviarEl.disabled = carregando;
  if (carregando) {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  } else {
    inputEl.focus();
  }
}

async function enviarMensagem(texto) {
  renderMessage("user", texto);
  definirCarregando(true);
  try {
    const dados = await pedirJson("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: texto }),
    });
    renderMessage("assistant", dados.reply);
  } catch (err) {
    renderError(err.message);
  } finally {
    definirCarregando(false);
  }
}

formEl.addEventListener("submit", (event) => {
  event.preventDefault();
  const content = inputEl.value.trim();
  if (!content || inputEl.disabled) return;
  inputEl.value = "";
  enviarMensagem(content);
});

async function loadHistory() {
  try {
    const history = await pedirJson("/api/history");
    // Redesenha do zero: a notificação que o poll já pôs na tela também está
    // gravada no histórico, e sem limpar ela apareceria duas vezes.
    messagesEl.innerHTML = "";
    history.forEach((m) => {
      if (ehNotificacao(m)) renderNotificacao(m.content);
      else renderMessage(m.role, m.content);
    });
  } catch (err) {
    renderError("Não foi possível carregar o histórico.");
  }
}

// --- Painéis ---------------------------------------------------------------

function alternarPainel(painel, botao) {
  const abrindo = painel.classList.contains("hidden");
  [catalogoPanelEl, pedidosPanelEl].forEach((p) => p.classList.add("hidden"));
  [catalogoToggleEl, pedidosToggleEl].forEach((b) => {
    b.classList.remove("ativa");
    b.setAttribute("aria-expanded", "false");
  });
  if (abrindo) {
    painel.classList.remove("hidden");
    botao.classList.add("ativa");
    botao.setAttribute("aria-expanded", "true");
  }
  const hash = abrindo ? `#${painel.id.replace("-panel", "")}` : "";
  history.replaceState(null, "", hash || location.pathname);
  return abrindo;
}

function criarLinha(texto, className) {
  const p = document.createElement("p");
  p.className = className;
  p.textContent = texto;
  return p;
}

function criarBotao(rotulo, aoClicar, classe = "botao-secundario") {
  const botao = document.createElement("button");
  botao.type = "button";
  botao.className = classe;
  botao.textContent = rotulo;
  botao.addEventListener("click", aoClicar);
  return botao;
}

// --- Catálogo ---------------------------------------------------------------

function criarCardProduto(produto) {
  const card = document.createElement("div");
  card.className = "card";

  const titulo = document.createElement("h3");
  titulo.textContent = produto.nome;
  card.appendChild(titulo);

  card.appendChild(criarLinha(produto.descricao, "card-secundario"));
  card.appendChild(
    criarLinha(
      `${moeda.format(produto.preco)} · ${produto.prazo_entrega_dias} dia(s) · ⭐ ${produto.avaliacao}`,
      "card-info"
    )
  );

  const estoque = criarLinha(
    produto.estoque > 0 ? `${produto.estoque} em estoque` : "Sem estoque",
    produto.estoque > 0 ? "card-info" : "card-alerta"
  );
  card.appendChild(estoque);

  const acoes = document.createElement("div");
  acoes.className = "card-acoes";
  const pedir = criarBotao(
    "Pedir",
    () => {
      alternarPainel(catalogoPanelEl, catalogoToggleEl);
      enviarMensagem(`Quero comprar o produto "${produto.nome}" (id ${produto.id}).`);
    },
    "botao-primario"
  );
  pedir.disabled = produto.estoque <= 0;
  acoes.appendChild(pedir);
  acoes.appendChild(
    criarBotao("Saber mais", () => {
      alternarPainel(catalogoPanelEl, catalogoToggleEl);
      enviarMensagem(`Me explica o que devo olhar antes de escolher um ${produto.categoria.replace(/-/g, " ")}.`);
    })
  );
  card.appendChild(acoes);

  return card;
}

function renderCatalogo(produtos) {
  catalogoListaEl.innerHTML = "";
  catalogoContagemEl.textContent = `${produtos.length} produto(s)`;
  compararEl.hidden = !categoriaEl.value;

  if (produtos.length === 0) {
    catalogoListaEl.appendChild(criarLinha("Nenhum produto encontrado.", "card-info"));
    return;
  }
  produtos.forEach((p) => catalogoListaEl.appendChild(criarCardProduto(p)));
}

async function loadCategorias() {
  try {
    const categorias = await pedirJson("/api/categorias");
    categorias.forEach((categoria) => {
      const option = document.createElement("option");
      option.value = categoria;
      option.textContent = categoria.replace(/-/g, " ");
      categoriaEl.appendChild(option);
    });
  } catch (err) {
    catalogoContagemEl.textContent = "Não foi possível carregar as categorias.";
  }
}

async function loadCatalogo() {
  const params = new URLSearchParams();
  if (categoriaEl.value) params.set("categoria", categoriaEl.value);
  if (buscaEl.value.trim()) params.set("query", buscaEl.value.trim());
  try {
    renderCatalogo(await pedirJson(`/api/produtos?${params}`));
  } catch (err) {
    catalogoListaEl.textContent = err.message;
  }
}

let buscaTimeout;
buscaEl.addEventListener("input", () => {
  clearTimeout(buscaTimeout);
  buscaTimeout = setTimeout(loadCatalogo, 250);
});
categoriaEl.addEventListener("change", loadCatalogo);

compararEl.addEventListener("click", () => {
  const categoria = categoriaEl.value.replace(/-/g, " ");
  alternarPainel(catalogoPanelEl, catalogoToggleEl);
  enviarMensagem(`Compara as opções de ${categoria} pra mim.`);
});

catalogoToggleEl.addEventListener("click", async () => {
  const abriu = alternarPainel(catalogoPanelEl, catalogoToggleEl);
  if (abriu && !catalogoListaEl.hasChildNodes()) {
    await loadCategorias();
    loadCatalogo();
  }
});

// --- Pedidos ----------------------------------------------------------------

// Espelha models.ETAPAS_RASTREIO. A lista de pedidos devolve só a etapa
// atual, e buscar /rastreio por card seria uma requisição por pedido.
const ETAPAS_PEDIDO = [
  "confirmado",
  "em separação",
  "enviado",
  "saiu para entrega",
  "entregue",
];

async function copiarTexto(texto) {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(texto);
      return true;
    }
  } catch (err) {
    // Sem permissão de área de transferência: cai na cópia por seleção.
  }
  const campo = document.createElement("textarea");
  campo.value = texto;
  campo.setAttribute("readonly", "");
  campo.style.position = "fixed";
  campo.style.opacity = "0";
  document.body.appendChild(campo);
  campo.select();
  let copiou = false;
  try {
    copiou = document.execCommand("copy");
  } catch (err) {
    copiou = false;
  }
  campo.remove();
  return copiou;
}

function criarRastreioCopiavel(codigo) {
  const linha = document.createElement("p");
  linha.className = "card-info rastreio";

  const rotulo = document.createElement("span");
  rotulo.className = "rastreio-rotulo";
  rotulo.textContent = "Rastreio";

  const confirmacao = document.createElement("span");
  confirmacao.className = "rastreio-copiado";
  confirmacao.setAttribute("role", "status");
  confirmacao.hidden = true;

  const botao = document.createElement("button");
  botao.type = "button";
  botao.className = "rastreio-codigo";
  botao.textContent = codigo;
  botao.title = "Clique para copiar";
  botao.setAttribute("aria-label", `Copiar o código de rastreio ${codigo}`);

  let timeout;
  botao.addEventListener("click", async () => {
    const copiou = await copiarTexto(codigo);
    confirmacao.textContent = copiou ? "copiado" : "copie manualmente";
    confirmacao.hidden = false;
    clearTimeout(timeout);
    timeout = setTimeout(() => {
      confirmacao.hidden = true;
    }, 2000);
  });

  linha.append(rotulo, botao, confirmacao);
  return linha;
}

function criarLinhaDoTempo(status) {
  const atual = ETAPAS_PEDIDO.indexOf(status);
  if (atual < 0) return [];

  const lista = document.createElement("ol");
  lista.className = "etapas";
  lista.setAttribute("aria-label", "Progresso do pedido");

  ETAPAS_PEDIDO.forEach((etapa, indice) => {
    const item = document.createElement("li");
    item.className = "etapa";
    if (indice < atual) item.classList.add("feita");
    if (indice === atual) {
      item.classList.add("atual");
      item.setAttribute("aria-current", "step");
    }
    item.title = etapa;

    const marca = document.createElement("span");
    marca.className = "etapa-marca";
    const nome = document.createElement("span");
    nome.className = "etapa-nome";
    nome.textContent = etapa;

    item.append(marca, nome);
    lista.appendChild(item);
  });

  const legenda = criarLinha(
    `Etapa ${atual + 1} de ${ETAPAS_PEDIDO.length}`,
    "etapas-legenda"
  );
  return [lista, legenda];
}

function criarCardPedido(pedido) {
  const card = document.createElement("div");
  card.className = "card";

  const titulo = document.createElement("h3");
  titulo.textContent = `Pedido #${pedido.id}`;
  card.appendChild(titulo);

  card.appendChild(criarLinha(pedido.produto_nome, "card-secundario"));
  card.appendChild(
    criarLinha(
      `${pedido.quantidade}x · ${moeda.format(pedido.valor_total)} · ${formatarData(pedido.data_criacao)}`,
      "card-info"
    )
  );

  const status = document.createElement("p");
  status.className = "card-info";
  const selo = document.createElement("span");
  selo.className = "selo";
  selo.textContent = pedido.status;
  status.appendChild(selo);
  if (pedido.data_entrega_agendada) {
    status.append(` entrega em ${formatarData(pedido.data_entrega_agendada)}`);
  }
  card.appendChild(status);

  if (pedido.codigo_rastreio) {
    card.appendChild(criarRastreioCopiavel(pedido.codigo_rastreio));
  }

  criarLinhaDoTempo(pedido.status).forEach((el) => card.appendChild(el));

  const detalhe = document.createElement("p");
  detalhe.className = "card-detalhe";
  card.appendChild(detalhe);

  const mostrar = (texto) => {
    detalhe.textContent = texto;
  };

  const acoes = document.createElement("div");
  acoes.className = "card-acoes";

  acoes.appendChild(
    criarBotao("Rastrear", async () => {
      mostrar("consultando...");
      try {
        const r = await pedirJson(`/api/pedidos/${pedido.id}/rastreio`);
        mostrar(`${r.etapa_atual}, ${r.localizacao}`);
      } catch (err) {
        mostrar(err.message);
      }
    })
  );

  acoes.appendChild(
    criarBotao("Agendar entrega", async () => {
      const data = prompt("Data da entrega (AAAA-MM-DD):");
      if (!data) return;
      mostrar("agendando...");
      try {
        await pedirJson(`/api/pedidos/${pedido.id}/agendar-entrega`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ data_entrega: data }),
        });
        loadPedidos();
      } catch (err) {
        mostrar(err.message);
      }
    })
  );

  acoes.appendChild(
    criarBotao("2ª via boleto", async () => {
      mostrar("gerando...");
      try {
        const d = await pedirJson(`/api/pedidos/${pedido.id}/segunda-via?tipo=boleto`);
        mostrar(`${d.linha_digitavel} · vence ${formatarData(d.vencimento)}`);
      } catch (err) {
        mostrar(err.message);
      }
    })
  );

  acoes.appendChild(
    criarBotao("Nota fiscal", async () => {
      mostrar("gerando...");
      try {
        const d = await pedirJson(`/api/pedidos/${pedido.id}/segunda-via?tipo=nf`);
        mostrar(`${d.numero_nf} · ${moeda.format(d.valor)}`);
      } catch (err) {
        mostrar(err.message);
      }
    })
  );

  card.appendChild(acoes);
  return card;
}

async function loadPedidos() {
  try {
    const pedidos = await pedirJson("/api/pedidos");
    pedidosListaEl.innerHTML = "";
    pedidosContagemEl.textContent = `${pedidos.length} pedido(s)`;
    if (pedidos.length === 0) {
      pedidosListaEl.appendChild(
        criarLinha("Nenhum pedido ainda. Peça algo pelo catálogo ou pelo chat.", "card-info")
      );
      return;
    }
    pedidos.forEach((p) => pedidosListaEl.appendChild(criarCardPedido(p)));
  } catch (err) {
    pedidosListaEl.textContent = err.message;
  }
}

pedidosAtualizarEl.addEventListener("click", loadPedidos);

pedidosToggleEl.addEventListener("click", () => {
  if (alternarPainel(pedidosPanelEl, pedidosToggleEl)) {
    loadPedidos();
  }
});

// --- Notificações de pedido -------------------------------------------------

const INTERVALO_NOTIFICACOES = 5000;
const INTERVALO_NOTIFICACOES_MAXIMO = 60000;
const FALHAS_ATE_AVISAR = 2;

let intervaloNotificacoes = INTERVALO_NOTIFICACOES;
let timerNotificacoes;
let consultaEmVoo = false;
let falhasSeguidas = 0;

// Aba escondida não consulta: o status é derivado do relógio no servidor, então
// nada se perde enquanto ninguém olha, e a volta pra aba busca o estado atual.
function agendarNotificacoes(atraso = intervaloNotificacoes) {
  clearTimeout(timerNotificacoes);
  if (document.hidden) return;
  timerNotificacoes = setTimeout(verificarNotificacoes, atraso);
}

// O status do pedido é derivado do relógio no backend, então é a consulta
// que descobre que ele andou. As mensagens já vêm salvas no histórico, aqui
// só entram na tela.
async function verificarNotificacoes() {
  if (consultaEmVoo || document.hidden) {
    agendarNotificacoes();
    return;
  }
  consultaEmVoo = true;
  try {
    const { novas } = await pedirJson("/api/notificacoes");
    falhasSeguidas = 0;
    intervaloNotificacoes = INTERVALO_NOTIFICACOES;
    conexaoAvisoEl.hidden = true;
    if (novas.length) {
      novas.forEach((m) => renderNotificacao(m.content));
      // Só há mudança de etapa quando chega notificação, então esta é a hora
      // exata de redesenhar a lista, sem precisar de um segundo poll.
      if (!pedidosPanelEl.classList.contains("hidden")) loadPedidos();
    }
  } catch (err) {
    // Consulta de fundo: um aviso fixo e discreto, nunca uma bolha de erro a
    // cada tentativa. O intervalo dobra até o teto pra não martelar a API.
    falhasSeguidas += 1;
    intervaloNotificacoes = Math.min(
      intervaloNotificacoes * 2,
      INTERVALO_NOTIFICACOES_MAXIMO
    );
    conexaoAvisoEl.hidden = falhasSeguidas < FALHAS_ATE_AVISAR;
  } finally {
    consultaEmVoo = false;
    agendarNotificacoes();
  }
}

document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    clearTimeout(timerNotificacoes);
    return;
  }
  agendarNotificacoes(falhasSeguidas ? intervaloNotificacoes : 0);
});

// Abre o painel indicado na URL (#catalogo / #pedidos), pra que recarregar
// a página não perca o contexto em que a pessoa estava.
function abrirPainelDaUrl() {
  if (location.hash === "#catalogo") {
    catalogoToggleEl.click();
  } else if (location.hash === "#pedidos") {
    pedidosToggleEl.click();
  }
}

// Só depois do histórico na tela: notificação renderizada antes seria
// desenhada de novo quando o histórico chegasse.
loadHistory().then(() => agendarNotificacoes());
abrirPainelDaUrl();
