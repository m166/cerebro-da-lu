// `comFormatacao` e `formatarData` moram em formatacao.js, carregado
// antes deste arquivo: são puras e por isso têm teste em node.
const messagesEl = document.getElementById("messages");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("chat-input");
const enviarEl = document.getElementById("chat-enviar");
const perfilStatusEl = document.getElementById("perfil-status");

const menuBotaoEl = document.getElementById("menu-botao");
const menuEl = document.getElementById("menu");
const menuTrocarEl = document.getElementById("menu-trocar");

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

const anexoBotaoEl = document.getElementById("anexo-botao");
const anexoArquivoEl = document.getElementById("anexo-arquivo");
const anexoPreviaEl = document.getElementById("anexo-previa");
const anexoImagemEl = document.getElementById("anexo-imagem");
const anexoRemoverEl = document.getElementById("anexo-remover");

const entradaEl = document.getElementById("entrada");
const entradaFormEl = document.getElementById("entrada-form");
const entradaTelefoneEl = document.getElementById("entrada-telefone");
const entradaErroEl = document.getElementById("entrada-erro");
const entradaExemplosEl = document.getElementById("entrada-exemplos");
const simuladorNumeroEl = document.getElementById("simulador-numero");
const trocarNumeroEl = document.getElementById("trocar-numero");

// Foto escolhida e ainda não enviada, já em data URL pra ir no corpo JSON.
let anexoPendente = null;

const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });


async function pedirJson(url, opcoes) {
  const resposta = await fetch(url, opcoes);
  if (resposta.status === 204) return null;

  const dados = await resposta.json().catch(() => ({}));
  if (!resposta.ok) {
    const erro = new Error(dados.detail || "Não foi possível completar a operação.");
    // 401 aqui não é falha: é o servidor dizendo que não sabe de qual número
    // veio a requisição. Quem chamou não deve mostrar bolha de erro, e sim
    // devolver a pessoa pra tela de identificação.
    erro.naoIdentificado = resposta.status === 401;
    throw erro;
  }
  return dados;
}

// --- Identificação ----------------------------------------------------------

const NUMEROS_DE_EXEMPLO = ["11 98888-1234", "21 97777-4321", "31 96666-8899"];

let identificado = false;

// Permite abrir a tela já como um número (`?telefone=11988881234`). Serve pro
// print em headless, que não clica em nada, e pra alternar entre dois
// clientes em abas diferentes sem passar pelo formulário.
function numeroDaUrl() {
  return new URLSearchParams(location.search).get("telefone");
}

function mostrarEntrada(mensagem) {
  identificado = false;
  entradaEl.hidden = false;
  entradaErroEl.hidden = !mensagem;
  entradaErroEl.textContent = mensagem || "";
  simuladorNumeroEl.textContent = "ninguém ainda";
  entradaTelefoneEl.focus();
}

function aoIdentificar(eu) {
  identificado = true;
  entradaEl.hidden = true;
  entradaErroEl.hidden = true;
  simuladorNumeroEl.textContent = eu.telefone_formatado;
  document.title = `Lu · ${eu.telefone_formatado}`;
}

async function entrar(telefone) {
  const eu = await pedirJson("/api/sessao", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ telefone }),
  });
  aoIdentificar(eu);
  await loadHistory();
  agendarNotificacoes(0);
  return eu;
}

entradaFormEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const telefone = entradaTelefoneEl.value.trim();
  if (!telefone) return;
  try {
    await entrar(telefone);
  } catch (err) {
    entradaErroEl.textContent = err.message;
    entradaErroEl.hidden = false;
  }
});

NUMEROS_DE_EXEMPLO.forEach((numero) => {
  const botao = document.createElement("button");
  botao.type = "button";
  botao.className = "entrada-exemplo";
  botao.textContent = numero;
  botao.addEventListener("click", () => {
    entradaTelefoneEl.value = numero;
    entradaFormEl.requestSubmit();
  });
  entradaExemplosEl.appendChild(botao);
});

async function trocarDeNumero() {
  clearTimeout(timerNotificacoes);
  await fetch("/api/sessao", { method: "DELETE" });
  messagesEl.innerHTML = "";
  ultimaData = null;
  ultimoAutor = null;
  entradaTelefoneEl.value = "";
  // Sem isto, recarregar depois de trocar voltaria pro número da URL.
  history.replaceState(null, "", location.pathname);
  fecharMenu();
  fecharPaineis();
  mostrarEntrada();
}

