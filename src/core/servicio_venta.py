"""Servicio de venta en caja. Python puro: arma líneas y totales vía puertos."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from core.calculos import impuesto_incluido, subtotal_por_peso, subtotal_por_unidad
from core.entidades import (
    Devolucion, ItemDevolucion, LineaDevolucion, LineaVenta, MovimientoInventario,
    Pago, Producto, Venta,
)
from core.perifericos.gs1 import (
    FORMATO_PESO_DEFECTO, FormatoGS1, ResultadoGS1, decodificar_gs1, es_peso_variable,
)
from core.puertos import (
    RepositorioDevoluciones, RepositorioImpuestos, RepositorioInventario,
    RepositorioProductos, RepositorioVentas,
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
                peso_kg: Decimal | None = None,
                importe: Decimal | None = None) -> LineaVenta:
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
            subtotal = (importe if importe is not None
                        else subtotal_por_peso(producto.precio, peso_kg))
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

    def agregar_escaneado(self, codigo: str,
                          formato: FormatoGS1 = FORMATO_PESO_DEFECTO) -> LineaVenta:
        """Agrega según un código escaneado: GS1 de peso variable o EAN/PLU normal."""
        if not es_peso_variable(codigo, formato):
            return self.agregar(codigo, cantidad=1)
        resultado = decodificar_gs1(codigo, formato)
        producto = self._productos.por_codigo(resultado.codigo_producto)
        if producto is None:
            raise ProductoNoEncontrado(
                f"producto inexistente: {resultado.codigo_producto!r} (código {codigo!r})")
        if not producto.vendido_por_peso:
            raise ValueError(
                f"{producto.nombre} no se vende por peso pero el código es de peso variable")
        peso, importe = peso_e_importe_gs1(resultado, producto, formato.valor_es_precio)
        return self.agregar(resultado.codigo_producto, peso_kg=peso, importe=importe)

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


_GRAMO = Decimal("0.001")  # granularidad de peso al derivarlo desde un precio embebido


def peso_e_importe_gs1(resultado: ResultadoGS1, producto: Producto,
                       valor_es_precio: bool) -> tuple[Decimal, Decimal | None]:
    """Traduce un ResultadoGS1 a (peso_kg, importe). importe=None salvo en modo precio."""
    if not valor_es_precio:
        return resultado.peso_kg, None
    if producto.precio <= CERO:
        raise ValueError(
            f"{producto.nombre} con precio 0: no se puede derivar peso de un código de precio")
    importe = Decimal(resultado.valor_crudo)
    peso = (importe / producto.precio).quantize(_GRAMO, rounding=ROUND_HALF_UP)
    return peso, importe


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


_PESO = Decimal("1")  # cuantización a peso colombiano entero


class LineaNoEncontrada(ValueError):
    pass


class CantidadDevueltaExcede(ValueError):
    pass


def _prorratear(valor: Decimal, ratio: Decimal) -> Decimal:
    return (valor * ratio).quantize(_PESO, rounding=ROUND_HALF_UP)


def construir_lineas_devolucion(
    venta: Venta, items: list[ItemDevolucion], ya_devuelto: dict[int, Decimal],
) -> list[LineaDevolucion]:
    """Valida cada item contra (vendido − ya_devuelto) y prorratea desde la línea original."""
    por_linea = {linea.id: linea for linea in venta.lineas}
    resultado: list[LineaDevolucion] = []
    for item in items:
        linea = por_linea.get(item.venta_linea_id)
        if linea is None:
            raise LineaNoEncontrada(
                f"la línea {item.venta_linea_id} no pertenece a la venta {venta.id}")
        remanente = linea.cantidad_o_peso - ya_devuelto.get(item.venta_linea_id, CERO)
        if item.cantidad_o_peso > remanente:
            raise CantidadDevueltaExcede(
                f"línea {item.venta_linea_id}: se devuelve {item.cantidad_o_peso} de {remanente}")
        ratio = item.cantidad_o_peso / linea.cantidad_o_peso
        resultado.append(LineaDevolucion(
            producto_id=linea.producto_id,
            cantidad_o_peso=item.cantidad_o_peso,
            impuesto=_prorratear(linea.impuesto, ratio),
            subtotal=_prorratear(linea.subtotal, ratio),
            venta_linea_id=linea.id,
        ))
    return resultado


def entradas_de_devolucion(dev: Devolucion) -> list[MovimientoInventario]:
    return [
        MovimientoInventario(
            producto_id=linea.producto_id,
            tipo="entrada",
            cantidad=linea.cantidad_o_peso,
            fecha=dev.fecha,
            ref=f"devolucion:{dev.id}",
        )
        for linea in dev.lineas
    ]


def _todo_devuelto(venta: Venta, ya_devuelto: dict[int, Decimal],
                   lineas_dev: list[LineaDevolucion]) -> bool:
    acumulado = dict(ya_devuelto)
    for linea in lineas_dev:
        acumulado[linea.venta_linea_id] = (
            acumulado.get(linea.venta_linea_id, CERO) + linea.cantidad_o_peso)
    return all(acumulado.get(linea.id, CERO) == linea.cantidad_o_peso for linea in venta.lineas)


class VentaNoDevolvible(ValueError):
    pass


class ReembolsoDescuadrado(ValueError):
    pass


class ServicioDevolucion:
    """Devuelve líneas de una venta: repone inventario y reembolsa dinero. Solo puertos."""

    def __init__(self, ventas: RepositorioVentas, devoluciones: RepositorioDevoluciones,
                 inventario: RepositorioInventario) -> None:
        self._ventas = ventas
        self._devoluciones = devoluciones
        self._inventario = inventario

    def devolver(self, venta_id: int, items: list[ItemDevolucion], reembolsos: list[Pago], *,
                 fecha: datetime, caja_sesion_id: int | None = None,
                 usuario_id: int | None = None) -> Devolucion:
        venta = self._ventas.por_id(venta_id)
        if venta is None:
            raise VentaNoEncontrada(f"venta inexistente: {venta_id}")
        if venta.estado in ("anulada", "devuelta"):
            raise VentaNoDevolvible(f"venta {venta_id} en estado {venta.estado!r}")
        ya_devuelto = self._devoluciones.devuelto_por_linea(venta_id)
        lineas = construir_lineas_devolucion(venta, items, ya_devuelto)
        total = sum((l.subtotal for l in lineas), CERO)
        total_impuestos = sum((l.impuesto for l in lineas), CERO)
        if sum((r.monto for r in reembolsos), CERO) != total:
            raise ReembolsoDescuadrado(
                f"reembolso {sum((r.monto for r in reembolsos), CERO)} ≠ devuelto {total}")
        dev = Devolucion(
            venta_id=venta_id, fecha=fecha, lineas=tuple(lineas),
            total=total, total_impuestos=total_impuestos, reembolsos=tuple(reembolsos),
            caja_sesion_id=caja_sesion_id, usuario_id=usuario_id)
        guardada = self._devoluciones.guardar(dev)
        for movimiento in entradas_de_devolucion(guardada):
            self._inventario.registrar(movimiento)
        nuevo_estado = "devuelta" if _todo_devuelto(venta, ya_devuelto, lineas) else "devuelta_parcial"
        self._ventas.marcar_estado(venta_id, nuevo_estado)
        return guardada
