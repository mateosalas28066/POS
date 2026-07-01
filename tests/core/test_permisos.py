import pytest

from core.permisos import (
    ACCION_DESCUENTO_MANUAL, ACCION_EDITAR_PRODUCTOS, ACCION_GESTIONAR_USUARIOS, puede,
)

ACCIONES_ADMIN = [ACCION_GESTIONAR_USUARIOS, ACCION_EDITAR_PRODUCTOS, ACCION_DESCUENTO_MANUAL]


@pytest.mark.parametrize("accion", ACCIONES_ADMIN)
def test_admin_puede_acciones_restringidas(accion):
    assert puede("admin", accion) is True


@pytest.mark.parametrize("accion", ACCIONES_ADMIN)
def test_cajero_no_puede_acciones_restringidas(accion):
    assert puede("cajero", accion) is False


@pytest.mark.parametrize("accion", ["vender", "anular", "devolver", "cerrar_caja"])
def test_cajero_puede_acciones_no_restringidas(accion):
    assert puede("cajero", accion) is True