trocarNumeroEl.addEventListener("click", trocarDeNumero);
menuTrocarEl.addEventListener("click", trocarDeNumero);

// --- Menu do cabeçalho ------------------------------------------------------

function fecharMenu() {
  menuEl.hidden = true;
  menuBotaoEl.setAttribute("aria-expanded", "false");
}

menuBotaoEl.addEventListener("click", (event) => {
  event.stopPropagation();
  menuEl.hidden = !menuEl.hidden;
  menuBotaoEl.setAttribute("aria-expanded", String(!menuEl.hidden));
});

document.addEventListener("click", (event) => {
  if (!menuEl.hidden && !menuEl.contains(event.target)) fecharMenu();
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  if (!menuEl.hidden) return fecharMenu();
  fecharPaineis();
});

// --- Chat -------------------------------------------------------------------

function anexarBolha(bolha, sempreRolar = true) {
  const acompanhar =
    sempreRolar ||
    messagesEl.scrollHeight - messagesEl.scrollTop - messagesEl.clientHeight < 80;
  messagesEl.appendChild(bolha);
  if (acompanhar) messagesEl.scrollTop = messagesEl.scrollHeight;
}

function agora() {
  return new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

// Separador de dia, como num app de mensagem. Só aparece quando a data muda,
// então uma conversa do mesmo dia não ganha faixa nenhuma.
let ultimaData = null;

function marcarDia(rotulo) {
  if (rotulo === ultimaData) return;
  ultimaData = rotulo;
  const faixa = document.createElement("div");
  faixa.className = "separador-data";
  faixa.textContent = rotulo;
  messagesEl.appendChild(faixa);
}

function criarBalao(classe, conteudo, hora, tique) {
  const bubble = document.createElement("div");
  bubble.className = `bubble ${classe}`;

  const texto = document.createElement("span");
  texto.appendChild(comFormatacao(conteudo));
  bubble.appendChild(texto);

  if (hora) {
    const marca = document.createElement("span");
    marca.className = "hora";
    marca.append(document.createTextNode(hora));
    if (tique) {
      const marcaTique = document.createElement("span");
      marcaTique.className = tique === "lido" ? "tique lido" : "tique";
      marcaTique.textContent = tique === "lido" ? "✓✓" : "✓";
      marca.appendChild(marcaTique);
    }
    bubble.appendChild(marca);
  }
  return bubble;
}

// Rabicho e folga só na primeira mensagem de uma sequência do mesmo autor.
// Não há avatar por mensagem: no WhatsApp ele só aparece em grupo, e numa
// conversa de duas pessoas a foto ao lado de cada balão entrega que a tela
// não é o app de verdade.
let ultimoAutor = null;

function renderMessage(role, content, hora = agora(), foto = null, tique = "lido") {
  if (role === "error") {
    anexarBolha(criarBalao("error", content));
    ultimoAutor = null;
    return null;
  }

  marcarDia("Hoje");

  const linha = document.createElement("div");
  const daLu = role !== "user";
  linha.className = `linha-mensagem ${daLu ? "da-lu" : "de-mim"}`;
  if (ultimoAutor !== role) linha.classList.add("abre-sequencia");
  ultimoAutor = role;

  const balao = criarBalao(daLu ? "assistant" : "user", content, hora, daLu ? null : tique);
  if (foto) {
    const img = document.createElement("img");
    img.className = "bubble-foto";
    img.src = foto;
    img.alt = "Foto enviada por você";
    balao.prepend(img);
  }
  linha.appendChild(balao);
  anexarBolha(linha);
  return linha;
}

function renderError(text) {
  renderMessage("error", text);
}

// Um tique cinza quando a mensagem saiu, dois azuis quando a Lu respondeu (ou
// seja, leu). É o sinal que o cliente olha no WhatsApp pra saber se chegou.
function marcarComoLido(linha) {
  const tique = linha && linha.querySelector(".tique");
  if (!tique) return;
  tique.textContent = "✓✓";
  tique.classList.add("lido");
}

// Cartão do produto ao lado da fala da Lu. Foi o que resolveu a queixa de que
// tudo chegava em texto: preço, foto e ação ficam visíveis sem ler o parágrafo.
function renderCartoesProduto(produtos) {
  if (!produtos || !produtos.length) return;

  const caixa = document.createElement("div");
  caixa.className = "cartoes-produto";

  produtos.forEach((produto) => {
    const cartao = document.createElement("div");
    cartao.className = "cartao-produto";

    const foto = document.createElement("img");
    foto.src = produto.imagem;
    foto.alt = produto.nome;
    foto.loading = "lazy";

    const texto = document.createElement("div");
    texto.className = "cartao-texto";

    const nome = document.createElement("p");
    nome.className = "cartao-nome";
    nome.textContent = produto.nome;

    const preco = document.createElement("p");
    preco.className = "cartao-preco";
    preco.textContent = moeda.format(produto.preco);

    const meta = document.createElement("p");
    meta.className = "cartao-meta";
    meta.textContent = `${produto.prazo_entrega_dias} dia(s) · ⭐ ${produto.avaliacao}`;

    texto.append(nome, preco, meta);

    const pedir = document.createElement("button");
    pedir.type = "button";
    pedir.className = "botao-primario";
    pedir.textContent = "Pedir";
    pedir.disabled = produto.estoque <= 0;
    pedir.addEventListener("click", () =>
      enviarMensagem(`Quero comprar o ${produto.nome} (id ${produto.id}).`)
    );

    cartao.append(foto, texto, pedir);
    caixa.appendChild(cartao);
  });

  anexarBolha(caixa, false);
}

// O aviso de status e a resposta da Lu são os dois "assistant", porque os
// dois foram ditos por ela. Quem separa é o campo `tipo`, que a API manda
// junto. Antes isso era adivinhado por regex no texto, e mudar a frase no
// backend fazia o aviso voltar a parecer resposta comum, sem erro nenhum.
function ehNotificacao(mensagem) {
  return mensagem.tipo === "notificacao";
}

// No WhatsApp um aviso de pedido chega como mensagem, não como cartão
// amarelo: o emoji é o único destaque que o canal real permitiria.
function renderNotificacao(content) {
  const linha = renderMessage("assistant", `📦 ${content}`);
  // Chega sozinha, sem o cliente ter pedido: só puxa a rolagem se ele já
  // estiver no fim da conversa, pra não tirar da tela o que ele está lendo.
  return linha;
}

function definirCarregando(carregando) {
  // "digitando..." vai pro cabeçalho, que é onde o WhatsApp mostra. Um balão
  // de três pontinhos na conversa não existe lá.
  perfilStatusEl.textContent = carregando ? "digitando..." : "online";
  inputEl.disabled = carregando;
  enviarEl.disabled = carregando;
  anexoBotaoEl.disabled = carregando;
  if (carregando) {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  } else {
    inputEl.focus();
  }
}

function tratarErro(err) {
  if (err.naoIdentificado) {
    mostrarEntrada("Sua sessão expirou. Informe o número de novo.");
    return;
  }
  renderError(err.message);
}

async function enviarMensagem(texto, imagem = null) {
  const minha = renderMessage("user", texto, agora(), imagem, "enviado");
  definirCarregando(true);
  try {
    const dados = await pedirJson("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: texto, imagem }),
    });
    marcarComoLido(minha);
    renderMessage("assistant", dados.reply);
    renderCartoesProduto(dados.produtos);
  } catch (err) {
    tratarErro(err);
  } finally {
    definirCarregando(false);
  }
}

