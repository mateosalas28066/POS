import pytest

from core.entidades import Usuario
from ventas.repositorio_sqlite import RepositorioUsuariosSQLite


def test_guardar_y_leer_por_nombre(conn):
    repo = RepositorioUsuariosSQLite(conn)
    u = repo.guardar(Usuario(nombre="ana", rol="admin"), "hash-x")
    assert u.id is not None
    leido = repo.por_nombre("ana")
    assert leido.rol == "admin"
    assert leido.id == u.id


def test_credencial_devuelve_usuario_y_hash(conn):
    repo = RepositorioUsuariosSQLite(conn)
    repo.guardar(Usuario(nombre="ana"), "hash-x")
    usuario, hash_ = repo.credencial("ana")
    assert usuario.nombre == "ana"
    assert hash_ == "hash-x"


def test_credencial_inexistente_none(conn):
    repo = RepositorioUsuariosSQLite(conn)
    assert repo.credencial("fantasma") is None


def test_actualizar_password_reemplaza_hash(conn):
    repo = RepositorioUsuariosSQLite(conn)
    u = repo.guardar(Usuario(nombre="ana"), "hash-viejo")
    repo.actualizar_password(u.id, "hash-nuevo")
    _, hash_ = repo.credencial("ana")
    assert hash_ == "hash-nuevo"


def test_actualizar_password_usuario_inexistente_falla(conn):
    repo = RepositorioUsuariosSQLite(conn)
    with pytest.raises(LookupError):
        repo.actualizar_password(999, "h")


def test_listar(conn):
    repo = RepositorioUsuariosSQLite(conn)
    repo.guardar(Usuario(nombre="ana"), "h")
    repo.guardar(Usuario(nombre="beto"), "h")
    assert [u.nombre for u in repo.listar()] == ["ana", "beto"]
