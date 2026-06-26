from dataclasses import replace

import pytest

from core.entidades import Cliente
from core.servicio_clientes import (
    ClienteDuplicado,
    IDENTIFICACION_CONSUMIDOR_FINAL,
    ServicioClientes,
)


class FakeRepoClientes:
    def __init__(self):
        self._items: dict[int, Cliente] = {}
        self._next = 1

    def guardar(self, cliente):
        c = replace(cliente, id=self._next)
        self._items[self._next] = c
        self._next += 1
        return c

    def actualizar(self, cliente):
        if cliente.id not in self._items:
            raise LookupError(cliente.id)
        self._items[cliente.id] = cliente
        return cliente

    def por_id(self, id):
        return self._items.get(id)

    def por_identificacion(self, identificacion):
        return next((c for c in self._items.values()
                     if c.identificacion == identificacion), None)

    def listar(self):
        return list(self._items.values())


def test_crear_persiste_cliente():
    s = ServicioClientes(FakeRepoClientes())
    c = s.crear("900123", "Carnes SAS")
    assert c.id is not None
    assert c.nombre == "Carnes SAS"


def test_crear_rechaza_identificacion_duplicada():
    s = ServicioClientes(FakeRepoClientes())
    s.crear("900123", "Carnes SAS")
    with pytest.raises(ClienteDuplicado):
        s.crear("900123", "Otro Nombre")


def test_crear_exige_nombre_no_vacio():
    s = ServicioClientes(FakeRepoClientes())
    with pytest.raises(ValueError):
        s.crear("900123", "   ")


def test_crear_exige_identificacion_no_vacia():
    s = ServicioClientes(FakeRepoClientes())
    with pytest.raises(ValueError):
        s.crear("  ", "Carnes SAS")


def test_actualizar_exige_id():
    s = ServicioClientes(FakeRepoClientes())
    with pytest.raises(ValueError):
        s.actualizar(Cliente(identificacion="900123", nombre="Carnes SAS"))


def test_actualizar_modifica_cliente():
    s = ServicioClientes(FakeRepoClientes())
    c = s.crear("900123", "Carnes SAS")
    out = s.actualizar(replace(c, nombre="Carnes y Más"))
    assert out.nombre == "Carnes y Más"


def test_buscar_por_identificacion():
    s = ServicioClientes(FakeRepoClientes())
    s.crear("900123", "Carnes SAS")
    assert s.buscar("900123").nombre == "Carnes SAS"
    assert s.buscar("000") is None


def test_consumidor_final_se_resuelve_por_identificacion():
    repo = FakeRepoClientes()
    repo.guardar(Cliente(identificacion=IDENTIFICACION_CONSUMIDOR_FINAL,
                         nombre="Consumidor final"))
    s = ServicioClientes(repo)
    assert s.consumidor_final().identificacion == IDENTIFICACION_CONSUMIDOR_FINAL


def test_consumidor_final_sin_sembrar_lanza_lookuperror():
    s = ServicioClientes(FakeRepoClientes())
    with pytest.raises(LookupError):
        s.consumidor_final()