formEl.addEventListener("submit", (event) => {
  event.preventDefault();
  const content = inputEl.value.trim();
  // Com foto anexada dá pra enviar sem escrever nada: a pergunta implícita
  // é sempre a mesma, se a loja tem aquilo.
  if ((!content && !anexoPendente) || inputEl.disabled) return;

  const foto = anexoPendente;
  const texto = content || (foto ? "Vocês têm esse produto?" : "");
  inputEl.value = "";
  limparAnexo();
  enviarMensagem(texto, foto);
});

// --- Foto do produto --------------------------------------------------------

function limparAnexo() {
  anexoPendente = null;
  anexoArquivoEl.value = "";
  anexoPreviaEl.hidden = true;
  anexoImagemEl.removeAttribute("src");
}

anexoBotaoEl.addEventListener("click", () => anexoArquivoEl.click());
anexoRemoverEl.addEventListener("click", limparAnexo);

anexoArquivoEl.addEventListener("change", () => {
  const arquivo = anexoArquivoEl.files && anexoArquivoEl.files[0];
  if (!arquivo) return;

  // O mesmo teto do servidor, conferido aqui pra não subir 20MB e só então
  // descobrir que foi recusado.
  if (arquivo.size > 8 * 1024 * 1024) {
    renderError("A foto passa de 8MB. Mande uma menor.");
    limparAnexo();
    return;
  }

  const leitor = new FileReader();
  leitor.onload = () => {
    anexoPendente = leitor.result;
    anexoImagemEl.src = anexoPendente;
    anexoPreviaEl.hidden = false;
    inputEl.focus();
  };
  leitor.onerror = () => {
    renderError("Não consegui ler essa foto.");
    limparAnexo();
  };
  leitor.readAsDataURL(arquivo);
});

