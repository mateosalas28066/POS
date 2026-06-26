from dataclasses import replace

import pytest

from core.entidades import Cliente
from core.servicio_clientes import (
    IDENTIFICACION_CONSUMIDOR_FINAL,
    ServicioClientes,
)
from ventas.repositorio_sqlite import RepositorioClientesSQLite


def test_actualizar_modifica_cliente(conn):
    repo = RepositorioClientesSQLite(conn)
    c = repo.guardar(Cliente(identificacion="900123", nombre="Carnes SAS"))
    repo.actualizar(replace(c, nombre="Carnes y Más SAS"))
    assert repo.por_id(c.id).nombre == "Carnes y Más SAS"


def test_actualizar_cliente_inexistente_lanza_lookuperror(conn):
    repo = RepositorioClientesSQLite(conn)
    with pytest.raises(LookupError):
        repo.actualizar(Cliente(identificacion="x", nombre="x", id=999))


def test_consumidor_final_sembrado_por_migracion(conn):
    repo = RepositorioClientesSQLite(conn)
    cf = repo.por_identificacion(IDENTIFICACION_CONSUMIDOR_FINAL)
    assert cf is not None
    assert cf.nombre == "Consumidor final"


def test_servicio_consumidor_final_sobre_seed_real(conn):
    servicio = ServicioClientes(RepositorioClientesSQLite(conn))
    assert servicio.consumidor_final().identificacion == IDENTIFICACION_CONSUMIDOR_FINAL
