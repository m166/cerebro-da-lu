// Formatação de texto da conversa.
//
// Vive fora do script.js porque estas duas funções são puras e passíveis de
// teste: o script.js toca no DOM já na primeira linha, então carregá-lo no
// node exigiria simular a app inteira. Aqui basta um DOM mínimo.
//
// Os testes estão em `tests/frontend/formatacao.test.js` e rodam com
// `node --test`, sem instalar nada.

// O WhatsApp formata com UM marcador de cada lado: *negrito*, _itálico_,
// ~riscado~. Não é markdown, e a diferença importa: `**oferta**` não vira
// negrito lá, o cliente vê os asteriscos na tela.
const MARCADORES = { "*": "strong", _: "em", "~": "s" };

// O padrão é definido uma vez e derivado nas duas formas que o código usa:
// separar e conferir. Ter duas fontes aqui já deu bug: a guarda perguntava
// "começa e termina com o mesmo marcador?", que é verdade também pra trecho
// que a regex recusou, e negrito passava a atravessar quebra de linha.
const PADRAO = /\*[^*\n]+\*|_[^_\n]+_|~[^~\n]+~/;
const SEPARADOR = new RegExp(`(${PADRAO.source})`, "g");
const TRECHO_INTEIRO = new RegExp(`^(?:${PADRAO.source})$`);

function comFormatacao(conteudo) {
  const fragmento = document.createDocumentFragment();
  String(conteudo)
    .split(SEPARADOR)
    .forEach((pedaco) => {
      if (!pedaco) return;
      const tag = MARCADORES[pedaco[0]];
      const miolo = pedaco.slice(1, -1);
      // Espaço colado no marcador não formata no WhatsApp: "* texto *" é
      // texto comum, e tratar como negrito faria a tela mentir.
      const formata = tag && TRECHO_INTEIRO.test(pedaco) && miolo === miolo.trim();
      if (formata) {
        const elemento = document.createElement(tag);
        elemento.textContent = miolo;
        fragmento.appendChild(elemento);
      } else {
        fragmento.appendChild(document.createTextNode(pedaco));
      }
    });
  return fragmento;
}

function formatarData(valor) {
  if (!valor) return "";
  // Reformata a string em vez de usar Date: "2026-09-15" seria lido como
  // UTC e, no fuso do Brasil, exibido como 14/09, um dia antes do que o
  // cliente agendou.
  const [ano, mes, dia] = String(valor).slice(0, 10).split("-");
  return dia ? `${dia}/${mes}/${ano}` : String(valor);
}

// No navegador as funções ficam globais, como antes. `module` só existe no
// node, então esta linha não faz nada na tela do cliente.
if (typeof module !== "undefined" && module.exports) {
  module.exports = { comFormatacao, formatarData, MARCADORES };
}
