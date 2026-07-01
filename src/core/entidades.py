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


ESTADOS_VENTA = ("pagada", "anulada", "devuelta_parcial", "devuelta")


@dataclass(frozen=True)
class MedioPago:
    nombre: str
    id: int | None = None


ROLES = ("admin", "cajero")


@dataclass(frozen=True)
class Usuario:
    nombre: str
    rol: str = "cajero"
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.nombre.strip():
            raise ValueError("el nombre de usuario es obligatorio")
        if self.rol not in ROLES:
            raise ValueError(f"rol inválido: {self.rol!r}")


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

    def __post_init__(self) -> None:
        if self.subtotal < CERO or self.impuesto < CERO or self.precio_unit < CERO:
            raise ValueError("valores monetarios de LineaVenta deben ser no negativos")
        if self.cantidad_o_peso <= CERO:
            raise ValueError("cantidad_o_peso debe ser positiva")


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


ESTADOS_CAJA = ("abierta", "cerrada")


@dataclass(frozen=True)
class CajaSesion:
    apertura_fecha: datetime
    monto_inicial: Decimal
    usuario_id: int | None = None
    cierre_fecha: datetime | None = None
    monto_contado: Decimal | None = None
    estado: str = "abierta"
    id: int | None = None

    def __post_init__(self) -> None:
        if self.estado not in ESTADOS_CAJA:
            raise ValueError(f"estado de caja invalido: {self.estado!r}")
        if self.monto_inicial < CERO:
            raise ValueError("monto_inicial no puede ser negativo")
        if self.monto_contado is not None and self.monto_contado < CERO:
            raise ValueError("monto_contado no puede ser negativo")


@dataclass(frozen=True)
class Arqueo:
    monto_inicial: Decimal
    efectivo_ventas: Decimal
    esperado: Decimal
    contado: Decimal
    diferencia: Decimal


ESTADOS_DEVOLUCION = ("emitida",)


@dataclass(frozen=True)
class ItemDevolucion:
    """Input del cajero: qué línea y cuánto se devuelve. Lo demás lo deriva el dominio."""
    venta_linea_id: int
    cantidad_o_peso: Decimal

    def __post_init__(self) -> None:
        if self.cantidad_o_peso <= CERO:
            raise ValueError("cantidad_o_peso a devolver debe ser positiva")


@dataclass(frozen=True)
class LineaDevolucion:
    producto_id: int
    cantidad_o_peso: Decimal   # cuánto se devuelve de la línea (>0; unidad o kg)
    impuesto: Decimal          # IVA contenido devuelto (prorrateado)
    subtotal: Decimal          # dinero devuelto por esta línea (IVA incluido)
    venta_linea_id: int | None = None
    devolucion_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.subtotal < CERO or self.impuesto < CERO:
            raise ValueError("valores monetarios de LineaDevolucion deben ser no negativos")
        if self.cantidad_o_peso <= CERO:
            raise ValueError("cantidad_o_peso debe ser positiva")


@dataclass(frozen=True)
class Devolucion:
    venta_id: int
    fecha: datetime
    lineas: tuple[LineaDevolucion, ...]
    total: Decimal             # Σ subtotales devueltos = dinero a reembolsar
    total_impuestos: Decimal
    reembolsos: tuple[Pago, ...]   # salida de dinero por medio (reusa Pago; monto>0)
    caja_sesion_id: int | None = None   # sesión donde SALE el dinero (la abierta hoy)
    usuario_id: int | None = None
    estado: str = "emitida"
    id: int | None = None

    def __post_init__(self) -> None:
        if self.estado not in ESTADOS_DEVOLUCION:
            raise ValueError(f"estado de devolución inválido: {self.estado!r}")
