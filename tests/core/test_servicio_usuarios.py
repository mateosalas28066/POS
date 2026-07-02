from dataclasses import replace

import pytest

from core.entidades import Usuario
from core.servicio_usuarios import CredencialInvalida, ServicioUsuarios, UsuarioDuplicado


class FakeRepoUsuarios:
    def __init__(self):
        self._items: dict[int, Usuario] = {}
        self._hashes: dict[int, str] = {}
        self._next = 1

    def guardar(self, usuario, hash_password):
        u = replace(usuario, id=self._next)
        self._items[self._next] = u
        self._hashes[self._next] = hash_password
        self._next += 1
        return u

    def por_id(self, id):
        return self._items.get(id)

    def por_nombre(self, nombre):
        return next((u for u in self._items.values() if u.nombre == nombre), None)

    def credencial(self, nombre):
        u = self.por_nombre(nombre)
        return (u, self._hashes[u.id]) if u else None

    def actualizar_password(self, usuario_id, hash_password):
        if usuario_id not in self._items:
            raise LookupError(f"usuario inexistente: id={usuario_id}")
        self._hashes[usuario_id] = hash_password

    def listar(self):
        return list(self._items.values())


def test_crear_persiste_usuario():
    s = ServicioUsuarios(FakeRepoUsuarios())
    u = s.crear("ana", "clave1234", rol="admin")
    assert u.id is not None
    assert u.rol == "admin"


def test_crear_rechaza_nombre_duplicado():
    s = ServicioUsuarios(FakeRepoUsuarios())
    s.crear("ana", "clave1234")
    with pytest.raises(UsuarioDuplicado):
        s.crear("ana", "otra")


def test_crear_exige_password():
    s = ServicioUsuarios(FakeRepoUsuarios())
    with pytest.raises(ValueError):
        s.crear("ana", "")


def test_autenticar_ok():
    s = ServicioUsuarios(FakeRepoUsuarios())
    s.crear("ana", "clave1234")
    assert s.autenticar("ana", "clave1234").nombre == "ana"


def test_autenticar_password_mala_devuelve_none():
    s = ServicioUsuarios(FakeRepoUsuarios())
    s.crear("ana", "clave1234")
    assert s.autenticar("ana", "incorrecta") is None


def test_autenticar_usuario_inexistente_devuelve_none():
    s = ServicioUsuarios(FakeRepoUsuarios())
    assert s.autenticar("fantasma", "x") is None


def test_cambiar_password_permite_autenticar_con_la_nueva():
    s = ServicioUsuarios(FakeRepoUsuarios())
    s.crear("ana", "clave1234")
    s.cambiar_password("ana", "clave1234", "nueva5678")
    assert s.autenticar("ana", "nueva5678") is not None
    assert s.autenticar("ana", "clave1234") is None


def test_cambiar_password_con_actual_incorrecta_falla():
    s = ServicioUsuarios(FakeRepoUsuarios())
    s.crear("ana", "clave1234")
    with pytest.raises(CredencialInvalida):
        s.cambiar_password("ana", "incorrecta", "nueva5678")


def test_cambiar_password_exige_nueva_no_vacia():
    s = ServicioUsuarios(FakeRepoUsuarios())
    s.crear("ana", "clave1234")
    with pytest.raises(ValueError):
        s.cambiar_password("ana", "clave1234", "")
