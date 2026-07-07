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


def test_ambos_roles_pueden_gestionar_promociones():
    from core.permisos import ACCION_GESTIONAR_PROMOCIONES, puede
    assert puede("admin", ACCION_GESTIONAR_PROMOCIONES) is True
    assert puede("cajero", ACCION_GESTIONAR_PROMOCIONES) is True


@pytest.mark.parametrize("accion", ["gestionar_inventario_multiubicacion", "confirmar_traslado"])
def test_inventario_multiubicacion_es_solo_admin(accion):
    from core.permisos import ACCION_CONFIRMAR_TRASLADO, ACCION_GESTIONAR_INVENTARIO
    assert accion in (ACCION_GESTIONAR_INVENTARIO, ACCION_CONFIRMAR_TRASLADO)
    assert puede("admin", accion) is True
    assert puede("cajero", accion) is False
