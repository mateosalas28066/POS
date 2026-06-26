from dataclasses import replace

import pytest

from core.entidades import Cliente
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
