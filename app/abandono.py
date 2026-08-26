"""Quando o cliente está desistindo da compra.

É o gatilho do cupom, e por isso a régua é conservadora: oferecer desconto a
quem ia comprar do mesmo jeito é dinheiro entregue à toa, e é irreversível.
Na dúvida, este módulo diz que não houve abandono.

## O que conta como sinal

O sinal principal é o **silêncio**, que foi o que o produto pediu ("demora
pra responder, levar dias"). Mas silêncio sozinho engana: alguém que sempre
responde no dia seguinte não abandonou nada às 20 horas de silêncio, e
alguém que respondia em dois minutos e sumiu há seis horas provavelmente
desistiu.

Por isso o silêncio é comparado com o **ritmo daquela conversa**, medido nos
intervalos anteriores do próprio cliente. É a diferença entre um limiar fixo
e um limiar que entende a pessoa.

## O que impede o abandono de ser declarado

- **Conversa sem interesse demonstrado.** Quem só perguntou o horário da loja
  não abandonou compra nenhuma, não havia compra.
- **Pedido já fechado.** Se ele comprou, acabou. Silêncio depois disso é
  cliente satisfeito, não carrinho abandonado.
- **Conversa fresca.** Existe um piso absoluto de silêncio, porque cliente
  que está digitando a resposta não pode receber cupom na cara.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

# Piso absoluto. Abaixo disto não se declara abandono, por mais atípico que
# o silêncio pareça: ninguém desiste de uma compra em vinte minutos, e o
# cliente pode só ter ido almoçar.
SILENCIO_MINIMO = timedelta(hours=6)

# Teto. Passou disto, é abandono independente do ritmo da conversa, porque
# nenhum ritmo normal de atendimento tem dois dias de intervalo.
SILENCIO_CONCLUSIVO = timedelta(days=2)

# Quantas vezes o silêncio atual precisa superar o ritmo habitual do cliente
# pra contar como quebra de padrão. Três é folgado de propósito: quem
# responde em 10 minutos precisa sumir por 30 pra levantar suspeita, e ainda
# assim só conta depois do piso de 6 horas.
FATOR_DE_QUEBRA = 3


def _aware(momento: datetime) -> datetime:
    """O banco devolve UTC; comparar ingênuo com ciente estoura TypeError."""
    return momento if momento.tzinfo else momento.replace(tzinfo=timezone.utc)


def ritmo_habitual(momentos_do_cliente: List[datetime]) -> Optional[timedelta]:
    """Quanto tempo esta pessoa costuma levar pra responder.

    Usa a **mediana** dos intervalos, não a média: uma única pausa pra dormir
    levanta a média e faria qualquer silêncio parecer normal depois.

    Precisa de pelo menos dois intervalos pra significar alguma coisa. Com
    menos, devolve `None` e quem chama cai no limiar absoluto.
    """
    if len(momentos_do_cliente) < 3:
        return None

    ordenados = sorted(_aware(m) for m in momentos_do_cliente)
    intervalos = sorted(
        (depois - antes).total_seconds()
        for antes, depois in zip(ordenados, ordenados[1:])
    )
    meio = len(intervalos) // 2
    if len(intervalos) % 2:
        mediana = intervalos[meio]
    else:
        mediana = (intervalos[meio - 1] + intervalos[meio]) / 2
    return timedelta(seconds=mediana)


def avaliar(
    momentos_do_cliente: List[datetime],
    demonstrou_interesse: bool,
    ja_comprou: bool,
    agora: Optional[datetime] = None,
) -> dict:
    """Diz se o cliente parece ter desistido, e por quê.

    Devolve sempre o motivo, inclusive quando a resposta é não: quem chama
    precisa poder explicar a decisão, e um booleano sozinho vira caixa preta
    na hora de entender por que um cupom saiu ou deixou de sair.
    """
    agora = _aware(agora or datetime.now(timezone.utc))

    if not momentos_do_cliente:
        return {"abandonou": False, "motivo": "o cliente nunca escreveu", "silencio": None}

    ultima = max(_aware(m) for m in momentos_do_cliente)
    silencio = agora - ultima
    base = {"silencio": silencio, "ritmo": ritmo_habitual(momentos_do_cliente)}

    if ja_comprou:
        return {**base, "abandonou": False, "motivo": "o pedido já foi fechado"}
    if not demonstrou_interesse:
        return {**base, "abandonou": False, "motivo": "não houve interesse em produto"}
    if silencio < SILENCIO_MINIMO:
        return {
            **base,
            "abandonou": False,
            "motivo": f"silêncio de {_humano(silencio)}, ainda dentro do normal",
        }
    if silencio >= SILENCIO_CONCLUSIVO:
        return {
            **base,
            "abandonou": True,
            "motivo": f"sumiu há {_humano(silencio)}",
        }

    ritmo = base["ritmo"]
    if ritmo and silencio > ritmo * FATOR_DE_QUEBRA:
        return {
            **base,
            "abandonou": True,
            "motivo": (
                f"costuma responder em {_humano(ritmo)} e está há "
                f"{_humano(silencio)} sem falar"
            ),
        }

    return {
        **base,
        "abandonou": False,
        "motivo": f"silêncio de {_humano(silencio)} compatível com o ritmo da conversa",
    }


def _humano(intervalo: timedelta) -> str:
    horas = intervalo.total_seconds() / 3600
    if horas < 1:
        return f"{int(intervalo.total_seconds() // 60)} min"
    if horas < 48:
        return f"{horas:.0f}h"
    return f"{horas / 24:.0f} dias"
