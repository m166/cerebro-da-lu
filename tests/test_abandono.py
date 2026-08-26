"""Detecção de que o cliente está desistindo da compra.

É o gatilho do cupom, então errar pra mais custa dinheiro: dar desconto a
quem ia comprar do mesmo jeito é margem entregue de graça, e não dá pra
desfazer. Na dúvida, o módulo diz que não houve abandono, e a maioria dos
testes abaixo verifica exatamente essa recusa.
"""

from datetime import datetime, timedelta, timezone

from app import abandono

AGORA = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)


def _ha(**kwargs):
    return AGORA - timedelta(**kwargs)


def _avaliar(momentos, interesse=True, comprou=False):
    return abandono.avaliar(momentos, interesse, comprou, agora=AGORA)


# --- O piso e o teto --------------------------------------------------------

def test_silencio_curto_nao_e_abandono():
    """Cliente pode ter ido almoçar. Ninguém desiste em vinte minutos."""
    assert _avaliar([_ha(minutes=20)])["abandonou"] is False


def test_silencio_de_dias_e_abandono_conclusivo():
    resultado = _avaliar([_ha(days=3)])
    assert resultado["abandonou"] is True
    assert "sumiu há" in resultado["motivo"]


def test_logo_abaixo_do_piso_ainda_nao_conta():
    """Fronteira exata: o piso existe pra não constranger quem está digitando."""
    quase = abandono.SILENCIO_MINIMO - timedelta(minutes=1)
    assert _avaliar([AGORA - quase])["abandonou"] is False


# --- O ritmo da pessoa ------------------------------------------------------

def test_quem_responde_rapido_e_some_levanta_suspeita():
    """Respondia de 5 em 5 minutos e sumiu há 8 horas: quebrou o padrão."""
    momentos = [
        _ha(hours=9, minutes=15),
        _ha(hours=9, minutes=10),
        _ha(hours=9, minutes=5),
        _ha(hours=8),
    ]
    resultado = _avaliar(momentos)
    assert resultado["abandonou"] is True
    assert "costuma responder" in resultado["motivo"]


def test_quem_sempre_demora_nao_e_acusado_por_demorar():
    """Este é o falso positivo caro: alguém que responde uma vez por dia não
    abandonou nada às 8 horas de silêncio."""
    momentos = [_ha(days=4), _ha(days=3), _ha(days=2), _ha(hours=8)]
    resultado = _avaliar(momentos)
    assert resultado["abandonou"] is False
    assert "compatível com o ritmo" in resultado["motivo"]


def test_ritmo_usa_mediana_e_nao_media():
    """Uma pausa pra dormir levantaria a média e mascararia todo silêncio."""
    momentos = [
        _ha(hours=30),
        _ha(hours=29, minutes=55),   # 5 min
        _ha(hours=10),               # 20h, a noite
        _ha(hours=9, minutes=55),    # 5 min
    ]
    ritmo = abandono.ritmo_habitual(momentos)
    assert ritmo < timedelta(hours=1)


def test_poucas_mensagens_nao_definem_ritmo():
    """Com uma ou duas falas não há padrão, e inventar um seria chute."""
    assert abandono.ritmo_habitual([_ha(hours=5)]) is None
    assert abandono.ritmo_habitual([_ha(hours=5), _ha(hours=4)]) is None


# --- As travas ---------------------------------------------------------------

def test_sem_interesse_nao_ha_o_que_abandonar():
    resultado = _avaliar([_ha(days=3)], interesse=False)
    assert resultado["abandonou"] is False
    assert "interesse" in resultado["motivo"]


def test_quem_comprou_nao_abandonou():
    resultado = _avaliar([_ha(days=3)], comprou=True)
    assert resultado["abandonou"] is False
    assert "pedido já foi fechado" in resultado["motivo"]


def test_conversa_vazia_nao_abandona():
    assert _avaliar([])["abandonou"] is False


def test_data_sem_fuso_nao_estoura():
    """O banco devolve UTC, e comparar ingênuo com ciente daria TypeError."""
    ingenua = (AGORA - timedelta(days=3)).replace(tzinfo=None)
    assert _avaliar([ingenua])["abandonou"] is True


# --- O motivo ---------------------------------------------------------------

def test_sempre_devolve_motivo_legivel():
    """Booleano sozinho vira caixa preta na hora de explicar por que um cupom
    saiu ou deixou de sair."""
    for caso in ([], [_ha(minutes=10)], [_ha(days=3)]):
        assert _avaliar(caso)["motivo"]
