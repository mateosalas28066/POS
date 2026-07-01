import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from dataclasses import replace  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.servicio_usuarios import ServicioUsuarios  # noqa: E402
from caja.pantalla_usuarios import PantallaUsuarios  # noqa: E402


class _FakeRepo:
    def __init__(self):
        self._items = {}
        self._hashes = {}
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

    def listar(self):
        return list(self._items.values())


def test_crear_agrega_usuario_a_la_tabla():
    _app = QApplication.instance() or QApplication([])
    win = PantallaUsuarios(ServicioUsuarios(_FakeRepo()))
    win._nombre.setText("ana")
    win._password.setText("clave1234")
    win._al_crear()
    assert win._tabla.rowCount() == 1
    assert "ana" in win._tabla.item(0, 0).text()


def test_crear_sin_password_muestra_error():
    _app = QApplication.instance() or QApplication([])
    win = PantallaUsuarios(ServicioUsuarios(_FakeRepo()))
    win._nombre.setText("ana")
    win._al_crear()
    assert "Error" in win._estado.text()
    assert win._tabla.rowCount() == 0
