"""Catálogo de produtos mockado, simulando o que seria uma integração real
com o catálogo/estoque do Magalu.

Cada categoria tem no mínimo 4 produtos com preço, prazo, avaliação e
estoque bem distribuídos — de propósito, pra que comparação e sugestão
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
    ],
    "celulares": [
        ("Smartphone Nova 5G", 1899.00, 2, 4.5, 45, "128GB, câmera tripla, bateria 5000mAh."),
        ("Smartphone Prime Lite", 999.00, 5, 4.0, 60, "64GB, ótimo custo-benefício pra uso básico."),
        ("Smartphone Galaxy Vision Ultra", 6299.00, 3, 4.9, 10, "512GB, câmera 200MP, tela 6.8'' 120Hz."),
        ("Smartphone Nova Pro 5G", 2799.00, 3, 4.6, 28, "256GB, 12GB RAM, carregamento rápido de 67W."),
        ("Smartphone Basic Go", 699.00, 7, 3.7, 90, "32GB, tela 6.1'', pra quem quer só o essencial."),
        ("Smartphone Rugged Force", 2199.00, 6, 4.4, 15, "À prova d'água e de queda, bateria 6000mAh."),
    ],
    "tvs": [
        ("Smart TV 55'' 4K", 2299.00, 4, 4.6, 18, "4K, HDR, apps de streaming integrados."),
        ("Smart TV 43'' Full HD", 1499.00, 5, 4.2, 25, "Full HD, 2 entradas HDMI, ideal pra quarto."),
        ("Smart TV 65'' QLED 4K", 4199.00, 6, 4.8, 9, "QLED, 120Hz, ótima pra jogos e filmes."),
        ("Smart TV 75'' 8K Premium", 8999.00, 9, 4.7, 3, "8K, painel Mini LED, som Dolby Atmos."),
        ("Smart TV 32'' HD", 999.00, 3, 3.9, 40, "HD, compacta, entradas USB e HDMI."),
    ],
    "audio": [
        ("Fone de Ouvido Bluetooth ProSound", 349.90, 2, 4.8, 80, "Cancelamento de ruído ativo, 30h de bateria."),
        ("Fone de Ouvido Bluetooth Básico", 89.90, 7, 3.9, 120, "Bluetooth 5.0, 8h de bateria, uso casual."),
        ("Fone de Ouvido TWS AirBeat", 229.90, 3, 4.5, 65, "In-ear sem fio, estojo com carga, resistente a suor."),
        ("Headset Gamer ThunderX", 449.00, 4, 4.6, 30, "Som surround 7.1, microfone com cancelamento de ruído."),
        ("Fone de Ouvido Studio Monitor", 899.00, 5, 4.9, 12, "Over-ear com fio, resposta plana pra produção musical."),
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
                }
            )
    return produtos


PRODUTOS = _montar_catalogo()
CATEGORIAS = list(CATALOGO_POR_CATEGORIA)
