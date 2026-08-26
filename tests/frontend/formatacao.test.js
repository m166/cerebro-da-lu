// Testes das funções puras da tela, com o runner embutido do node:
//
//     node --test tests/frontend/
//
// Não instala nada e não precisa de navegador. O `pytest` também roda estes
// testes (veja tests/test_frontend.py), e pula quando não há node na máquina.
//
// O DOM aqui é um esqueleto de três funções, o suficiente pro `comFormatacao`
// montar nós. Simular o navegador inteiro seria testar o simulador, não o
// código.

const test = require("node:test");
const assert = require("node:assert");
const path = require("node:path");

function noDeTexto(texto) {
  return { tipo: "texto", texto };
}

globalThis.document = {
  createDocumentFragment: () => ({
    filhos: [],
    appendChild(no) {
      this.filhos.push(no);
      return no;
    },
  }),
  createElement: (tag) => ({ tipo: tag, textContent: "" }),
  createTextNode: noDeTexto,
};

const { comFormatacao, formatarData } = require(
  path.join(__dirname, "..", "..", "static", "formatacao.js")
);

// Achata o fragmento em algo comparável: "texto puro" ou "strong:conteúdo".
function render(entrada) {
  return comFormatacao(entrada).filhos.map((no) =>
    no.tipo === "texto" ? no.texto : `${no.tipo}:${no.textContent}`
  );
}

test("negrito usa um asterisco, como no WhatsApp", () => {
  assert.deepStrictEqual(render("sai por *R$ 249* hoje"), [
    "sai por ",
    "strong:R$ 249",
    " hoje",
  ]);
});

test("itálico com underscore e riscado com til", () => {
  assert.deepStrictEqual(render("de _R$ 329_ por ~R$ 400~"), [
    "de ",
    "em:R$ 329",
    " por ",
    "s:R$ 400",
  ]);
});

test("markdown de dois asteriscos não vira negrito limpo", () => {
  // Este é o ponto: `**x**` não é negrito no WhatsApp. O cliente vê o
  // asterisco sobrando, e a tela precisa mostrar isso em vez de esconder.
  const saida = render("**oferta**");
  assert.ok(saida.includes("*"), "o asterisco extra tem que aparecer");
  assert.ok(saida.includes("strong:oferta"));
});

test("asterisco com espaço colado é texto comum", () => {
  assert.deepStrictEqual(render("2 * 3 = 6"), ["2 * 3 = 6"]);
});

test("asterisco solto não quebra nem some", () => {
  assert.deepStrictEqual(render("custa 5* com desconto"), ["custa 5* com desconto"]);
});

test("texto sem marcador nenhum passa inteiro", () => {
  assert.deepStrictEqual(render("chega quinta-feira"), ["chega quinta-feira"]);
});

test("marcador não atravessa quebra de linha", () => {
  const saida = render("*primeira\nsegunda*");
  assert.deepStrictEqual(saida, ["*primeira\nsegunda*"]);
});

test("conteúdo é texto, nunca HTML interpretado", () => {
  // A regra do projeto: nada de montar HTML por concatenação com dado da
  // API. Aqui o que entra vira nó de texto, então tag chega como caractere.
  assert.deepStrictEqual(render("<img src=x onerror=alert(1)>"), [
    "<img src=x onerror=alert(1)>",
  ]);
});

test("formatarData reformata a string sem passar por Date", () => {
  // O bug era este: `new Date("2026-09-15")` é lido como UTC e, no fuso do
  // Brasil, aparece como 14/09, um dia antes do que o cliente agendou.
  assert.strictEqual(formatarData("2026-09-15"), "15/09/2026");
});

test("formatarData aceita data com hora junto", () => {
  assert.strictEqual(formatarData("2026-09-15 18:30:00"), "15/09/2026");
});

test("formatarData devolve vazio pra nulo", () => {
  assert.strictEqual(formatarData(null), "");
  assert.strictEqual(formatarData(""), "");
});

test("formatarData não estraga o que não é data", () => {
  assert.strictEqual(formatarData("em breve"), "em breve");
});
