"""Entidades de dominio del inventario. Python puro: sin Qt, sin SQLite."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

CERO = Decimal("0")
TIPOS_MOVIMIENTO = ("entrada", "salida")


@dataclass(frozen=True)
class Categoria:
    nombre: str
    id: int | None = None


@dataclass(frozen=True)
class Impuesto:
    nombre: str
    tarifa: Decimal  # fracción: 0.19 = IVA 19%
    id: int | None = None
    codigo_dian: str | None = None  # reservado DIAN, sin uso fiscal hoy

    def __post_init__(self) -> None:
        if not (CERO <= self.tarifa <= Decimal("1")):
            raise ValueError("tarifa debe estar entre 0 y 1")


@dataclass(frozen=True)
class Producto:
    codigo_barras: str
    nombre: str
    precio: Decimal
    vendido_por_peso: bool = False
    unidad: str = "und"  # "und" o "kg"
    costo: Decimal = CERO
    categoria_id: int | None = None
    impuesto_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.precio < CERO:
            raise ValueError("precio no puede ser negativo")
        if self.costo < CERO:
            raise ValueError("costo no puede ser negativo")


@dataclass(frozen=True)
class MovimientoInventario:
    producto_id: int
    tipo: str  # "entrada" o "salida"; el signo del stock lo da el tipo
    cantidad: Decimal  # siempre positiva
    fecha: datetime
    ref: str | None = None
    lote_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.tipo not in TIPOS_MOVIMIENTO:
            raise ValueError(f"tipo inválido: {self.tipo!r}")
        if self.cantidad <= CERO:
            raise ValueError("cantidad debe ser positiva")


ESTADOS_VENTA = ("pagada", "anulada")


@dataclass(frozen=True)
class MedioPago:
    nombre: str
    id: int | None = None


@dataclass(frozen=True)
class Cliente:
    identificacion: str
    nombre: str
    contacto: str | None = None
    bloqueado_edicion: bool = False
    tipo_documento: str | None = None        # reservado DIAN
    regimen: str | None = None               # reservado DIAN
    tipo_responsabilidad: str | None = None  # reservado DIAN
    id: int | None = None


@dataclass(frozen=True)
class Pago:
    medio_pago_id: int
    monto: Decimal
    referencia: str | None = None
    venta_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.monto <= CERO:
            raise ValueError("monto del pago debe ser positivo")


@dataclass(frozen=True)
class LineaVenta:
    producto_id: int
    descripcion: str          # nombre del producto al momento de vender (snapshot para recibo)
    cantidad_o_peso: Decimal  # unidades (entero) o kg (decimal)
    precio_unit: Decimal      # precio al público, IVA incluido
    impuesto: Decimal         # IVA contenido en el subtotal
    subtotal: Decimal         # lo que paga el cliente por esta línea
    venta_id: int | None = None
    id: int | None = None


@dataclass(frozen=True)
class Venta:
    fecha: datetime
    lineas: tuple[LineaVenta, ...]
    total: Decimal            # Σ subtotales (IVA incluido)
    total_impuestos: Decimal  # Σ IVA contenido
    usuario_id: int | None = None
    caja_sesion_id: int | None = None
    cliente_id: int | None = None
    estado: str = "pagada"
    id: int | None = None

    def __post_init__(self) -> None:
        if self.estado not in ESTADOS_VENTA:
            raise ValueError(f"estado inválido: {self.estado!r}")
