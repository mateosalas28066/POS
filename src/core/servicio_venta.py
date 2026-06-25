"""Servicio de venta en caja. Python puro: arma líneas y totales vía puertos."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from core.calculos import impuesto_incluido, subtotal_por_peso, subtotal_por_unidad
from core.entidades import LineaVenta, Venta
from core.puertos import RepositorioImpuestos, RepositorioProductos

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
