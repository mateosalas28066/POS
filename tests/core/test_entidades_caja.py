from datetime import datetime
from decimal import Decimal
import pytest
from core.entidades import Arqueo, CajaSesion

def test_caja_sesion_minima_abierta():
    s = CajaSesion(apertura_fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("100000"))
    assert s.estado == "abierta"
    assert s.cierre_fecha is None
    assert s.monto_contado is None
    assert s.id is None

def test_caja_sesion_monto_inicial_negativo_falla():
    with pytest.raises(ValueError):
        CajaSesion(apertura_fecha=datetime(2026, 6, 25, 9, 0), monto_inicial=Decimal("-1"))

def test_caja_sesion_estado_invalido_falla():
    with pytest.raises(ValueError):
        CajaSesion(apertura_fecha=datetime(2026, 6, 25, 9, 0),
                   monto_inicial=Decimal("0"), estado="pausada")

def test_caja_sesion_monto_contado_negativo_falla():
    with pytest.raises(ValueError):
        CajaSesion(apertura_fecha=datetime(2026, 6, 25, 9, 0),
                   monto_inicial=Decimal("0"), monto_contado=Decimal("-5"))

def test_arqueo_es_valor_de_lectura():
    a = Arqueo(monto_inicial=Decimal("100000"), efectivo_ventas=Decimal("13000"),
               esperado=Decimal("113000"), contado=Decimal("112000"),
               diferencia=Decimal("-1000"))
    assert a.diferencia == Decimal("-1000")
    assert a.esperado == Decimal("113000")
