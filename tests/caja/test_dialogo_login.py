import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from dataclasses import replace  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.entidades import Usuario  # noqa: E402
from core.servicio_usuarios import ServicioUsuarios  # noqa: E402
from caja.dialogos.dialogo_login import DialogoLogin  # noqa: E402


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


def _servicio_con_admin():
    s = ServicioUsuarios(_FakeRepo())
    s.crear("admin", "clave1234", rol="admin")
    return s


def test_login_ok_setea_usuario():
    _app = QApplication.instance() or QApplication([])
    dlg = DialogoLogin(_servicio_con_admin())
    dlg._nombre.setText("admin")
    dlg._password.setText("clave1234")
    dlg._intentar()
    assert dlg.usuario is not None
    assert dlg.usuario.rol == "admin"


def test_login_fallido_muestra_error_y_no_setea_usuario():
    _app = QApplication.instance() or QApplication([])
    dlg = DialogoLogin(_servicio_con_admin())
    dlg._nombre.setText("admin")
    dlg._password.setText("incorrecta")
    dlg._intentar()
    assert dlg.usuario is None
    assert dlg._estado.text() != ""
