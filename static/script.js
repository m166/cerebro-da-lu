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

function renderMessage(role, content) {
  const bubble = document.createElement("div");
  bubble.className = `bubble ${role}`;
  bubble.textContent = content;
  messagesEl.appendChild(bubble);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function renderError(text) {
  renderMessage("error", text);
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
    history.forEach((m) => renderMessage(m.role, m.content));
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

// Abre o painel indicado na URL (#catalogo / #pedidos), pra que recarregar
// a página não perca o contexto em que a pessoa estava.
function abrirPainelDaUrl() {
  if (location.hash === "#catalogo") {
    catalogoToggleEl.click();
  } else if (location.hash === "#pedidos") {
    pedidosToggleEl.click();
  }
}

loadHistory();
abrirPainelDaUrl();
