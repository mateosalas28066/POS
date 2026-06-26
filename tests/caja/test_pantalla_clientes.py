import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.servicio_clientes import ServicioClientes  # noqa: E402
from caja.pantalla_clientes import PantallaClientes  # noqa: E402


class _FakeRepo:
    def __init__(self):
        self._items = {}
        self._next = 1

    def guardar(self, cliente):
        from dataclasses import replace
        c = replace(cliente, id=self._next)
        self._items[self._next] = c
        self._next += 1
        return c

    def actualizar(self, cliente):
        self._items[cliente.id] = cliente
        return cliente

    def por_id(self, id):
        return self._items.get(id)

    def por_identificacion(self, identificacion):
        return next((c for c in self._items.values()
                     if c.identificacion == identificacion), None)

    def listar(self):
        return list(self._items.values())


def test_crear_agrega_fila_a_la_tabla():
    _app = QApplication.instance() or QApplication([])
    win = PantallaClientes(ServicioClientes(_FakeRepo()))
    win._identificacion.setText("900123")
    win._nombre.setText("Carnes SAS")
    win._al_crear()
    assert win._tabla.rowCount() == 1
    assert "Carnes SAS" in win._tabla.item(0, 1).text()


def test_crear_duplicado_muestra_error():
    _app = QApplication.instance() or QApplication([])
    win = PantallaClientes(ServicioClientes(_FakeRepo()))
    win._identificacion.setText("900123")
    win._nombre.setText("Carnes SAS")
    win._al_crear()
    win._identificacion.setText("900123")
    win._nombre.setText("Otro")
    win._al_crear()
    assert "Error" in win._estado.text()
    assert win._tabla.rowCount() == 1
