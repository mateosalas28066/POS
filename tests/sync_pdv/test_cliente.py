from inventario.db import aplicar_migraciones, conectar
from sync_pdv.cliente import ClienteSync
from sync_pdv.outbox import EventoSync, RepositorioOutboxSQLite


class _TransporteFake:
    def __init__(self):
        self.recibidos = []

    def push(self, eventos):
        self.recibidos.extend(eventos)
        return [e["uuid"] for e in eventos]   # acepta todos


def _repo():
    c = conectar(":memory:")
    aplicar_migraciones(c)
    return RepositorioOutboxSQLite(c)


def test_sincronizar_sube_y_marca_enviados():
    repo = _repo()
    repo.encolar(EventoSync("u1", "local-01", "venta", {"total": "10"}, "2026-07-06T10:00:00"))
    transporte = _TransporteFake()
    n = ClienteSync(repo, transporte).sincronizar()
    assert n == 1
    assert transporte.recibidos[0]["uuid"] == "u1"
    assert repo.pendientes() == []           # ya marcados enviados


def test_sincronizar_idempotente_sin_pendientes():
    repo = _repo()
    assert ClienteSync(repo, _TransporteFake()).sincronizar() == 0
