"""Catálogo de produtos mockado, simulando o que seria uma integração real
com o catálogo/estoque do Magalu.

Cada categoria tem no mínimo 4 produtos com preço, prazo, avaliação e
estoque bem distribuídos, de propósito, pra que comparação e sugestão
tenham trade-offs reais (o mais barato raramente é o melhor avaliado).
"""

# (nome, preco, prazo_entrega_dias, avaliacao, estoque, descricao)
CATALOGO_POR_CATEGORIA = {
    "notebooks": [
        ("Notebook Titan X15", 4899.90, 3, 4.7, 12, "Gamer, RTX 4060, 16GB RAM, SSD 512GB."),
        ("Notebook Essencial 14", 2599.00, 6, 4.3, 30, "Uso diário, 8GB RAM, SSD 256GB."),
        ("Notebook UltraBook Air 13", 5799.00, 2, 4.8, 8, "Ultrafino, 1.2kg, 16GB RAM, SSD 1TB, 12h de bateria."),
        ("Notebook Estudo Plus 15", 3299.00, 5, 4.1, 22, "Intel i5, 8GB RAM, SSD 512GB, tela 15.6 Full HD."),
        ("Notebook Workstation Pro 17", 8499.00, 8, 4.6, 4, "17'', 32GB RAM, SSD 1TB, placa dedicada pra renderização."),
        ("Notebook Chromebook 11", 1499.0, 4, 3.8, 40, "Leve, bateria de 12h, ideal pra navegar e estudar."),
        ("Notebook Criador 16 OLED", 7299.0, 6, 4.8, 5, "Tela OLED 16'', 32GB RAM, calibrada pra edição de cor."),
        ("Notebook 2 em 1 Touch 14", 4199.0, 5, 4.4, 14, "Tela sensível ao toque, dobra 360 graus, caneta inclusa."),
    ],
    "celulares": [
        ("Smartphone Nova 5G", 1899.00, 2, 4.5, 45, "128GB, câmera tripla, bateria 5000mAh."),
        ("Smartphone Prime Lite", 999.00, 5, 4.0, 60, "64GB, ótimo custo-benefício pra uso básico."),
        ("Smartphone Galaxy Vision Ultra", 6299.00, 3, 4.9, 10, "512GB, câmera 200MP, tela 6.8'' 120Hz."),
        ("Smartphone Nova Pro 5G", 2799.00, 3, 4.6, 28, "256GB, 12GB RAM, carregamento rápido de 67W."),
        ("Smartphone Basic Go", 699.00, 7, 3.7, 90, "32GB, tela 6.1'', pra quem quer só o essencial."),
        ("Smartphone Rugged Force", 2199.00, 6, 4.4, 15, "À prova d'água e de queda, bateria 6000mAh."),
        ("Smartphone Dobrável Flip", 5499.0, 5, 4.5, 6, "Dobrável, tela interna de 6.7'', cabe no bolso fechado."),
        ("Smartphone Nova Plus 5G", 2299.0, 3, 4.5, 32, "256GB, tela 120Hz, câmera com estabilização óptica."),
        ("Smartphone Sênior Teclas Grandes", 449.0, 6, 4.0, 50, "Teclas grandes, som alto, botão de emergência."),
    ],
    "tvs": [
        ("Smart TV 55'' 4K", 2299.00, 4, 4.6, 18, "4K, HDR, apps de streaming integrados."),
        ("Smart TV 43'' Full HD", 1499.00, 5, 4.2, 25, "Full HD, 2 entradas HDMI, ideal pra quarto."),
        ("Smart TV 65'' QLED 4K", 4199.00, 6, 4.8, 9, "QLED, 120Hz, ótima pra jogos e filmes."),
        ("Smart TV 75'' 8K Premium", 8999.00, 9, 4.7, 3, "8K, painel Mini LED, som Dolby Atmos."),
        ("Smart TV 32'' HD", 999.00, 3, 3.9, 40, "HD, compacta, entradas USB e HDMI."),
        ("Smart TV 50'' 4K", 1899.0, 4, 4.4, 22, "50 polegadas, 4K, HDR10, três entradas HDMI."),
        ("Smart TV 60'' 4K QLED", 3299.0, 6, 4.6, 11, "60 polegadas, QLED, 120Hz, som Dolby."),
        ("Smart TV 85'' 4K Gigante", 11999.0, 12, 4.7, 2, "85 polegadas, 4K, ideal pra sala grande."),
    ],
    "audio": [
        ("Fone de Ouvido Bluetooth ProSound", 349.90, 2, 4.8, 80, "Cancelamento de ruído ativo, 30h de bateria."),
        ("Fone de Ouvido Bluetooth Básico", 89.90, 7, 3.9, 120, "Bluetooth 5.0, 8h de bateria, uso casual."),
        ("Fone de Ouvido TWS AirBeat", 229.90, 3, 4.5, 65, "In-ear sem fio, estojo com carga, resistente a suor."),
        ("Headset Gamer ThunderX", 449.00, 4, 4.6, 30, "Som surround 7.1, microfone com cancelamento de ruído."),
        ("Fone de Ouvido Studio Monitor", 899.00, 5, 4.9, 12, "Over-ear com fio, resposta plana pra produção musical."),
        ("Fone TWS com Cancelamento", 699.0, 3, 4.7, 30, "Sem fio, cancelamento ativo, 8h por carga."),
        ("Fone Esportivo com Gancho", 179.0, 4, 4.2, 70, "Gancho na orelha, resistente a suor, não cai correndo."),
        ("Fone Over-ear Bluetooth 60h", 549.0, 4, 4.6, 25, "60 horas de bateria, dobrável, com estojo rígido."),
    ],
    "caixas-de-som": [
        ("Caixa de Som Bluetooth Boom 20W", 259.00, 3, 4.4, 55, "20W RMS, à prova d'água IPX7, 12h de bateria."),
        ("Caixa de Som Portátil Mini", 99.90, 6, 3.8, 100, "5W, compacta, entrada P2 e Bluetooth."),
        ("Caixa de Som Party Tower 300W", 1299.00, 7, 4.6, 14, "300W, luzes LED, entrada pra microfone e violão."),
        ("Soundbar Cinema 2.1", 899.00, 4, 4.5, 20, "2.1 canais com subwoofer sem fio, HDMI ARC."),
    ],
    "geladeiras": [
        ("Geladeira Frost Free 400L", 3199.00, 10, 4.4, 7, "Frost free, 400 litros, classificação A."),
        ("Geladeira Duplex 300L", 2299.00, 8, 4.1, 12, "Duplex, 300 litros, degelo manual."),
        ("Geladeira French Door 540L", 6799.00, 12, 4.8, 3, "French door, 540 litros, dispenser de água e gelo."),
        ("Geladeira Inverse 450L", 4299.0, 10, 4.6, 8, "Inverse, freezer embaixo, 450 litros, frost free."),
        ("Geladeira Side by Side 560L", 7999.0, 12, 4.7, 4, "Side by side, 560 litros, painel externo de controle."),
        ("Geladeira Retrô 300L", 3899.0, 9, 4.4, 6, "Visual retrô, 300 litros, puxador cromado."),
        ("Frigobar 120L", 1099.00, 5, 4.0, 25, "120 litros, ideal pra quarto ou escritório."),
    ],
    "maquinas-de-lavar": [
        ("Máquina de Lavar 11kg", 2199.00, 9, 4.5, 10, "11kg, 12 programas, dispensador automático."),
        ("Máquina de Lavar 8kg", 1599.00, 7, 4.2, 18, "8kg, 8 programas, econômica."),
        ("Lava e Seca 13kg", 4299.00, 11, 4.7, 5, "Lava e seca 13kg, motor inverter silencioso."),
        ("Tanquinho 10kg", 749.00, 6, 3.9, 30, "Semiautomático, 10kg, baixo consumo de água."),
    ],
    "micro-ondas": [
        ("Micro-ondas 30L Inox", 899.00, 5, 4.5, 22, "30 litros, inox, 10 níveis de potência."),
        ("Micro-ondas 20L Branco", 549.00, 6, 4.1, 35, "20 litros, compacto, 8 programas automáticos."),
        ("Micro-ondas 45L com Grill", 1499.00, 8, 4.6, 8, "45 litros, função grill e dourador."),
        ("Micro-ondas 17L Compacto", 449.00, 4, 3.8, 40, "17 litros, ideal pra cozinhas pequenas."),
    ],
    "fogoes": [
        ("Fogão 4 Bocas Inox", 1099.00, 7, 4.3, 15, "4 bocas, acendimento automático, forno de 56L."),
        ("Fogão 5 Bocas Vidro", 1699.00, 8, 4.6, 10, "5 bocas, mesa de vidro, forno autolimpante."),
        ("Cooktop 4 Bocas Indução", 2499.00, 6, 4.7, 6, "Indução, 4 zonas, timer e trava de segurança."),
        ("Fogão 6 Bocas Profissional", 3799.00, 12, 4.8, 3, "6 bocas, alta potência, forno duplo."),
    ],
    "ar-condicionado": [
        ("Ar-Condicionado Split 9000 BTUs", 1899.00, 9, 4.4, 14, "Split 9000 BTUs, inverter, classificação A."),
        ("Ar-Condicionado Split 12000 BTUs", 2399.00, 10, 4.6, 9, "Split 12000 BTUs, inverter, com Wi-Fi."),
        ("Ar-Condicionado Portátil 10000 BTUs", 2799.00, 5, 3.9, 12, "Portátil, sem instalação, 10000 BTUs."),
        ("Ar-Condicionado Split 18000 BTUs", 3499.00, 12, 4.7, 5, "Split 18000 BTUs, ideal pra ambientes grandes."),
    ],
    "ventiladores": [
        ("Ventilador de Coluna 40cm", 299.00, 4, 4.2, 40, "40cm, 3 velocidades, oscilação automática."),
        ("Ventilador de Mesa 30cm", 149.00, 3, 3.9, 70, "30cm, silencioso, 3 velocidades."),
        ("Ventilador de Teto com Luz", 449.00, 7, 4.4, 20, "3 pás, luminária integrada, controle de parede."),
        ("Circulador de Ar Turbo", 379.00, 5, 4.5, 25, "Alta vazão, ideal pra ambientes amplos."),
    ],
    "air-fryers": [
        ("Air Fryer 4L Digital", 449.00, 3, 4.6, 45, "4 litros, painel digital, 8 programas."),
        ("Air Fryer 3L Mecânica", 299.00, 5, 4.2, 60, "3 litros, timer mecânico, fácil de limpar."),
        ("Air Fryer Oven 12L", 899.00, 6, 4.7, 15, "12 litros, função forno, assa frango inteiro."),
        ("Air Fryer 6L Família", 649.00, 4, 4.5, 28, "6 litros, cesto grande, ideal pra 4 pessoas."),
        ("Air Fryer Dupla 8L", 1099.0, 5, 4.8, 12, "Dois cestos independentes, prepara dois pratos ao mesmo tempo."),
        ("Air Fryer 2L Individual", 219.0, 4, 4.0, 55, "2 litros, ocupa pouco espaço, pra uma pessoa."),
    ],
    "cafeteiras": [
        ("Cafeteira Expresso Automática", 1299.00, 5, 4.7, 12, "Expresso automática, moedor integrado, vaporizador."),
        ("Cafeteira Elétrica 30 Cafés", 199.00, 4, 4.1, 55, "Filtro permanente, jarra de vidro de 1.8L."),
        ("Cafeteira de Cápsulas Compacta", 549.00, 3, 4.5, 30, "Cápsulas, aquece em 25s, pressão de 19 bar."),
        ("Cafeteira Italiana Inox 6 Doses", 129.00, 6, 4.3, 40, "Moka em inox, 6 doses, serve fogão e indução."),
    ],
    "liquidificadores": [
        ("Liquidificador 1200W 12 Velocidades", 349.00, 4, 4.5, 35, "1200W, copo de vidro de 2L, 12 velocidades."),
        ("Liquidificador Básico 550W", 129.00, 6, 3.8, 80, "550W, copo plástico de 1.5L, 2 velocidades."),
        ("Mixer de Mão 800W", 249.00, 3, 4.4, 45, "800W, hastes em inox, com processador e batedor."),
        ("Liquidificador Turbo 1500W Inox", 599.00, 5, 4.7, 18, "1500W, lâminas em inox, função pulsar e gelo."),
    ],
    "aspiradores": [
        ("Aspirador Robô Wi-Fi", 1899.00, 6, 4.6, 12, "Robô com mapeamento, controle por app, função mop."),
        ("Aspirador Vertical Sem Fio", 899.00, 4, 4.4, 25, "Sem fio, 45min de autonomia, filtro HEPA."),
        ("Aspirador de Pó 1400W", 399.00, 5, 4.1, 40, "1400W com fio, reservatório de 2L, kit de bicos."),
        ("Aspirador de Pó e Água 20L", 749.00, 7, 4.5, 15, "20 litros, pó e água, ideal pra oficina e carro."),
    ],
    "tablets": [
        ("Tablet 10'' 128GB", 1699.00, 4, 4.4, 20, "10'', 128GB, 4GB RAM, Wi-Fi."),
        ("Tablet 8'' 64GB Infantil", 899.00, 5, 4.2, 30, "8'', capa emborrachada, controle parental."),
        ("Tablet Pro 12'' 256GB", 4299.00, 3, 4.8, 8, "12'' 120Hz, 256GB, suporta caneta e teclado."),
        ("Tablet 10'' 4G 64GB", 1399.00, 6, 4.0, 22, "10'', chip 4G, 64GB, bateria de 7000mAh."),
    ],
    "smartwatches": [
        ("Smartwatch Fit Pulse", 399.00, 3, 4.3, 50, "Monitor cardíaco, de sono e 20 modos esportivos."),
        ("Smartwatch GPS Runner", 1299.00, 4, 4.7, 18, "GPS integrado, 14 dias de bateria, à prova d'água."),
        ("Smartwatch Premium AMOLED", 2499.00, 3, 4.8, 10, "Tela AMOLED, ECG, chamadas por Bluetooth."),
        ("Pulseira Fitness Básica", 149.00, 6, 3.8, 90, "Contador de passos, notificações, 7 dias de bateria."),
    ],
    "consoles": [
        ("Console NextGen 1TB", 4499.00, 5, 4.9, 6, "1TB SSD, 4K a 120fps, 1 controle sem fio."),
        ("Console Compacto Digital 512GB", 2999.00, 4, 4.7, 12, "Digital, 512GB, 4K, sem leitor de disco."),
        ("Console Portátil Handheld", 2299.00, 6, 4.6, 15, "Portátil, tela 7'' touch, dock pra TV."),
        ("Console Retrô 900 Jogos", 349.00, 7, 3.9, 35, "900 jogos clássicos, 2 controles, saída HDMI."),
    ],
    "monitores": [
        ("Monitor 24'' Full HD 75Hz", 799.00, 4, 4.3, 30, "24'' IPS, Full HD, 75Hz, HDMI e VGA."),
        ("Monitor Gamer 27'' 165Hz", 1699.00, 5, 4.7, 14, "27'' QHD, 165Hz, 1ms, FreeSync."),
        ("Monitor 32'' 4K Profissional", 2899.00, 6, 4.8, 7, "32'' 4K, 99% sRGB, USB-C com 65W."),
        ("Monitor 21.5'' HD Básico", 549.00, 6, 3.9, 45, "21.5'', Full HD, 60Hz, ideal pra escritório."),
        ("Monitor Ultrawide 34'' QHD", 3499.0, 7, 4.7, 8, "Ultrawide 34'', curvo, substitui dois monitores."),
        ("Monitor Portátil 15.6'' USB-C", 1199.0, 5, 4.3, 18, "Portátil, liga por um cabo USB-C, cabe na mochila."),
    ],
    "teclados": [
        ("Teclado Mecânico RGB", 449.00, 3, 4.7, 35, "Switch blue, RGB por tecla, layout ABNT2."),
        ("Teclado Sem Fio Slim", 179.00, 4, 4.3, 60, "Sem fio 2.4GHz, slim, silencioso."),
        ("Teclado Gamer Semi-Mecânico", 249.00, 5, 4.1, 45, "Semi-mecânico, anti-ghosting, RGB."),
        ("Teclado Mecânico Compacto 60%", 599.00, 4, 4.8, 20, "Layout 60%, hot-swap, Bluetooth e USB-C."),
    ],
    "mouses": [
        ("Mouse Gamer 16000 DPI", 249.00, 3, 4.6, 50, "16000 DPI, 7 botões programáveis, RGB."),
        ("Mouse Sem Fio Básico", 79.90, 5, 4.0, 100, "Sem fio, 1200 DPI, ambidestro."),
        ("Mouse Ergonômico Vertical", 199.00, 6, 4.4, 30, "Vertical, reduz esforço no punho, sem fio."),
        ("Mouse Gamer Sem Fio Pro", 599.00, 4, 4.8, 15, "Sem fio de 1ms, 26000 DPI, 70g."),
        ("Mouse Trackball Ergonômico", 379.0, 6, 4.4, 22, "Trackball, não exige mover o braço, alivia o ombro."),
        ("Mouse Silencioso Sem Fio", 129.0, 4, 4.3, 65, "Clique silencioso, bom pra escritório compartilhado."),
    ],
    "impressoras": [
        ("Impressora Multifuncional Tanque de Tinta", 1299.00, 5, 4.6, 20, "Tanque de tinta, Wi-Fi, imprime, copia e digitaliza."),
        ("Impressora Laser Mono", 1099.00, 6, 4.4, 15, "Laser monocromática, 30ppm, rede e Wi-Fi."),
        ("Impressora Jato de Tinta Compacta", 549.00, 4, 3.9, 30, "Compacta, Wi-Fi, ideal pra baixo volume."),
        ("Impressora Laser Color", 2799.00, 8, 4.5, 6, "Laser colorida, duplex automático, com rede."),
    ],
    "cadeiras": [
        ("Cadeira Gamer Reclinável", 1299.00, 7, 4.5, 18, "Reclina 180°, apoio lombar, almofadas inclusas."),
        ("Cadeira de Escritório Presidente", 899.00, 6, 4.2, 25, "Couro sintético, relax, base giratória."),
        ("Cadeira Ergonômica Tela Mesh", 1899.00, 8, 4.8, 10, "Tela mesh, apoio lombar ajustável, braços 4D."),
        ("Cadeira Escritório Básica", 399.00, 5, 3.8, 40, "Giratória, altura a gás, encosto médio."),
    ],
    "colchoes": [
        ("Colchão Queen Molas Ensacadas", 2499.00, 9, 4.7, 8, "Queen, molas ensacadas, pillow top."),
        ("Colchão Solteiro Espuma D33", 799.00, 6, 4.1, 25, "Solteiro, espuma D33, selo do Inmetro."),
        ("Colchão King Látex Premium", 4999.00, 12, 4.8, 4, "King, látex natural, 7 zonas de conforto."),
        ("Colchão Casal Espuma D28", 1199.00, 7, 4.0, 20, "Casal, espuma D28, tecido antiácaro."),
    ],
    "sofas": [
        ("Sofá Retrátil 3 Lugares", 2799.00, 12, 4.5, 7, "Retrátil e reclinável, 3 lugares, suede."),
        ("Sofá 2 Lugares Compacto", 1299.00, 9, 4.1, 15, "2 lugares, pés de madeira, tecido linho."),
        ("Sofá de Canto 5 Lugares", 4599.00, 14, 4.7, 4, "De canto com chaise, 5 lugares, veludo."),
        ("Poltrona Decorativa", 799.00, 8, 4.3, 20, "Poltrona pé palito, tecido bouclê."),
    ],
    "bicicletas": [
        ("Bicicleta Mountain Bike Aro 29", 1899.00, 8, 4.5, 12, "Aro 29, 21 marchas, freio a disco."),
        ("Bicicleta Urbana Aro 26", 999.00, 6, 4.0, 20, "Aro 26, 6 marchas, garupa e paralamas."),
        ("Bicicleta Elétrica Aro 26", 5499.00, 10, 4.7, 5, "Elétrica, autonomia de 60km, motor de 350W."),
        ("Bicicleta Infantil Aro 16", 549.00, 5, 4.2, 30, "Aro 16, rodinhas removíveis, de 4 a 7 anos."),
    ],
    "cameras": [
        ("Câmera Mirrorless 24MP", 4999.00, 5, 4.8, 6, "Mirrorless 24MP, vídeo 4K, lente 18-55mm."),
        ("Câmera de Ação 4K", 899.00, 4, 4.4, 25, "4K a 60fps, à prova d'água, com estabilização."),
        ("Câmera de Segurança Wi-Fi Interna", 249.00, 3, 4.3, 60, "Wi-Fi, visão noturna, áudio bidirecional."),
        ("Câmera Instantânea", 599.00, 4, 4.5, 20, "Fotos instantâneas, flash automático."),
        ("Câmera Mirrorless Full Frame 33MP", 12999.00, 8, 4.9, 2, "Full frame 33MP, vídeo 4K 60fps, estabilização no corpo."),
        ("Webcam Full HD com Microfone", 299.00, 3, 4.2, 55, "1080p a 30fps, foco automático, microfone duplo."),
    ],
    "fornos-eletricos": [
        ("Forno Elétrico 45L", 749.00, 6, 4.4, 18, "45 litros, timer, grill e dourador."),
        ("Forno Elétrico 12L Compacto", 329.00, 4, 3.9, 40, "12 litros, cabe em bancada pequena."),
        ("Forno Elétrico 80L Bancada", 1349.00, 8, 4.7, 9, "80 litros, convecção e espeto giratório."),
        ("Forno de Embutir 60L Inox", 2499.00, 11, 4.6, 5, "De embutir, 60 litros, inox, autolimpante."),
    ],
    "lava-loucas": [
        ("Lava-louças 8 Serviços", 2299.00, 9, 4.4, 12, "8 serviços, 6 programas, compacta."),
        ("Lava-louças 10 Serviços Inox", 3199.00, 10, 4.6, 7, "10 serviços, inox, ciclo rápido."),
        ("Lava-louças de Bancada 6 Serviços", 1699.00, 6, 4.1, 20, "De bancada, dispensa instalação hidráulica fixa."),
        ("Lava-louças 14 Serviços Premium", 4899.00, 13, 4.8, 3, "14 serviços, secagem por condensação, silenciosa."),
    ],
    "purificadores": [
        ("Purificador de Água Gelada", 899.00, 5, 4.5, 30, "Refrigerado por compressor, água natural e gelada."),
        ("Purificador de Água Natural", 449.00, 4, 4.0, 45, "Sem refrigeração, filtragem em três estágios."),
        ("Purificador com Água Quente", 1499.00, 7, 4.6, 12, "Natural, gelada e quente, com trava de segurança."),
        ("Filtro de Barro 8L", 189.00, 6, 4.2, 60, "Cerâmica natural, 8 litros, sem energia elétrica."),
    ],
    "roteadores": [
        ("Roteador Wi-Fi 6 Dual Band", 449.00, 3, 4.6, 35, "Wi-Fi 6, dual band, 4 antenas, cobre 120m²."),
        ("Roteador Wi-Fi 5 Básico", 149.00, 5, 3.9, 80, "Wi-Fi 5, 300Mbps, ideal pra apartamento pequeno."),
        ("Sistema Mesh 3 Pontos", 1299.00, 4, 4.8, 14, "Malha com 3 pontos, cobre 300m² sem queda de sinal."),
        ("Roteador Gamer Wi-Fi 6E", 999.00, 5, 4.7, 10, "Wi-Fi 6E, prioriza tráfego de jogo, baixa latência."),
    ],
    "armazenamento": [
        ("SSD Externo 1TB USB-C", 649.00, 3, 4.7, 40, "1TB, USB-C, leitura de 1050MB/s, resistente a queda."),
        ("HD Externo 2TB", 449.00, 4, 4.3, 55, "2TB, USB 3.0, alimentação pelo cabo."),
        ("Pen Drive 128GB", 89.00, 3, 4.1, 120, "128GB, USB 3.2, corpo metálico."),
        ("Cartão de Memória 256GB", 199.00, 4, 4.5, 70, "256GB, classe 10, grava vídeo 4K sem travar."),
    ],
    "grills": [
        ("Grill e Sanduicheira 3 em 1", 279.00, 4, 4.4, 45, "Grill, sanduicheira e waffle, chapas removíveis."),
        ("Grill Elétrico Antiaderente", 189.00, 5, 4.0, 60, "Chapa antiaderente, dreno de gordura."),
        ("Churrasqueira Elétrica 2200W", 599.00, 6, 4.5, 22, "2200W, uso interno, sem fumaça."),
        ("Sanduicheira Compacta", 99.00, 4, 3.8, 90, "Compacta, aquecimento rápido, luz indicadora."),
    ],
    "panelas-eletricas": [
        ("Panela de Pressão Elétrica 6L", 549.00, 5, 4.6, 28, "6 litros, 12 programas, cozinha feijão em 20min."),
        ("Panela Elétrica de Arroz 1,8L", 229.00, 4, 4.2, 50, "1,8 litro, desliga sozinha, mantém aquecido."),
        ("Multiprocessador Elétrico 5L", 899.00, 6, 4.7, 15, "5 litros, refoga, cozinha e mantém temperatura."),
        ("Fritadeira Elétrica com Óleo 3L", 319.00, 5, 3.9, 35, "3 litros de óleo, cesto removível, termostato."),
    ],
    "secadores": [
        ("Secador de Cabelo 2000W", 199.00, 3, 4.4, 65, "2000W, íons, duas velocidades e três temperaturas."),
        ("Secador Profissional 2400W", 449.00, 4, 4.7, 25, "2400W, motor AC, difusor e concentrador."),
        ("Secador de Viagem Dobrável", 119.00, 5, 3.9, 80, "Cabo dobrável, bivolt, cabe na mala de mão."),
        ("Escova Secadora Rotativa", 329.00, 4, 4.5, 30, "Seca e modela ao mesmo tempo, cerdas rotativas."),
    ],
    "barbeadores": [
        ("Barbeador Elétrico à Prova d'Água", 349.00, 4, 4.5, 40, "Três lâminas flutuantes, uso seco ou molhado."),
        ("Máquina de Cortar Cabelo Sem Fio", 249.00, 4, 4.4, 45, "Sem fio, 8 pentes, 90min de autonomia."),
        ("Aparador de Pelos Multifuncional", 179.00, 5, 4.1, 55, "Barba, nariz e orelha, 5 acessórios."),
        ("Barbeador de Lâmina Recarregável", 599.00, 5, 4.7, 18, "Cabeça 3D, base de limpeza automática."),
    ],
    "climatizacao": [
        ("Umidificador de Ar 4L", 249.00, 4, 4.3, 40, "4 litros, névoa fria, silencioso pra quarto."),
        ("Desumidificador 12L/dia", 1299.00, 7, 4.6, 12, "Retira 12 litros por dia, ideal pra litoral."),
        ("Aquecedor Elétrico a Óleo", 699.00, 6, 4.5, 20, "7 aletas, termostato, não resseca o ar."),
        ("Aquecedor Halógeno Portátil", 249.00, 4, 3.9, 45, "Aquece rápido, três níveis, desliga se tombar."),
    ],
    "iluminacao": [
        ("Lâmpada Inteligente Wi-Fi RGB", 89.00, 3, 4.4, 100, "16 milhões de cores, controle por app e por voz."),
        ("Kit 4 Lâmpadas LED 9W", 49.00, 5, 4.2, 150, "Kit com 4, branca fria, equivale a 60W."),
        ("Luminária de Mesa LED com USB", 159.00, 4, 4.5, 60, "Três temperaturas, braço articulado, porta USB."),
        ("Fita LED 5m Colorida", 119.00, 4, 4.0, 80, "5 metros, controle remoto, adesiva."),
    ],
    "seguranca": [
        ("Fechadura Digital com Biometria", 899.00, 7, 4.5, 18, "Digital, senha e chave, até 100 digitais."),
        ("Videoporteiro Wi-Fi", 749.00, 6, 4.4, 20, "Atende pelo celular, visão noturna, grava."),
        ("Sensor de Presença Wi-Fi", 149.00, 4, 4.2, 60, "Alerta no celular, alimentado por pilha."),
        ("Cofre Eletrônico 20L", 399.00, 6, 4.3, 25, "20 litros, senha e chave de emergência, aço."),
    ],
}


