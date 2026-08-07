"""Base de conhecimento sobre tecnologia e categorias de produto.

É o corpus do RAG: a Lu consulta estes documentos pra fundamentar uma
recomendação (o que olhar, o que significa cada especificação) em vez de
inventar. O catálogo diz *o que temos*; esta base diz *o que importa*.

`categoria` casa com as categorias de `catalogo.py` quando aplicável, o
que permite filtrar a busca. Documentos gerais usam categoria vazia.
"""

# (titulo, categoria, texto)
_DOCUMENTOS = [
    (
        "Quanta memória RAM um notebook precisa",
        "notebooks",
        "A memória RAM define quantas coisas o computador consegue fazer ao mesmo tempo. "
        "8GB dá conta de navegador, pacote office e streaming — é suficiente pra estudo e "
        "trabalho de escritório. 16GB é o recomendado pra jogos atuais, edição de vídeo leve "
        "e quem deixa dezenas de abas abertas. 32GB só compensa pra renderização 3D, máquinas "
        "virtuais ou edição profissional. Comprar RAM demais é desperdício; de menos trava.",
    ),
    (
        "SSD ou HD, e quanto de armazenamento",
        "notebooks",
        "SSD é muito mais rápido que HD tradicional: o computador liga em segundos e os "
        "programas abrem quase instantaneamente. Hoje qualquer notebook decente vem com SSD. "
        "Sobre tamanho: 256GB é apertado se você guarda fotos e vídeos, 512GB é o ponto de "
        "equilíbrio pra maioria das pessoas, e 1TB é pra quem trabalha com arquivos grandes "
        "ou instala muitos jogos.",
    ),
    (
        "Placa de vídeo dedicada versus integrada",
        "notebooks",
        "A placa de vídeo integrada usa a memória do sistema e dá conta de vídeo, navegação e "
        "jogos leves. A placa dedicada tem memória própria e é necessária pra jogos modernos, "
        "edição de vídeo, modelagem 3D e renderização. Se a pessoa quer jogar ou trabalha com "
        "imagem e vídeo, placa dedicada não é luxo, é requisito. Pra estudo e escritório, "
        "pagar por placa dedicada é dinheiro jogado fora.",
    ),
    (
        "Como escolher o tamanho da tela do notebook",
        "notebooks",
        "Telas de 13 a 14 polegadas são mais leves e melhores pra quem carrega o notebook todo "
        "dia. 15,6 polegadas é o tamanho mais comum e equilibra tela e portabilidade. 17 "
        "polegadas praticamente substitui um desktop: ótimo pra trabalhar, ruim pra carregar. "
        "Peso abaixo de 1,5kg faz diferença real pra quem usa transporte público.",
    ),
    (
        "Megapixels não definem a qualidade da câmera do celular",
        "celulares",
        "Mais megapixels não significa foto melhor. O que mais importa é o tamanho do sensor, "
        "a abertura da lente e o processamento de imagem. Um celular de 12MP com sensor bom "
        "tira fotos melhores que um de 108MP com sensor pequeno, principalmente à noite. "
        "Megapixels altos ajudam quando você quer recortar a foto ou imprimir grande.",
    ),
    (
        "Quanta bateria e armazenamento o celular precisa",
        "celulares",
        "Bateria de 5000mAh costuma durar o dia inteiro em uso normal; abaixo de 4000mAh quem "
        "usa muito precisa recarregar durante o dia. Carregamento rápido (acima de 30W) importa "
        "mais que capacidade pura pra quem esquece de carregar. Sobre armazenamento: 64GB enche "
        "rápido com fotos e vídeos, 128GB serve a maioria, e 256GB ou mais é pra quem grava "
        "muito vídeo ou instala muitos jogos.",
    ),
    (
        "Vale a pena um celular 5G",
        "celulares",
        "O 5G entrega internet móvel mais rápida e com menos atraso, mas só funciona onde há "
        "cobertura — nas capitais está bem distribuído, no interior ainda é irregular. Se a "
        "pessoa troca de celular a cada 4 ou 5 anos, vale garantir o 5G pra não ficar pra trás. "
        "Se troca com frequência e a região não tem cobertura, não é motivo pra pagar mais.",
    ),
    (
        "Qual o tamanho de TV certo pra cada sala",
        "tvs",
        "A regra prática é a distância do sofá dividida por 1,5 pra TVs 4K. Sentado a 2 metros, "
        "uma TV de 50 a 55 polegadas fica confortável; a 3 metros, 65 polegadas. TV grande "
        "demais em ambiente pequeno cansa a vista, e pequena demais desperdiça a resolução. "
        "Pra quarto, de 32 a 43 polegadas costuma ser suficiente.",
    ),
    (
        "4K, 8K, QLED e OLED: o que muda",
        "tvs",
        "4K é o padrão atual e tem conteúdo de sobra em streaming. 8K tem quatro vezes mais "
        "pixels, mas quase não existe conteúdo nativo e a diferença é imperceptível abaixo de "
        "65 polegadas. QLED entrega brilho alto e cores vivas, ótimo em sala clara. OLED tem "
        "preto absoluto e contraste superior, melhor pra assistir filme no escuro. Pra maioria "
        "das pessoas, uma boa TV 4K vale mais que uma 8K de entrada.",
    ),
    (
        "Taxa de atualização da TV importa pra jogar",
        "tvs",
        "A taxa de atualização, medida em Hz, diz quantas imagens a TV mostra por segundo. 60Hz "
        "é suficiente pra filmes e séries, que são gravados em taxas menores. 120Hz faz "
        "diferença real em videogame de nova geração e em esportes, deixando o movimento mais "
        "fluido. Se a pessoa não joga, pagar por 120Hz rende pouco.",
    ),
    (
        "Cancelamento de ruído em fones de ouvido",
        "audio",
        "O cancelamento de ruído ativo usa microfones pra anular o som externo constante — motor "
        "de ônibus, ar-condicionado, avião. Faz muita diferença em transporte público e "
        "escritório barulhento. Não elimina bem vozes e sons agudos repentinos. Se a pessoa usa "
        "o fone em casa em ambiente silencioso, é um recurso que encarece sem entregar valor.",
    ),
    (
        "Fone in-ear, over-ear ou TWS",
        "audio",
        "Os TWS (totalmente sem fio, tipo earbuds) são práticos pra academia e deslocamento, mas "
        "têm menos bateria e som mais limitado. Os over-ear, que cobrem a orelha, entregam som "
        "melhor e mais conforto em uso longo, porém são grandes e esquentam. Fones com fio ainda "
        "ganham em qualidade por preço e não precisam de carga — por isso são o padrão pra "
        "produção musical, onde fidelidade importa mais que praticidade.",
    ),
    (
        "Potência de caixa de som: RMS é o que vale",
        "caixas-de-som",
        "Potência RMS é a que a caixa sustenta de forma contínua e é o número honesto. Potência "
        "PMPO é pico instantâneo e serve mais pra marketing. Pra uso pessoal em quarto, de 10 a "
        "20W RMS basta. Pra sala e reuniões pequenas, de 30 a 60W. Só festa em área externa "
        "justifica centenas de watts. Também vale olhar a certificação de resistência à água "
        "(IPX7 aguenta imersão) pra uso em piscina e praia.",
    ),
    (
        "Litragem de geladeira por tamanho de família",
        "geladeiras",
        "Até 2 pessoas, de 250 a 300 litros resolve. De 3 a 4 pessoas, de 350 a 450 litros. "
        "Acima de 5 pessoas ou quem faz compra grande de mês, 500 litros ou mais. Frost free "
        "evita ter que degelar manualmente e mantém a umidade melhor, mas consome um pouco mais "
        "de energia que o modelo de degelo manual.",
    ),
    (
        "Capacidade de máquina de lavar e o que é lava e seca",
        "maquinas-de-lavar",
        "A conta prática é cerca de 2 a 3kg de capacidade por pessoa da casa: 8kg para 2 ou 3 "
        "pessoas, 11kg para 4 ou 5, acima disso pra famílias grandes ou quem lava cobertor em "
        "casa. A lava e seca economiza espaço e resolve dias de chuva, mas seca menos roupa do "
        "que lava (normalmente cerca de metade da capacidade) e demora bastante no ciclo de "
        "secagem.",
    ),
    (
        "Qual capacidade de air fryer escolher",
        "air-fryers",
        "De 3 a 4 litros serve 1 ou 2 pessoas. De 5 a 6 litros atende uma família de 4. Acima de "
        "10 litros já são modelos tipo forno, que assam frango inteiro e têm mais funções, mas "
        "ocupam bancada e demoram mais pra pré-aquecer. Painel digital facilita repetir "
        "receitas; o mecânico é mais simples e costuma quebrar menos.",
    ),
    (
        "Quantos BTUs de ar-condicionado o ambiente precisa",
        "ar-condicionado",
        "A referência é cerca de 600 a 800 BTUs por metro quadrado, somando mais se o cômodo "
        "pega sol da tarde ou tem muita gente. Na prática: quarto de até 12m² pede 9000 BTUs, "
        "sala de 15 a 20m² pede 12000 BTUs, ambiente de 25 a 30m² pede 18000 BTUs. Aparelho "
        "subdimensionado fica ligado o tempo todo e gasta mais que um do tamanho certo.",
    ),
    (
        "Ar-condicionado inverter compensa",
        "ar-condicionado",
        "O modelo inverter varia a rotação do compressor em vez de ligar e desligar, o que "
        "economiza de 30% a 40% de energia e faz menos barulho. Custa mais caro na compra e "
        "compensa pra quem usa várias horas por dia — em uso esporádico, a economia demora a "
        "pagar a diferença. Modelos portáteis não precisam de instalação, mas são menos "
        "eficientes e mais barulhentos que os split.",
    ),
    (
        "Micro-ondas: litragem e potência",
        "micro-ondas",
        "De 17 a 20 litros atende quem esquenta pratos e faz pipoca. De 25 a 30 litros cabe "
        "travessa e é o tamanho mais versátil pra família. Acima de 40 litros já dá pra usar "
        "como forno auxiliar, com grill e função dourador. Potência maior aquece mais rápido, "
        "mas o que costuma pesar mais no dia a dia é o tamanho do prato giratório.",
    ),
    (
        "Cooktop de indução versus fogão a gás",
        "fogoes",
        "A indução aquece mais rápido, tem controle preciso de temperatura e é mais segura, já "
        "que a superfície esquenta pouco. Exige panelas com fundo magnético e uma instalação "
        "elétrica que aguente a carga. O fogão a gás funciona com qualquer panela, custa menos "
        "e não depende de energia elétrica pra acender — ainda é a escolha mais prática pra "
        "maioria das casas brasileiras.",
    ),
    (
        "Taxa de atualização e tempo de resposta em monitores",
        "monitores",
        "Pra trabalho e estudo, 60 ou 75Hz é confortável. Pra jogos competitivos, 144Hz ou mais "
        "dá vantagem real na fluidez. Tempo de resposta de 1ms evita rastro em movimento rápido. "
        "Sobre o painel: IPS tem as melhores cores e ângulo de visão, sendo o ideal pra design; "
        "VA tem contraste alto; TN é o mais rápido e barato, porém com cores fracas.",
    ),
    (
        "Resolução de monitor por tamanho de tela",
        "monitores",
        "Em 21 a 24 polegadas, Full HD já fica nítido. Em 27 polegadas, o ideal é QHD, porque "
        "Full HD nesse tamanho deixa os pixels visíveis. De 32 polegadas pra cima, 4K faz "
        "diferença clara. Monitor com USB-C que entrega energia permite ligar o notebook com um "
        "cabo só, carregando e transmitindo imagem ao mesmo tempo.",
    ),
    (
        "Teclado mecânico e tipos de switch",
        "teclados",
        "Teclado mecânico tem acionamento individual por tecla: dura muito mais e responde "
        "melhor. Switch azul é barulhento e tem clique marcante, ótimo pra digitar e péssimo "
        "pra ambiente compartilhado. Switch vermelho é linear e silencioso, preferido pra jogos. "
        "Switch marrom fica no meio-termo. Layout ABNT2 é o brasileiro, com tecla de cedilha — "
        "vale conferir, porque teclado sem ela incomoda no dia a dia.",
    ),
    (
        "DPI de mouse e ergonomia",
        "mouses",
        "DPI é a sensibilidade do sensor. Números altíssimos (16000, 26000) viram marketing: a "
        "maioria das pessoas joga entre 800 e 3200 DPI. O que importa mais é a precisão do "
        "sensor e o peso — mouses leves, abaixo de 80g, cansam menos em uso longo. Pra quem "
        "sente dor no punho, o mouse vertical muda a posição da mão e costuma aliviar.",
    ),
    (
        "Impressora a laser ou tanque de tinta",
        "impressoras",
        "Tanque de tinta tem o menor custo por página colorida e é ideal pra quem imprime foto e "
        "documento em casa. Laser monocromática é imbatível pra volume alto de texto: imprime "
        "rápido, o toner rende muito e não seca se ficar parada. Jato de tinta com cartucho só "
        "compensa pra quem imprime pouquíssimo — o cartucho seca e sai caro por página.",
    ),
    (
        "O que faz uma cadeira ser ergonômica",
        "cadeiras",
        "O essencial é apoio lombar ajustável, altura regulável e braços que permitam manter o "
        "cotovelo em 90 graus. Encosto em tela ventila melhor em clima quente; estofado é mais "
        "confortável no frio. Cadeira gamer costuma ter visual esportivo e reclinar bastante, "
        "mas nem toda cadeira gamer é ergonômica de verdade — pra quem passa 8 horas sentado, "
        "o ajuste lombar vale mais que o design.",
    ),
    (
        "Densidade e tipo de colchão",
        "colchoes",
        "A densidade da espuma (D28, D33, D45) indica firmeza e suporte de peso: quanto maior o "
        "número, mais firme e mais peso aguenta. Molas ensacadas se movem de forma independente, "
        "o que evita que um lado balance quando a outra pessoa se mexe — a melhor opção pra "
        "casal. Látex é durável, ventila bem e é hipoalergênico, porém é o mais caro. Pillow top "
        "é a camada extra de conforto sobre o colchão.",
    ),
    (
        "Aro e marchas de bicicleta",
        "bicicletas",
        "O aro 29 rola melhor sobre obstáculos e é o padrão pra trilha em adultos. O aro 26 é "
        "mais ágil e cabe melhor em pessoas mais baixas. Marchas servem pra manter a pedalada "
        "confortável em subida: quem anda só no plano da cidade não precisa de 21 marchas. Freio "
        "a disco funciona muito melhor na chuva que o freio v-brake. Bicicleta elétrica ajuda em "
        "trajeto longo e cidade com ladeira, mas exige recarga e é bem mais pesada.",
    ),
    (
        "Câmera mirrorless, câmera de ação e o celular",
        "cameras",
        "A mirrorless tem sensor grande e lente trocável: é o salto real de qualidade em relação "
        "ao celular, principalmente com pouca luz e para desfocar o fundo. A câmera de ação é "
        "feita pra movimento, resiste a água e queda, mas tem sensor pequeno. Pra foto casual, "
        "um bom celular já resolve — a câmera dedicada compensa quando a pessoa quer aprender "
        "fotografia ou precisa de qualidade profissional.",
    ),
    (
        "Smartwatch: GPS, monitoramento e bateria",
        "smartwatches",
        "GPS integrado permite registrar corrida e pedalada sem levar o celular — quem só quer "
        "contar passos não precisa. Monitoramento cardíaco e de sono existe até nos modelos "
        "básicos; ECG e medição de oxigênio são de linha premium. Atenção à bateria: relógios "
        "com tela AMOLED e muitos recursos duram de 1 a 3 dias, enquanto pulseiras simples "
        "passam de uma semana.",
    ),
    (
        "Console com leitor de disco ou digital",
        "consoles",
        "A versão digital é mais barata, porém você só compra jogo pela loja online, sem "
        "possibilidade de revender, emprestar ou comprar usado. Com leitor de disco dá pra "
        "aproveitar mídia física e o mercado de seminovos, o que costuma compensar a diferença "
        "de preço pra quem joga muitos títulos. Console portátil vale pra quem joga fora de "
        "casa; se o uso é sempre na TV, um modelo de mesa entrega mais desempenho pelo preço.",
    ),
    (
        "Potência de liquidificador e quando usar mixer",
        "liquidificadores",
        "Até 800W dá conta de suco, vitamina e massa de bolo. Acima de 1000W com lâminas de inox "
        "é o que tritura gelo e faz creme mais encorpado sem forçar o motor. Copo de vidro não "
        "mancha nem retém cheiro, mas pesa e quebra; o de plástico é prático e mais leve. O "
        "mixer de mão é melhor pra bater direto na panela — sopa e purê — e ocupa muito menos "
        "espaço na cozinha.",
    ),
    (
        "Tipos de cafeteira",
        "cafeteiras",
        "A elétrica de filtro faz volume grande com custo baixíssimo por xícara e é a melhor pra "
        "casa cheia ou escritório. A de cápsula é a mais prática e consistente, porém a cápsula "
        "encarece muito o café no longo prazo. A expresso automática com moedor entrega a melhor "
        "qualidade, moendo o grão na hora, mas é a mais cara e exige limpeza frequente. A "
        "italiana (moka) é barata, durável e faz café encorpado, exigindo um pouco de prática.",
    ),
    (
        "Aspirador robô, vertical ou com fio",
        "aspiradores",
        "O robô mantém a casa limpa no dia a dia sozinho, mas não substitui uma limpeza pesada e "
        "sofre com tapete grosso e fio solto. O vertical sem fio é prático pra limpeza rápida e "
        "escada, limitado pela bateria (de 30 a 45 minutos). O com fio tem a maior potência e "
        "não acaba no meio do trabalho. Pra quem tem animal em casa, filtro HEPA faz diferença "
        "real na quantidade de pelo e alérgeno no ar.",
    ),
    (
        "Tablet: quando substitui o notebook",
        "tablets",
        "Pra consumir conteúdo — vídeo, leitura, navegação — o tablet é melhor que o notebook por "
        "ser leve e ter bateria longa. Pra produzir texto e planilha, só compensa com teclado "
        "acoplado, e ainda assim com limitações de sistema. Suporte a caneta é o diferencial "
        "real pra quem desenha ou faz anotação à mão. Versão com chip 4G evita depender de "
        "wi-fi, mas exige um plano de dados separado.",
    ),
    (
        "Ventilador de teto, coluna ou circulador",
        "ventiladores",
        "O de teto distribui melhor o ar no ambiente inteiro e não ocupa espaço, porém exige "
        "instalação. O de coluna com oscilação atende bem sala e quarto e pode ser movido. O "
        "circulador tem alta vazão direcionada: renova o ar mais rápido e ajuda a espalhar o "
        "frio do ar-condicionado, o que permite deixar o aparelho em temperatura mais alta e "
        "gastar menos energia.",
    ),
    (
        "Como escolher o tamanho do sofá",
        "sofas",
        "Meça a parede antes: o sofá deve ocupar no máximo dois terços dela, pra circulação não "
        "travar. Dois lugares serve ambiente pequeno e casal. Três lugares é o padrão de sala. "
        "Sofá de canto com chaise aproveita bem o formato em L, mas engole espaço e dificulta "
        "mudar o layout. O modelo retrátil e reclinável é mais confortável pra assistir TV, "
        "porém precisa de folga atrás pra reclinar.",
    ),
    (
        "Voltagem 110V ou 220V e o que acontece se errar",
        "",
        "Antes de comprar qualquer eletrodoméstico, confira a voltagem da tomada onde ele vai "
        "ficar. Ligar um aparelho de 110V em 220V costuma queimá-lo na hora, e o contrário faz "
        "ele funcionar mal ou não ligar. Aparelhos bivolt se adaptam sozinhos e são a escolha "
        "segura pra quem pode mudar de casa. Produtos de alta potência, como ar-condicionado e "
        "forno elétrico, geralmente exigem tomada e disjuntor dedicados.",
    ),
    (
        "Classificação de eficiência energética",
        "",
        "O selo do Procel classifica o consumo de A (mais econômico) até E. Em aparelhos que "
        "ficam ligados o tempo todo — geladeira e ar-condicionado — a diferença entre A e C "
        "aparece na conta de luz todo mês e costuma pagar a diferença de preço em poucos anos. "
        "Em produtos de uso esporádico, o impacto é pequeno e não vale pagar muito mais caro só "
        "pelo selo.",
    ),
    (
        "Garantia, nota fiscal e direito de arrependimento",
        "",
        "A garantia legal é de 90 dias para produto durável, e o fabricante costuma oferecer "
        "garantia adicional de 1 ano. Guarde sempre a nota fiscal: é ela que comprova a data da "
        "compra. Em compra pela internet existe o direito de arrependimento de 7 dias a partir "
        "do recebimento, sem precisar justificar o motivo. Defeito que aparece dentro da "
        "garantia deve ser resolvido em até 30 dias.",
    ),
]

DOCUMENTOS = [
    {"id": indice + 1, "titulo": titulo, "categoria": categoria, "texto": texto}
    for indice, (titulo, categoria, texto) in enumerate(_DOCUMENTOS)
]


def texto_indexavel(documento: dict) -> str:
    """O que vai virar embedding: título junto do corpo dá mais sinal."""
    return f"{documento['titulo']}. {documento['texto']}"
