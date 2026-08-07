const messagesEl = document.getElementById("messages");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("chat-input");
const catalogoToggleEl = document.getElementById("catalogo-toggle");
const catalogoPanelEl = document.getElementById("catalogo-panel");
const catalogoListaEl = document.getElementById("catalogo-lista");
const categoriaEl = document.getElementById("catalogo-categoria");
const buscaEl = document.getElementById("catalogo-busca");
const contagemEl = document.getElementById("catalogo-contagem");

const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

function renderMessage(role, content) {
  const bubble = document.createElement("div");
  bubble.className = `bubble ${role}`;
  bubble.textContent = content;
  messagesEl.appendChild(bubble);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function renderError(text) {
  const bubble = document.createElement("div");
  bubble.className = "bubble error";
  bubble.textContent = text;
  messagesEl.appendChild(bubble);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

formEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const content = inputEl.value.trim();
  if (!content) return;

  inputEl.value = "";
  renderMessage("user", content);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });

    const data = await response.json();

    if (!response.ok) {
      renderError(data.detail || "Erro desconhecido ao falar com o servidor.");
      return;
    }

    renderMessage("assistant", data.reply);
  } catch (err) {
    renderError("Não foi possível conectar ao servidor.");
  }
});

async function loadHistory() {
  try {
    const response = await fetch("/api/history");
    const history = await response.json();
    history.forEach((message) => renderMessage(message.role, message.content));
  } catch (err) {
    renderError("Não foi possível carregar o histórico.");
  }
}

function criarLinha(texto, className) {
  const p = document.createElement("p");
  p.className = className;
  p.textContent = texto;
  return p;
}

function criarCard(produto) {
  const card = document.createElement("div");
  card.className = "produto-card";

  const titulo = document.createElement("h3");
  titulo.textContent = produto.nome;
  card.appendChild(titulo);

  card.appendChild(criarLinha(produto.descricao, "produto-descricao"));
  card.appendChild(
    criarLinha(
      `${moeda.format(produto.preco)} · ${produto.prazo_entrega_dias} dia(s) · ⭐ ${produto.avaliacao}`,
      "produto-info"
    )
  );
  card.appendChild(
    criarLinha(
      produto.estoque > 0 ? `${produto.estoque} em estoque` : "Sem estoque",
      "produto-info"
    )
  );

  const botao = document.createElement("button");
  botao.type = "button";
  botao.textContent = "Pedir";
  botao.disabled = produto.estoque <= 0;
  botao.addEventListener("click", () => {
    catalogoPanelEl.classList.add("hidden");
    inputEl.value = `Quero comprar o produto "${produto.nome}" (id ${produto.id}).`;
    formEl.requestSubmit();
  });
  card.appendChild(botao);

  return card;
}

function renderCatalogo(produtos) {
  catalogoListaEl.innerHTML = "";
  contagemEl.textContent = `${produtos.length} produto(s)`;

  if (produtos.length === 0) {
    catalogoListaEl.appendChild(criarLinha("Nenhum produto encontrado.", "produto-info"));
    return;
  }

  produtos.forEach((produto) => catalogoListaEl.appendChild(criarCard(produto)));
}

async function loadCategorias() {
  try {
    const response = await fetch("/api/categorias");
    const categorias = await response.json();
    categorias.forEach((categoria) => {
      const option = document.createElement("option");
      option.value = categoria;
      option.textContent = categoria.replace(/-/g, " ");
      categoriaEl.appendChild(option);
    });
  } catch (err) {
    contagemEl.textContent = "Não foi possível carregar as categorias.";
  }
}

async function loadCatalogo() {
  const params = new URLSearchParams();
  if (categoriaEl.value) params.set("categoria", categoriaEl.value);
  if (buscaEl.value.trim()) params.set("query", buscaEl.value.trim());

  try {
    const response = await fetch(`/api/produtos?${params}`);
    renderCatalogo(await response.json());
  } catch (err) {
    catalogoListaEl.textContent = "Não foi possível carregar o catálogo.";
  }
}

let buscaTimeout;
buscaEl.addEventListener("input", () => {
  clearTimeout(buscaTimeout);
  buscaTimeout = setTimeout(loadCatalogo, 250);
});

categoriaEl.addEventListener("change", loadCatalogo);

catalogoToggleEl.addEventListener("click", async () => {
  const abrindo = catalogoPanelEl.classList.contains("hidden");
  catalogoPanelEl.classList.toggle("hidden");
  if (abrindo && !catalogoListaEl.hasChildNodes()) {
    await loadCategorias();
    loadCatalogo();
  }
});

loadHistory();
