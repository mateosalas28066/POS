"""ClienteSync, además de push, baja el snapshot de catálogo y lo aplica a la réplica."""
from inventario.db import aplicar_migraciones, conectar
from sync_pdv.cliente import ClienteSync
from sync_pdv.outbox import EventoSync, RepositorioOutboxSQLite

SNAP = {"productos": [{"producto_id": 1, "codigo_barras": "0001", "nombre": "Lomo",
                       "unidad": "kg", "vendido_por_peso": True, "categoria_id": 10,
                       "categoria_nombre": "Carnes", "impuesto_id": 5, "tarifa_impuesto": "0.19",
                       "precio": "20000", "costo": "12000",
                       "actualizado_en": "2026-07-07T10:00:00"}], "promociones": []}


class _TransFake:
    def __init__(self):
        self.push_recibido = []
        self.pull_local = None

    def push(self, eventos):
        self.push_recibido.extend(eventos)
        return [e["uuid"] for e in eventos]

    def pull_catalogo(self, local_id):
        self.pull_local = local_id
        return SNAP


class _ReplicaEspia:
    def __init__(self):
        self.aplicado = None

    def aplicar_catalogo(self, snapshot):
        self.aplicado = snapshot


def _repo():
    c = conectar(":memory:")
    aplicar_migraciones(c)
    return RepositorioOutboxSQLite(c)


def test_sincronizar_aplica_snapshot_tras_push():
    repo = _repo()
    repo.encolar(EventoSync("u1", "local-01", "venta", {"total": "10"}, "2026-07-06T10:00:00"))
    trans, replica = _TransFake(), _ReplicaEspia()
    ClienteSync(repo, trans, replica=replica, local_id="local-01").sincronizar()
    assert trans.push_recibido[0]["uuid"] == "u1"
    assert trans.pull_local == "local-01"
    assert replica.aplicado == SNAP


def test_pull_ocurre_aun_sin_pendientes():
    repo = _repo()                               # outbox vacío
    trans, replica = _TransFake(), _ReplicaEspia()
    n = ClienteSync(repo, trans, replica=replica, local_id="local-01").sincronizar()
    assert n == 0                                # nada que subir
    assert replica.aplicado == SNAP             # pero el catálogo se baja igual


def test_sin_replica_no_hace_pull():
    repo = _repo()
    trans = _TransFake()
    ClienteSync(repo, trans).sincronizar()       # sin replica/local_id -> compat Fase 1
    assert trans.pull_local is None
