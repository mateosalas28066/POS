from caja.bootstrap import preparar_db, sembrar_demo


def test_preparar_db_siembra_categorias_y_productos():
    conn = preparar_db(":memory:")
    cats = conn.execute("SELECT COUNT(*) AS n FROM categorias").fetchone()["n"]
    prods = conn.execute("SELECT COUNT(*) AS n FROM productos").fetchone()["n"]
    assert cats >= 4
    assert prods >= 4
    conn.close()


def test_sembrar_demo_es_idempotente():
    conn = preparar_db(":memory:")
    antes = conn.execute("SELECT COUNT(*) AS n FROM productos").fetchone()["n"]
    sembrar_demo(conn)  # segunda vez
    despues = conn.execute("SELECT COUNT(*) AS n FROM productos").fetchone()["n"]
    assert antes == despues
    conn.close()


def test_productos_tienen_stock_inicial():
    conn = preparar_db(":memory:")
    fila = conn.execute(
        "SELECT COUNT(*) AS n FROM inventario_movimientos WHERE tipo = 'entrada'").fetchone()
    assert fila["n"] >= 4
    conn.close()
