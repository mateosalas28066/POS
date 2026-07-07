"""Servicio de venta en caja. Python puro: arma líneas y totales vía puertos."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from core.calculos import (
    aplicar_descuento, impuesto_incluido, subtotal_por_peso, subtotal_por_unidad,
)
from core.entidades import (
    Devolucion, ItemDevolucion, LineaDevolucion, LineaVenta, MovimientoInventario,
    Pago, Producto, Venta,
)
from core.perifericos.gs1 import (
    FORMATO_PESO_DEFECTO, FormatoGS1, ResultadoGS1, decodificar_gs1, es_peso_variable,
)
from core.promociones import consumir_unidades, precio_con_promo, promo_vigente
from core.puertos import (
    RepositorioDevoluciones, RepositorioImpuestos, RepositorioInventario,
    RepositorioOutbox, RepositorioProductos, RepositorioPromociones, RepositorioVentas,
)

CERO = Decimal("0")


class ProductoNoEncontrado(ValueError):
    pass


class PesoRequerido(ValueError):
    pass


@dataclass
class _Entrada:
    producto_id: int
    descripcion: str
    cantidad_o_peso: Decimal
    precio_unit: Decimal
    subtotal_bruto: Decimal
    tarifa: Decimal
    promocion_id: int | None = None


class ServicioVenta:
    """Acumula líneas de una venta en curso y la confirma como `Venta`."""

    def __init__(self, productos: RepositorioProductos, impuestos: RepositorioImpuestos,
                 promociones: RepositorioPromociones | None = None) -> None:
        self._productos = productos
        self._impuestos = impuestos
        self._promociones = promociones
        self._entradas: list[_Entrada] = []
        self.descuento_pct: Decimal = CERO

    def establecer_descuento(self, pct: Decimal) -> None:
        if not (CERO <= pct < Decimal("1")):
            raise ValueError("descuento_pct debe estar en [0, 1)")
        self.descuento_pct = pct

    def _promo_para(self, producto: Producto, importe: Decimal | None,
                    ahora: datetime | None):
        if self._promociones is None or importe is not None:
            return None
        promo = self._promociones.activa_por_producto(producto.id)
        if promo is not None and promo_vigente(promo, ahora or datetime.now()):
            return promo
        return None

    def agregar(self, codigo_barras: str, *, cantidad: Decimal | int = 1,
                peso_kg: Decimal | None = None, importe: Decimal | None = None,
                ahora: datetime | None = None) -> LineaVenta:
        producto = self._productos.por_codigo(codigo_barras)
        if producto is None:
            raise ProductoNoEncontrado(f"producto inexistente: {codigo_barras!r}")
        tarifa = CERO
        if producto.impuesto_id is not None:
            impuesto = self._impuestos.por_id(producto.impuesto_id)
            if impuesto is not None:
                tarifa = impuesto.tarifa
        promo = self._promo_para(producto, importe, ahora)
        precio = precio_con_promo(producto.precio, promo) if promo is not None else producto.precio
        if producto.vendido_por_peso:
            if peso_kg is None:
                raise PesoRequerido(f"{producto.nombre} se vende por peso")
            cantidad_o_peso = peso_kg
            bruto = importe if importe is not None else subtotal_por_peso(precio, peso_kg)
        else:
            if importe is not None:
                raise ValueError(
                    f"{producto.nombre} se vende por unidad; importe no aplica")
            cantidad_o_peso = Decimal(cantidad)
            bruto = subtotal_por_unidad(precio, cantidad_o_peso)
        entrada = _Entrada(
            producto_id=producto.id, descripcion=producto.nombre,
            cantidad_o_peso=cantidad_o_peso, precio_unit=precio,
            subtotal_bruto=bruto, tarifa=tarifa,
            promocion_id=promo.id if promo is not None else None)
        self._entradas.append(entrada)
        return self._linea(entrada)

    def _linea(self, e: _Entrada) -> LineaVenta:
        subtotal = aplicar_descuento(e.subtotal_bruto, self.descuento_pct)
        return LineaVenta(
            producto_id=e.producto_id, descripcion=e.descripcion,
            cantidad_o_peso=e.cantidad_o_peso, precio_unit=e.precio_unit,
            impuesto=impuesto_incluido(subtotal, e.tarifa), subtotal=subtotal,
            promocion_id=e.promocion_id)

    def agregar_escaneado(self, codigo: str,
                          formato: FormatoGS1 = FORMATO_PESO_DEFECTO,
                          ahora: datetime | None = None) -> LineaVenta:
        """Agrega según un código escaneado: GS1 de peso variable o EAN/PLU normal."""
        if not es_peso_variable(codigo, formato):
            return self.agregar(codigo, cantidad=1, ahora=ahora)
        resultado = decodificar_gs1(codigo, formato)
        producto = self._productos.por_codigo(resultado.codigo_producto)
        if producto is None:
            raise ProductoNoEncontrado(
                f"producto inexistente: {resultado.codigo_producto!r} (código {codigo!r})")
        if not producto.vendido_por_peso:
            raise ValueError(
                f"{producto.nombre} no se vende por peso pero el código es de peso variable")
        peso, importe = peso_e_importe_gs1(resultado, producto, formato.valor_es_precio)
        return self.agregar(resultado.codigo_producto, peso_kg=peso, importe=importe, ahora=ahora)

    @property
    def lineas(self) -> tuple[LineaVenta, ...]:
        return tuple(self._linea(e) for e in self._entradas)

    @property
    def total(self) -> Decimal:
        return sum((l.subtotal for l in self.lineas), CERO)

    @property
    def total_impuestos(self) -> Decimal:
        return sum((l.impuesto for l in self.lineas), CERO)

    def confirmar(self, *, fecha: datetime, usuario_id: int | None = None,
                  caja_sesion_id: int | None = None, cliente_id: int | None = None) -> Venta:
        if not self._entradas:
            raise ValueError("no se puede confirmar una venta vacía")
        return Venta(
            fecha=fecha,
            lineas=self.lineas,
            total=self.total,
            total_impuestos=self.total_impuestos,
            usuario_id=usuario_id,
            caja_sesion_id=caja_sesion_id,
            cliente_id=cliente_id,
            descuento_pct=self.descuento_pct,
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
    def __init__(self, ventas: RepositorioVentas, inventario: RepositorioInventario,
                 promociones: RepositorioPromociones | None = None) -> None:
        self._ventas = ventas
        self._inventario = inventario
        self._promociones = promociones

    def registrar(self, venta: Venta, pagos: list[Pago]) -> Venta:
        guardada = self._ventas.guardar(venta, pagos)
        self._consumir_promos(guardada)
        for movimiento in salidas_de_venta(guardada):
            self._inventario.registrar(movimiento)
        return guardada

    def _consumir_promos(self, venta: Venta) -> None:
        if self._promociones is None:
            return
        pendiente: dict[int, Decimal] = defaultdict(lambda: CERO)
        for linea in venta.lineas:
            if linea.promocion_id is not None:
                pendiente[linea.promocion_id] += linea.cantidad_o_peso
        for promocion_id, cantidad in pendiente.items():
            promo = self._promociones.por_id(promocion_id)
            if promo is not None and promo.tipo_duracion == "unidades":
                self._promociones.actualizar(consumir_unidades(promo, cantidad))


class ServicioRegistroVentaConOutbox:
    """Decora ServicioRegistroVenta: registra y encola el evento para sync.

    core no conoce sync_pdv ni el transporte: el serializador
    (venta, pagos, almacen_id, local_id) -> evento se inyecta desde fuera.
    """

    def __init__(self, interno: ServicioRegistroVenta, outbox: RepositorioOutbox,
                 almacen_id: int, local_id: str, serializar) -> None:
        self._interno = interno
        self._outbox = outbox
        self._almacen_id = almacen_id
        self._local_id = local_id
        self._serializar = serializar

    def registrar(self, venta: Venta, pagos: list[Pago]) -> Venta:
        guardada = self._interno.registrar(venta, pagos)
        self._outbox.encolar(
            self._serializar(guardada, pagos, self._almacen_id, self._local_id))
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