async function loadHistory() {
  try {
    const history = await pedirJson("/api/history");
    // Redesenha do zero: a notificação que o poll já pôs na tela também está
    // gravada no histórico, e sem limpar ela apareceria duas vezes.
    messagesEl.innerHTML = "";
    ultimaData = null;
    ultimoAutor = null;
    history.forEach((m) => {
      if (ehNotificacao(m)) {
        renderNotificacao(m.content);
      } else {
        renderMessage(m.role, m.content);
        renderCartoesProduto(m.produtos);
      }
    });
  } catch (err) {
    if (err.naoIdentificado) return mostrarEntrada();
    renderError("Não foi possível carregar o histórico.");
  }
}

// --- Painéis ----------------------------------------------------------------

function fecharPaineis() {
  [catalogoPanelEl, pedidosPanelEl].forEach((p) => p.classList.add("hidden"));
  [catalogoToggleEl, pedidosToggleEl].forEach((b) =>
    b.setAttribute("aria-expanded", "false")
  );
  history.replaceState(null, "", location.pathname + location.search);
}

function alternarPainel(painel, botao) {
  const abrindo = painel.classList.contains("hidden");
  fecharPaineis();
  fecharMenu();
  if (abrindo) {
    painel.classList.remove("hidden");
    botao.setAttribute("aria-expanded", "true");
    history.replaceState(
      null,
      "",
      `${location.pathname}${location.search}#${painel.id.replace("-panel", "")}`
    );
  }
  return abrindo;
}

document.querySelectorAll(".painel-fechar").forEach((botao) => {
  botao.addEventListener("click", fecharPaineis);
});

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
  const card = document.createElement("article");
  card.className = "produto";

  const foto = document.createElement("img");
  foto.className = "produto-foto";
  foto.src = produto.imagem;
  foto.alt = produto.nome;
  foto.loading = "lazy";
  card.appendChild(foto);

  const corpo = document.createElement("div");
  corpo.className = "produto-corpo";

  const nome = document.createElement("h3");
  nome.className = "produto-nome";
  nome.textContent = produto.nome;

  const preco = document.createElement("p");
  preco.className = "produto-preco";
  preco.textContent = moeda.format(produto.preco);

  const meta = document.createElement("p");
  meta.className = "produto-meta";
  meta.textContent = `${produto.prazo_entrega_dias} dia(s) · ⭐ ${produto.avaliacao}`;

  const estoque = document.createElement("p");
  estoque.className = produto.estoque > 0 ? "produto-meta" : "produto-meta produto-esgotado";
  estoque.textContent = produto.estoque > 0 ? `${produto.estoque} em estoque` : "Sem estoque";

  corpo.append(nome, preco, meta, estoque);

  const acoes = document.createElement("div");
  acoes.className = "produto-acoes";
  const pedir = criarBotao(
    "Pedir",
    () => {
      fecharPaineis();
      enviarMensagem(`Quero comprar o ${produto.nome} (id ${produto.id}).`);
    },
    "botao-primario"
  );
  pedir.disabled = produto.estoque <= 0;
  acoes.append(
    pedir,
    criarBotao("Saber mais", () => {
      fecharPaineis();
      enviarMensagem(
        `Me explica o que devo olhar antes de escolher um ${produto.categoria.replace(/-/g, " ")}.`
      );
    })
  );
  corpo.appendChild(acoes);

  card.appendChild(corpo);
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
  fecharPaineis();
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
  if (document.hidden || !identificado) return;
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
    if (err.naoIdentificado) {
      mostrarEntrada();
      return;
    }
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

async function iniciar() {
  const daUrl = numeroDaUrl();
  try {
    if (daUrl) {
      await entrar(daUrl);
    } else {
      aoIdentificar(await pedirJson("/api/sessao"));
      await loadHistory();
      agendarNotificacoes(0);
    }
  } catch (err) {
    mostrarEntrada(daUrl ? err.message : "");
    return;
  }
  abrirPainelDaUrl();
}

iniciar();
