"""Servicio de venta en caja. Python puro: arma líneas y totales vía puertos."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from core.calculos import impuesto_incluido, subtotal_por_peso, subtotal_por_unidad
from core.entidades import LineaVenta, MovimientoInventario, Pago, Venta
from core.puertos import (
    RepositorioImpuestos, RepositorioInventario, RepositorioProductos, RepositorioVentas,
)

CERO = Decimal("0")


class ProductoNoEncontrado(ValueError):
    pass


class PesoRequerido(ValueError):
    pass


class ServicioVenta:
    """Acumula líneas de una venta en curso y la confirma como `Venta`."""

    def __init__(self, productos: RepositorioProductos, impuestos: RepositorioImpuestos) -> None:
        self._productos = productos
        self._impuestos = impuestos
        self._lineas: list[LineaVenta] = []

    def agregar(self, codigo_barras: str, *, cantidad: Decimal | int = 1,
                peso_kg: Decimal | None = None) -> LineaVenta:
        producto = self._productos.por_codigo(codigo_barras)
        if producto is None:
            raise ProductoNoEncontrado(f"producto inexistente: {codigo_barras!r}")
        tarifa = CERO
        if producto.impuesto_id is not None:
            impuesto = self._impuestos.por_id(producto.impuesto_id)
            if impuesto is not None:
                tarifa = impuesto.tarifa
        if producto.vendido_por_peso:
            if peso_kg is None:
                raise PesoRequerido(f"{producto.nombre} se vende por peso")
            cantidad_o_peso = peso_kg
            subtotal = subtotal_por_peso(producto.precio, peso_kg)
        else:
            cantidad_o_peso = Decimal(cantidad)
            subtotal = subtotal_por_unidad(producto.precio, cantidad_o_peso)
        linea = LineaVenta(
            producto_id=producto.id,
            descripcion=producto.nombre,
            cantidad_o_peso=cantidad_o_peso,
            precio_unit=producto.precio,
            impuesto=impuesto_incluido(subtotal, tarifa),
            subtotal=subtotal,
        )
        self._lineas.append(linea)
        return linea

    @property
    def lineas(self) -> tuple[LineaVenta, ...]:
        return tuple(self._lineas)

    @property
    def total(self) -> Decimal:
        return sum((l.subtotal for l in self._lineas), CERO)

    @property
    def total_impuestos(self) -> Decimal:
        return sum((l.impuesto for l in self._lineas), CERO)

    def confirmar(self, *, fecha: datetime, usuario_id: int | None = None,
                  caja_sesion_id: int | None = None, cliente_id: int | None = None) -> Venta:
        if not self._lineas:
            raise ValueError("no se puede confirmar una venta vacía")
        return Venta(
            fecha=fecha,
            lineas=self.lineas,
            total=self.total,
            total_impuestos=self.total_impuestos,
            usuario_id=usuario_id,
            caja_sesion_id=caja_sesion_id,
            cliente_id=cliente_id,
            estado="pagada",
        )


def salidas_de_venta(venta: Venta) -> list[MovimientoInventario]:
    return [
        MovimientoInventario(
            producto_id=linea.producto_id,
            tipo="salida",
            cantidad=linea.cantidad_o_peso,
            fecha=venta.fecha,
            ref=f"venta:{venta.id}",
        )
        for linea in venta.lineas
    ]


def entradas_de_anulacion(venta: Venta) -> list[MovimientoInventario]:
    return [
        MovimientoInventario(
            producto_id=linea.producto_id,
            tipo="entrada",
            cantidad=linea.cantidad_o_peso,
            fecha=venta.fecha,
            ref=f"anulacion:{venta.id}",
        )
        for linea in venta.lineas
    ]


class ServicioRegistroVenta:
    def __init__(self, ventas: RepositorioVentas, inventario: RepositorioInventario) -> None:
        self._ventas = ventas
        self._inventario = inventario

    def registrar(self, venta: Venta, pagos: list[Pago]) -> Venta:
        guardada = self._ventas.guardar(venta, pagos)
        for movimiento in salidas_de_venta(guardada):
            self._inventario.registrar(movimiento)
        return guardada


class VentaNoEncontrada(ValueError):
    pass


class VentaYaAnulada(ValueError):
    pass


class ServicioAnulacion:
    """Reversa una venta: repone inventario y la marca 'anulada'. No mueve dinero."""

    def __init__(self, ventas: RepositorioVentas, inventario: RepositorioInventario) -> None:
        self._ventas = ventas
        self._inventario = inventario

    def anular(self, venta_id: int) -> Venta:
        venta = self._ventas.por_id(venta_id)
        if venta is None:
            raise VentaNoEncontrada(f"venta inexistente: {venta_id}")
        if venta.estado == "anulada":
            raise VentaYaAnulada(f"venta {venta_id} ya estaba anulada")
        self._ventas.anular(venta_id)
        for movimiento in entradas_de_anulacion(venta):
            self._inventario.registrar(movimiento)
        return replace(venta, estado="anulada")
