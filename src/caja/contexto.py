"""Composition root: construye repos y servicios sobre una conexión SQLite."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from caja.bootstrap import preparar_db
from core.perifericos.gs1 import FORMATO_PESO_DEFECTO, FormatoGS1
from core.servicio_caja import ServicioCaja
from core.servicio_clientes import ServicioClientes
from core.servicio_reportes import ServicioReportes
from core.servicio_venta import (
    ServicioAnulacion, ServicioDevolucion, ServicioRegistroVenta, ServicioVenta,
)
from inventario.repositorio_sqlite import (
    RepositorioCategoriasSQLite, RepositorioImpuestosSQLite,
    RepositorioInventarioSQLite, RepositorioProductosSQLite,
)
from ventas.repositorio_sqlite import (
    RepositorioCajaSesionesSQLite, RepositorioClientesSQLite,
    RepositorioDevolucionesSQLite, RepositorioMediosPagoSQLite, RepositorioVentasSQLite,
)

EFECTIVO_MEDIO_PAGO_ID = 1


@dataclass
class ContextoApp:
    conn: sqlite3.Connection
    repo_productos: RepositorioProductosSQLite
    repo_categorias: RepositorioCategoriasSQLite
    repo_impuestos: RepositorioImpuestosSQLite
    repo_inventario: RepositorioInventarioSQLite
    repo_clientes: RepositorioClientesSQLite
    repo_medios_pago: RepositorioMediosPagoSQLite
    repo_ventas: RepositorioVentasSQLite
    repo_sesiones: RepositorioCajaSesionesSQLite
    repo_devoluciones: RepositorioDevolucionesSQLite
    svc_registro: ServicioRegistroVenta
    svc_anulacion: ServicioAnulacion
    svc_clientes: ServicioClientes
    svc_caja: ServicioCaja
    svc_devolucion: ServicioDevolucion
    svc_reportes: ServicioReportes
    formato_gs1: FormatoGS1 = FORMATO_PESO_DEFECTO

    @classmethod
    def desde_conn(cls, conn: sqlite3.Connection) -> "ContextoApp":
        productos = RepositorioProductosSQLite(conn)
        categorias = RepositorioCategoriasSQLite(conn)
        impuestos = RepositorioImpuestosSQLite(conn)
        inventario = RepositorioInventarioSQLite(conn)
        clientes = RepositorioClientesSQLite(conn)
        medios = RepositorioMediosPagoSQLite(conn)
        ventas = RepositorioVentasSQLite(conn)
        sesiones = RepositorioCajaSesionesSQLite(conn)
        devoluciones = RepositorioDevolucionesSQLite(conn)
        return cls(
            conn=conn,
            repo_productos=productos, repo_categorias=categorias, repo_impuestos=impuestos,
            repo_inventario=inventario, repo_clientes=clientes, repo_medios_pago=medios,
            repo_ventas=ventas, repo_sesiones=sesiones, repo_devoluciones=devoluciones,
            svc_registro=ServicioRegistroVenta(ventas, inventario),
            svc_anulacion=ServicioAnulacion(ventas, inventario),
            svc_clientes=ServicioClientes(clientes),
            svc_caja=ServicioCaja(sesiones, ventas, EFECTIVO_MEDIO_PAGO_ID),
            svc_devolucion=ServicioDevolucion(ventas, devoluciones, inventario),
            svc_reportes=ServicioReportes(ventas, devoluciones, inventario, sesiones,
                                          EFECTIVO_MEDIO_PAGO_ID),
        )

    @classmethod
    def crear(cls, ruta_db: str = "pos.db") -> "ContextoApp":
        return cls.desde_conn(preparar_db(ruta_db))

    def nueva_venta(self) -> ServicioVenta:
        return ServicioVenta(self.repo_productos, self.repo_impuestos)
