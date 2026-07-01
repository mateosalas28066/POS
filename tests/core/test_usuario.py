import pytest

from core.entidades import Usuario


def test_usuario_valido():
    u = Usuario(nombre="ana", rol="admin")
    assert u.nombre == "ana"
    assert u.rol == "admin"


def test_rol_por_defecto_cajero():
    assert Usuario(nombre="ana").rol == "cajero"


def test_rechaza_rol_invalido():
    with pytest.raises(ValueError):
        Usuario(nombre="ana", rol="gerente")


def test_rechaza_nombre_vacio():
    with pytest.raises(ValueError):
        Usuario(nombre="   ")