def _montar_catalogo():
    produtos = []
    for categoria, itens in CATALOGO_POR_CATEGORIA.items():
        for nome, preco, prazo, avaliacao, estoque, descricao in itens:
            produtos.append(
                {
                    "id": len(produtos) + 1,
                    "nome": nome,
                    "categoria": categoria,
                    "preco": preco,
                    "prazo_entrega_dias": prazo,
                    "avaliacao": avaliacao,
                    "estoque": estoque,
                    "descricao": descricao,
                    # Cada produto tem a sua ilustração, gerada a partir da
                    # forma da categoria com uma cor própria. Pra usar foto
                    # real, troque por a URL dela e pronto.
                    "imagem": f"/api/produtos/{len(produtos) + 1}/imagem.svg",
                }
            )
    return produtos


PRODUTOS = _montar_catalogo()
CATEGORIAS = list(CATALOGO_POR_CATEGORIA)


# --- Margem líquida --------------------------------------------------------
#
# Percentual do preço que sobra como lucro líquido depois de custo, imposto,
# frete e taxa de cartão. É o teto de qualquer desconto: sem esse número, um
# cupom é chute em cima do caixa da loja.
#
# Os valores seguem a realidade do varejo brasileiro, onde a margem varia
# muito por tipo de produto: eletrônico de alto valor gira com margem magra
# porque o cliente compara preço centavo a centavo, enquanto eletroportátil e
# acessório sustentam margem bem maior. Vender um notebook de R$ 5.000 pode
# dar menos lucro que vender três liquidificadores.
#
# **É dado mockado, como o resto do catálogo.** Numa integração real isto vem
# do ERP, por SKU e não por categoria, e muda com promoção de fornecedor. A
# substituição é trocar este dicionário por uma consulta, sem tocar em quem
# calcula o cupom.
MARGEM_PADRAO = 0.15

