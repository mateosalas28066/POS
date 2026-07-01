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


from caja.bootstrap import ADMIN_POR_DEFECTO, sembrar_admin
from core.servicio_usuarios import ServicioUsuarios
from ventas.repositorio_sqlite import RepositorioUsuariosSQLite
from inventario.db import aplicar_migraciones, conectar


def test_sembrar_admin_crea_admin_si_no_hay_usuarios():
    conn = conectar()
    aplicar_migraciones(conn)
    sembrar_admin(conn)
    nombre, password = ADMIN_POR_DEFECTO
    servicio = ServicioUsuarios(RepositorioUsuariosSQLite(conn))
    autenticado = servicio.autenticar(nombre, password)
    assert autenticado is not None
    assert autenticado.rol == "admin"


def test_sembrar_admin_es_idempotente():
    conn = conectar()
    aplicar_migraciones(conn)
    sembrar_admin(conn)
    sembrar_admin(conn)
    total = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    assert total == 1
