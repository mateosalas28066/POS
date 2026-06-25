def test_migracion_002_crea_tablas_de_venta(conn):
    tablas = {f["name"] for f in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"usuarios", "clientes", "medios_pago", "caja_sesiones",
            "ventas", "venta_lineas", "pagos"} <= tablas


def test_medios_pago_semilla(conn):
    nombres = {f["nombre"] for f in conn.execute("SELECT nombre FROM medios_pago")}
    assert {"Efectivo", "Tarjeta", "Transferencia"} <= nombres
