"""Puertos (interfaces) del dominio. Implementados por adaptadores fuera de core."""
from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from core.entidades import Categoria, Impuesto, MovimientoInventario, Producto


class RepositorioCategorias(Protocol):
    def guardar(self, categoria: Categoria) -> Categoria: ...


class RepositorioImpuestos(Protocol):
    def guardar(self, impuesto: Impuesto) -> Impuesto: ...


class RepositorioProductos(Protocol):
    def guardar(self, producto: Producto) -> Producto: ...
    def por_id(self, id: int) -> Producto | None: ...
    def por_codigo(self, codigo_barras: str) -> Producto | None: ...
    def listar(self) -> list[Producto]: ...


class RepositorioInventario(Protocol):
    def registrar(self, movimiento: MovimientoInventario) -> MovimientoInventario: ...
    def stock_de(self, producto_id: int) -> Decimal: ...