MARGEM_POR_CATEGORIA = {
    # Alto valor, comparação de preço agressiva, margem espremida.
    "celulares": 0.06,
    "notebooks": 0.07,
    "tvs": 0.07,
    "consoles": 0.05,
    "tablets": 0.08,
    "cameras": 0.09,
    "monitores": 0.10,
    "geladeiras": 0.10,
    "maquinas-de-lavar": 0.10,
    "ar-condicionado": 0.11,
    "lava-loucas": 0.11,
    "fogoes": 0.12,
    "bicicletas": 0.12,
    "smartwatches": 0.12,
    "impressoras": 0.12,
    # Impressora é o caso clássico de margem baixa no aparelho e alta no
    # suprimento. Aqui só existe o aparelho, então fica baixa.
    "colchoes": 0.20,
    "sofas": 0.22,
    "cadeiras": 0.20,
    "micro-ondas": 0.15,
    "fornos-eletricos": 0.18,
    "air-fryers": 0.20,
    "cafeteiras": 0.22,
    "liquidificadores": 0.25,
    "panelas-eletricas": 0.24,
    "grills": 0.25,
    "aspiradores": 0.18,
    "ventiladores": 0.24,
    "climatizacao": 0.20,
    "purificadores": 0.22,
    "secadores": 0.26,
    "barbeadores": 0.26,
    "audio": 0.20,
    "caixas-de-som": 0.22,
    "teclados": 0.28,
    "mouses": 0.30,
    "armazenamento": 0.20,
    "roteadores": 0.18,
    "iluminacao": 0.30,
    "seguranca": 0.22,
}


def margem_liquida(produto: dict) -> float:
    """Quanto sobra de lucro na venda deste produto, em reais.

    Categoria sem percentual declarado cai no padrão em vez de estourar: um
    produto novo no catálogo não pode derrubar a criação de cupom, e um
    padrão conservador erra pra menos, oferecendo desconto menor.
    """
    percentual = MARGEM_POR_CATEGORIA.get(produto["categoria"], MARGEM_PADRAO)
    return round(produto["preco"] * percentual, 2)
