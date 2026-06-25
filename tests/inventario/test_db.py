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
