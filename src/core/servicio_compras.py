"""Servicio de registro de compras. Python puro: persiste y alimenta inventario."""
from __future__ import annotations

from dataclasses import replace

from core.entidades import Compra, MovimientoInventario
from core.puertos import (
    RepositorioCompras, RepositorioInventario, RepositorioProductos,
)


class ServicioCompras:
    """Registra una compra: persiste, registra entradas de inventario y actualiza costo."""

    def __init__(self, compras: RepositorioCompras, inventario: RepositorioInventario,
                 productos: RepositorioProductos) -> None:
        self._compras = compras
        self._inventario = inventario
        self._productos = productos

    def registrar(self, compra: Compra) -> Compra:
        """Persiste la compra y, por cada línea: registra entrada de inventario y
        actualiza el costo del producto al costo_unit de la línea."""
        if not compra.lineas:
            raise ValueError("no se puede registrar una compra sin líneas")

        guardada = self._compras.guardar(compra)

        # Registrar entradas de inventario y actualizar costos
        for linea in guardada.lineas:
            # Registrar movimiento de entrada
            movimiento = MovimientoInventario(
                producto_id=linea.producto_id,
                tipo="entrada",
                cantidad=linea.cantidad,
                fecha=guardada.fecha,
                ref=f"compra:{guardada.id}",
            )
            self._inventario.registrar(movimiento)

            # Actualizar costo del producto
            producto = self._productos.por_id(linea.producto_id)
            if producto is not None:
                actualizado = replace(producto, costo=linea.costo_unit)
                self._productos.actualizar(actualizado)

        return guardada
