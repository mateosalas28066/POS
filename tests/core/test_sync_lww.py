from datetime import datetime, timedelta
from core.sync_lww import gana_escritura

T0 = datetime(2026, 7, 7, 10, 0, 0)

def test_entrante_mas_nueva_gana():
    assert gana_escritura(T0 + timedelta(seconds=1), T0) is True

def test_entrante_mas_vieja_pierde():
    assert gana_escritura(T0 - timedelta(seconds=1), T0) is False

def test_igual_no_sobrescribe():
    assert gana_escritura(T0, T0) is False   # LWW estricto: empate conserva lo existente

def test_sin_existente_gana():
    assert gana_escritura(T0, None) is True
