"""Cableado opcional del hilo de sincronización en background (ContextoApp.crear)."""
from sync_pdv.hilo_sincronizacion import HiloSincronizacion

VARS_SYNC = {
    "LOCAL_ID": "local-01",
    "ALMACEN_ID": "1",
    "SYNC_URL": "http://127.0.0.1:9",  # puerto que no escucha: no debe romper el arranque
    "LOCAL_TOKEN": "tok1",
}


def test_arranca_hilo_de_sync_con_ruta_real_y_env_completo(monkeypatch, tmp_path):
    for k, v in VARS_SYNC.items():
        monkeypatch.setenv(k, v)
    from caja.contexto import ContextoApp

    ruta = str(tmp_path / "pos.db")
    ctx = ContextoApp.crear(ruta)
    try:
        assert isinstance(ctx.hilo_sync, HiloSincronizacion)
    finally:
        ctx.hilo_sync.detener()
        ctx.conn.close()


def test_sin_sync_url_no_arranca_hilo(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCAL_ID", "local-01")
    monkeypatch.setenv("ALMACEN_ID", "1")
    monkeypatch.delenv("SYNC_URL", raising=False)
    monkeypatch.delenv("LOCAL_TOKEN", raising=False)
    from caja.contexto import ContextoApp

    ctx = ContextoApp.crear(str(tmp_path / "pos.db"))
    assert ctx.hilo_sync is None
    ctx.conn.close()


def test_en_memoria_no_arranca_hilo_aunque_haya_env_completo(monkeypatch):
    for k, v in VARS_SYNC.items():
        monkeypatch.setenv(k, v)
    from caja.contexto import ContextoApp

    ctx = ContextoApp.crear(":memory:")
    assert ctx.hilo_sync is None
    ctx.conn.close()
