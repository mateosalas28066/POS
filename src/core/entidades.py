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
    descuento_pct: Decimal = CERO            # fracción 0..1
    id: int | None = None

    def __post_init__(self) -> None:
        if not (CERO <= self.descuento_pct < Decimal("1")):
            raise ValueError("descuento_pct debe estar en [0, 1)")


@dataclass(frozen=True)
class Proveedor:
    identificacion: str
    nombre: str
    contacto: str | None = None
    bloqueado_edicion: bool = False
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


ESTADOS_COMPRA = ("pagada", "credito")


@dataclass(frozen=True)
class LineaCompra:
    producto_id: int
    descripcion: str          # snapshot del nombre del producto al momento de comprar
    cantidad: Decimal         # unidades o kg, siempre positiva
    costo_unit: Decimal       # costo unitario de esta línea
    subtotal: Decimal         # cantidad * costo_unit
    compra_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.cantidad <= CERO:
            raise ValueError("cantidad debe ser positiva")
        if self.costo_unit < CERO or self.subtotal < CERO:
            raise ValueError("valores monetarios de LineaCompra deben ser no negativos")


@dataclass(frozen=True)
class Compra:
    proveedor_id: int
    fecha: datetime
    lineas: tuple[LineaCompra, ...]
    total: Decimal
    estado: str = "pagada"    # "pagada" | "credito"
    usuario_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.estado not in ESTADOS_COMPRA:
            raise ValueError(f"estado de compra inválido: {self.estado!r}")


@dataclass(frozen=True)
class LineaVenta:
    producto_id: int
    descripcion: str          # nombre del producto al momento de vender (snapshot para recibo)
    cantidad_o_peso: Decimal  # unidades (entero) o kg (decimal)
    precio_unit: Decimal      # precio al público, IVA incluido
    impuesto: Decimal         # IVA contenido en el subtotal
    subtotal: Decimal         # lo que paga el cliente por esta línea
    promocion_id: int | None = None
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
    descuento_pct: Decimal = CERO   # descuento aplicado a la venta (cliente o manual)
    id: int | None = None

    def __post_init__(self) -> None:
        if self.estado not in ESTADOS_VENTA:
            raise ValueError(f"estado inválido: {self.estado!r}")
        if not (CERO <= self.descuento_pct < Decimal("1")):
            raise ValueError("descuento_pct debe estar en [0, 1)")


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
    otros_ingresos: Decimal = CERO   # ingresos manuales de efectivo (base extra, etc.)
    otros_egresos: Decimal = CERO    # egresos manuales (retiros, pagos desde caja)


TIPOS_MOVIMIENTO_CAJA = ("ingreso", "egreso")


@dataclass(frozen=True)
class MovimientoCaja:
    """Ingreso/egreso manual de efectivo dentro de una sesión de caja."""
    caja_sesion_id: int
    tipo: str          # "ingreso" o "egreso"
    monto: Decimal     # siempre positivo; el signo lo da el tipo
    motivo: str
    fecha: datetime
    usuario_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.tipo not in TIPOS_MOVIMIENTO_CAJA:
            raise ValueError(f"tipo de movimiento inválido: {self.tipo!r}")
        if self.monto <= CERO:
            raise ValueError("monto debe ser positivo")
        if not self.motivo.strip():
            raise ValueError("el motivo es obligatorio")


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


@dataclass(frozen=True)
class LineaDespiece:
    producto_corte_id: int
    peso: Decimal              # kg despiezados de este corte, siempre positivo
    costo_asignado: Decimal    # porción del costo_canal asignada a este corte
    costo_unit: Decimal        # costo_asignado / peso
    despiece_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.peso <= CERO:
            raise ValueError("peso debe ser positivo")
        if self.costo_asignado < CERO or self.costo_unit < CERO:
            raise ValueError("valores monetarios de LineaDespiece deben ser no negativos")


@dataclass(frozen=True)
class Despiece:
    producto_canal_id: int
    peso_canal: Decimal        # kg del canal que se despiezan (entrada consumida)
    costo_canal: Decimal       # costo total a repartir entre los cortes
    fecha: datetime
    lineas: tuple[LineaDespiece, ...]
    usuario_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.peso_canal <= CERO:
            raise ValueError("peso_canal debe ser positivo")
        if self.costo_canal < CERO:
            raise ValueError("costo_canal no puede ser negativo")


TIPOS_VALOR_PROMO = ("precio_fijo", "porcentaje")
TIPOS_DURACION_PROMO = ("tiempo", "unidades", "manual")


@dataclass(frozen=True)
class Promocion:
    producto_id: int
    tipo_valor: str            # "precio_fijo" | "porcentaje"
    valor: Decimal             # pesos (fijo) o fracción [0,1) (porcentaje)
    tipo_duracion: str         # "tiempo" | "unidades" | "manual"
    activa: bool = True
    desde: datetime | None = None
    hasta: datetime | None = None
    unidades_limite: Decimal | None = None
    unidades_restantes: Decimal | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.tipo_valor not in TIPOS_VALOR_PROMO:
            raise ValueError(f"tipo_valor inválido: {self.tipo_valor!r}")
        if self.tipo_duracion not in TIPOS_DURACION_PROMO:
            raise ValueError(f"tipo_duracion inválido: {self.tipo_duracion!r}")
        if self.tipo_valor == "porcentaje" and not (CERO <= self.valor < Decimal("1")):
            raise ValueError("valor de porcentaje debe estar en [0, 1)")
        if self.tipo_valor == "precio_fijo" and self.valor < CERO:
            raise ValueError("precio fijo no puede ser negativo")
        if self.tipo_duracion == "tiempo":
            if self.desde is None or self.hasta is None:
                raise ValueError("promo por tiempo requiere desde y hasta")
            if self.desde > self.hasta:
                raise ValueError("desde no puede ser posterior a hasta")
        if self.tipo_duracion == "unidades":
            if self.unidades_limite is None or self.unidades_limite <= CERO:
                raise ValueError("promo por unidades requiere unidades_limite > 0")
            if self.unidades_restantes is None:
                object.__setattr__(self, "unidades_restantes", self.unidades_limite)


@dataclass(frozen=True)
class AbonoCliente:
    cliente_id: int
    monto: Decimal
    fecha: datetime
    medio_pago_id: int
    caja_sesion_id: int | None = None
    usuario_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.monto <= CERO:
            raise ValueError("el monto del abono debe ser positivo")


@dataclass(frozen=True)
class PagoProveedor:
    proveedor_id: int
    monto: Decimal
    fecha: datetime
    medio_pago_id: int
    caja_sesion_id: int | None = None
    usuario_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.monto <= CERO:
            raise ValueError("el monto del pago debe ser positivo")


@dataclass(frozen=True)
class CategoriaGasto:
    nombre: str
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.nombre.strip():
            raise ValueError("el nombre de la categoría es obligatorio")


@dataclass(frozen=True)
class Gasto:
    fecha: datetime
    categoria_gasto_id: int
    monto: Decimal
    descripcion: str | None = None
    medio_pago_id: int = 1
    caja_sesion_id: int | None = None
    usuario_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.monto <= CERO:
            raise ValueError("el monto del gasto debe ser positivo")
