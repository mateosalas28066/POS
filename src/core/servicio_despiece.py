"""Servicio de despiece (carnicería): reparte el costo del canal entre los cortes
resultantes por valor de venta (fallback a peso si falta precio). Python puro."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from core.entidades import Despiece, LineaDespiece, MovimientoInventario
from core.puertos import RepositorioDespieces, RepositorioInventario, RepositorioProductos

CERO = Decimal("0")


class StockCanalInsuficiente(ValueError):
    pass


def prorratear_costeo_despiece(
    costo_canal: Decimal,
    cortes: list[tuple[int, Decimal, Decimal]],  # (producto_corte_id, peso, precio_venta)
) -> list[LineaDespiece]:
    """Reparte costo_canal entre los cortes. Por valor de venta si todos tienen precio > 0;
    si alguno no, cae a prorrateo por peso para todos (decisión 2, ver global-context.md)."""
    if not cortes:
        raise ValueError("no se puede prorratear un despiece sin cortes")

    por_valor = all(precio > CERO for _, _, precio in cortes)

    if por_valor:
        bases = [peso * precio for _, peso, precio in cortes]
    else:
        bases = [peso for _, peso, _ in cortes]

    total_base = sum(bases, CERO)

    lineas: list[LineaDespiece] = []
    for (producto_corte_id, peso, _precio), base in zip(cortes, bases):
        costo_asignado = costo_canal * (base / total_base)
        costo_unit = costo_asignado / peso
        lineas.append(LineaDespiece(
            producto_corte_id=producto_corte_id,
            peso=peso,
            costo_asignado=costo_asignado,
            costo_unit=costo_unit,
        ))
    return lineas


class ServicioDespiece:
    """Registra un despiece: valida stock del canal, calcula el costeo, persiste,
    registra movimientos de inventario y actualiza el costo de cada producto-corte."""

    def __init__(self, despieces: RepositorioDespieces, inventario: RepositorioInventario,
                 productos: RepositorioProductos) -> None:
        self._despieces = despieces
        self._inventario = inventario
        self._productos = productos

    def registrar(self, *, producto_canal_id: int, peso_canal: Decimal, costo_canal: Decimal,
                  cortes: list[tuple[int, Decimal]],  # (producto_corte_id, peso)
                  fecha: datetime, usuario_id: int | None = None) -> Despiece:
        """Valida stock suficiente del canal, calcula el costeo, persiste, y registra
        los movimientos de inventario (salida canal + entrada por cada corte), y actualiza
        el costo de cada producto-corte."""
        if self._inventario.stock_de(producto_canal_id) < peso_canal:
            raise StockCanalInsuficiente(
                f"stock insuficiente del canal {producto_canal_id} para despiezar {peso_canal}kg"
            )

        cortes_con_precio = []
        for producto_corte_id, peso in cortes:
            producto = self._productos.por_id(producto_corte_id)
            precio = producto.precio if producto is not None else CERO
            cortes_con_precio.append((producto_corte_id, peso, precio))

        lineas = prorratear_costeo_despiece(costo_canal, cortes_con_precio)

        despiece = Despiece(
            producto_canal_id=producto_canal_id,
            peso_canal=peso_canal,
            costo_canal=costo_canal,
            fecha=fecha,
            lineas=tuple(lineas),
            usuario_id=usuario_id,
        )
        guardado = self._despieces.guardar(despiece)

        self._inventario.registrar(MovimientoInventario(
            producto_id=producto_canal_id,
            tipo="salida",
            cantidad=peso_canal,
            fecha=fecha,
            ref=f"despiece:{guardado.id}",
        ))

        for linea in guardado.lineas:
            self._inventario.registrar(MovimientoInventario(
                producto_id=linea.producto_corte_id,
                tipo="entrada",
                cantidad=linea.peso,
                fecha=fecha,
                ref=f"despiece:{guardado.id}",
            ))
            producto = self._productos.por_id(linea.producto_corte_id)
            if producto is not None:
                self._productos.actualizar(replace(producto, costo=linea.costo_unit))

        return guardado
