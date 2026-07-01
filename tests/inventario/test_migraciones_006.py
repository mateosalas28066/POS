from inventario.db import aplicar_migraciones, conectar


def _columnas(conn, tabla):
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({tabla})")}


def test_crea_tabla_promociones():
    conn = conectar()
    aplicar_migraciones(conn)
    cols = _columnas(conn, "promociones")
    assert {"producto_id", "tipo_valor", "valor", "tipo_duracion", "activa",
            "desde", "hasta", "unidades_limite", "unidades_restantes"} <= cols


def test_venta_lineas_tiene_promocion_id():
    conn = conectar()
    aplicar_migraciones(conn)
    assert "promocion_id" in _columnas(conn, "venta_lineas")


def test_aplicar_migraciones_es_idempotente():
    conn = conectar()
    aplicar_migraciones(conn)
    aplicar_migraciones(conn)  # no debe lanzar "duplicate column name"
    assert "promocion_id" in _columnas(conn, "venta_lineas")
