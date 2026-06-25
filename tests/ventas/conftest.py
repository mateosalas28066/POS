import pytest

from inventario.db import conectar, aplicar_migraciones


@pytest.fixture
def conn():
    c = conectar()  # :memory:
    aplicar_migraciones(c)
    yield c
    c.close()
