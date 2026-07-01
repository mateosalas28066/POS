from caja.bootstrap import ADMIN_POR_DEFECTO
from caja.contexto import ContextoApp
from core.servicio_venta import ServicioVenta


def test_crear_en_memoria_expone_repos_y_servicios():
    ctx = ContextoApp.crear(":memory:")
    assert ctx.repo_productos.listar()  # seed cargó productos
    assert ctx.repo_medios_pago.listar()  # migración sembró medios
    assert ctx.svc_reportes is not None
    assert ctx.svc_caja is not None
    ctx.conn.close()


def test_nueva_venta_devuelve_instancia_fresca():
    ctx = ContextoApp.crear(":memory:")
    v1 = ctx.nueva_venta()
    v2 = ctx.nueva_venta()
    assert isinstance(v1, ServicioVenta)
    assert v1 is not v2
    ctx.conn.close()


def test_contexto_expone_formato_gs1_peso_por_defecto():
    ctx = ContextoApp.crear(":memory:")
    assert ctx.formato_gs1.valor_es_precio is False
    ctx.conn.close()


def test_contexto_autentica_admin_por_defecto():
    ctx = ContextoApp.crear(":memory:")
    nombre, password = ADMIN_POR_DEFECTO
    assert ctx.svc_usuarios.autenticar(nombre, password) is not None


def test_usuario_actual_id_none_por_defecto():
    ctx = ContextoApp.crear(":memory:")
    assert ctx.usuario_actual is None
    assert ctx.usuario_actual_id is None
