"""ClienteSync, además de push y pull de catálogo, baja el delta de inventario por
ubicación (cursor) y lo aplica (append + flip); no reaplica lo ya bajado."""
from inventario.db import aplicar_migraciones, conectar
from inventario.repositorio_ubicaciones_sqlite import RepositorioMovimientosUbicacionSQLite
from sync_pdv.cliente import ClienteSync
from sync_pdv.outbox import RepositorioOutboxSQLite

MOVS = [{"uuid": "d1", "tipo": "entrada", "producto_id": 1, "cantidad": "50",
         "origen_id": None, "destino_id": 9, "estado": "confirmado", "grupo_uuid": "g1",
         "lote_id": None, "ref": None, "fecha": "2026-07-07T12:00:00",
         "actualizado_en": "2026-07-07T12:00:00"}]


class _TransFake:
    def __init__(self, movs, cursor):
        self.pull_local = None
        self.llamadas = []
        self._movs = movs
        self._cursor = cursor

    def push(self, eventos):
        return [e["uuid"] for e in eventos]

    def pull_catalogo(self, local_id):
        self.pull_local = local_id
        return {"productos": [], "promociones": []}

    def pull_inventario(self, ubicacion_id, desde):
        self.llamadas.append((ubicacion_id, desde))
        return {"movimientos": self._movs, "cursor": self._cursor}


def _cliente(trans):
    conn = conectar(":memory:")
    aplicar_migraciones(conn)
    outbox = RepositorioOutboxSQLite(conn)
    repo_mov = RepositorioMovimientosUbicacionSQLite(conn)
    return ClienteSync(outbox, trans, replica=None, local_id="local-01",
                       repo_movimientos=repo_mov, ubicaciones=[9]), repo_mov


def test_sincronizar_aplica_delta_de_inventario():
    trans = _TransFake(MOVS, "2026-07-07T12:00:00")
    cliente, repo_mov = _cliente(trans)
    cliente.sincronizar()
    assert trans.llamadas == [(9, None)]
    assert repo_mov.stock(9, 1) == 50


def test_sincronizar_de_nuevo_pide_desde_el_cursor_guardado():
    trans = _TransFake(MOVS, "2026-07-07T12:00:00")
    cliente, repo_mov = _cliente(trans)
    cliente.sincronizar()
    cliente.sincronizar()
    assert trans.llamadas == [(9, None), (9, "2026-07-07T12:00:00")]


def test_sin_repo_movimientos_no_llama_pull_inventario():
    trans = _TransFake(MOVS, "2026-07-07T12:00:00")
    conn = conectar(":memory:")
    aplicar_migraciones(conn)
    ClienteSync(RepositorioOutboxSQLite(conn), trans).sincronizar()
    assert trans.llamadas == []
