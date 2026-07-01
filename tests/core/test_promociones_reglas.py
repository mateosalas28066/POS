from datetime import datetime
from decimal import Decimal

from core.entidades import Promocion
from core.promociones import consumir_unidades, precio_con_promo, promo_vigente

AHORA = datetime(2026, 7, 1, 12, 0)


def _fija(**kw):
    base = dict(producto_id=1, tipo_valor="precio_fijo", valor=Decimal("8000"),
                tipo_duracion="manual")
    base.update(kw)
    return Promocion(**base)


def test_manual_vigente_si_activa():
    assert promo_vigente(_fija(activa=True), AHORA) is True
    assert promo_vigente(_fija(activa=False), AHORA) is False


def test_tiempo_vigente_dentro_del_rango():
    p = _fija(tipo_duracion="tiempo",
              desde=datetime(2026, 7, 1, 0, 0), hasta=datetime(2026, 7, 1, 23, 59))
    assert promo_vigente(p, AHORA) is True


def test_tiempo_no_vigente_fuera_del_rango():
    p = _fija(tipo_duracion="tiempo",
              desde=datetime(2026, 6, 1), hasta=datetime(2026, 6, 30))
    assert promo_vigente(p, AHORA) is False


def test_unidades_vigente_si_restan():
    p = _fija(tipo_duracion="unidades", unidades_limite=Decimal("3"))
    assert promo_vigente(p, AHORA) is True
    agotada = _fija(tipo_duracion="unidades", unidades_limite=Decimal("3"),
                    unidades_restantes=Decimal("0"))
    assert promo_vigente(agotada, AHORA) is False


def test_precio_con_promo_fijo():
    assert precio_con_promo(Decimal("10000"), _fija(valor=Decimal("8000"))) == Decimal("8000")


def test_precio_con_promo_porcentaje():
    p = _fija(tipo_valor="porcentaje", valor=Decimal("0.2"))
    assert precio_con_promo(Decimal("2500"), p) == Decimal("2000")


def test_consumir_unidades_desactiva_al_agotar():
    p = _fija(tipo_duracion="unidades", unidades_limite=Decimal("2"))
    r = consumir_unidades(p, Decimal("2"))
    assert r.unidades_restantes == Decimal("0")
    assert r.activa is False


def test_consumir_unidades_deja_restante_positivo():
    p = _fija(tipo_duracion="unidades", unidades_limite=Decimal("5"))
    r = consumir_unidades(p, Decimal("2"))
    assert r.unidades_restantes == Decimal("3")
    assert r.activa is True
