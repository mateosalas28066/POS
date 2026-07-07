import threading

from inventario.db import conectar, aplicar_migraciones


def test_migraciones_crean_tablas_del_inventario():
    conn = conectar()  # :memory:
    aplicar_migraciones(conn)
    tablas = {fila["name"] for fila in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"categorias", "impuestos", "productos", "lotes",
            "inventario_movimientos"} <= tablas


def test_foreign_keys_activadas():
    conn = conectar()
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_check_same_thread_false_permite_usar_conexion_desde_otro_hilo(tmp_path):
    """El hilo de sincronización abre su propia conexión en el hilo principal
    pero la usa desde un hilo de background: sqlite3 debe permitirlo."""
    ruta = str(tmp_path / "pos.db")
    conn = conectar(ruta, check_same_thread=False)
    aplicar_migraciones(conn)

    errores = []

    def usar_desde_otro_hilo():
        try:
            conn.execute("SELECT 1").fetchone()
        except Exception as e:  # noqa: BLE001
            errores.append(e)

    hilo = threading.Thread(target=usar_desde_otro_hilo)
    hilo.start()
    hilo.join(timeout=5)
    assert errores == []
