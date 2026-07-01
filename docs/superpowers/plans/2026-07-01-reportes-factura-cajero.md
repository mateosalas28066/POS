# Reportes por factura y por cajero — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir a `ServicioReportes` el desglose por factura y por cajero (rango y sesión) y exponerlo en dos pestañas nuevas de `PantallaReportes`.

**Architecture:** Agregación de solo lectura en `core` sobre los puertos existentes (`ventas_en`, `pagos_en`, `devoluciones_en`, `ventas_de_sesion`, `de_sesion`, `pagos_de`). La UI Qt solo formatea y resuelve nombres vía repos. Sin métodos de repositorio nuevos, sin SQL nueva, sin cambios de esquema.

**Tech Stack:** Python 3.11, PySide6 (Qt6), pytest. Dinero en `Decimal`.

**Spec:** [../specs/2026-07-01-reportes-factura-cajero-design.md](../specs/2026-07-01-reportes-factura-cajero-design.md)

## Global Constraints

- `src/core/` NO conoce Qt ni SQLite; SQL solo en adaptadores de repositorio.
- Sin dependencias nuevas (solo stdlib + PySide6 ya presentes).
- Sin métodos de repositorio nuevos ni SQL nueva ni cambios de esquema.
- Dinero siempre en `Decimal`.
- `usuario_id = None` se agrupa como cajero "Sin cajero" (etiqueta de UI), ordenado al final.
- Devoluciones atribuidas al cajero que las procesó (`Devolucion.usuario_id`).
- `neto = total − total_devoluciones`.
- **IDs de task con prefijo `RPTFAC`** (convención `planes-pos`); en tracking usar el ID completo (`RPTFAC.1 — …`), nunca el número suelto.
- Orden TDD: test primero. Suite base: **259 passed** (`python -m pytest -q`).

---

## Estructura de archivos

- `src/core/servicio_reportes.py` (Modify) — nuevo dataclass `ReporteCajero`; métodos `por_cajero`, `por_cajero_de_sesion`, `facturas`; helper privado `_por_cajero`.
- `src/caja/pantalla_reportes.py` (Modify) — pestañas "Por factura" y "Por cajero".
- `tests/core/test_reportes_por_cajero.py` (Create) — RPTFAC.1 y RPTFAC.2.
- `tests/core/test_reportes_facturas.py` (Create) — RPTFAC.3.
- `tests/caja/test_pantalla_reportes_factura.py` (Create) — RPTFAC.4.
- `tests/caja/test_pantalla_reportes_cajero.py` (Create) — RPTFAC.5.

---

### Task RPTFAC.1: `ReporteCajero` + `por_cajero(desde, hasta)` en core/servicio_reportes

**Files:**
- Modify: `src/core/servicio_reportes.py`
- Test: `tests/core/test_reportes_por_cajero.py`

**Interfaces:**
- Consumes: `RepositorioVentas.ventas_en(desde, hasta) -> list[Venta]`, `RepositorioVentas.pagos_en(desde, hasta) -> list[Pago]` (cada `Pago` con `.venta_id`), `RepositorioDevoluciones.devoluciones_en(desde, hasta) -> list[Devolucion]` (cada `Devolucion` con `.usuario_id`, `.total`, `.reembolsos`).
- Produces:
  - `ReporteCajero(usuario_id: int|None, num_ventas: int, total: Decimal, total_impuestos: Decimal, total_devoluciones: Decimal, neto: Decimal, por_medio: dict[int, Decimal])`
  - `ServicioReportes.por_cajero(desde: datetime, hasta: datetime) -> tuple[ReporteCajero, ...]` (orden: `usuario_id` asc, `None` al final)
  - Helper privado `ServicioReportes._por_cajero(vs, pagos, devs) -> tuple[ReporteCajero, ...]` donde `pagos` es `list[tuple[int|None, Pago]]`.

- [ ] **Step 1: Write the failing test**

Create `tests/core/test_reportes_por_cajero.py`:

```python
from datetime import datetime
from decimal import Decimal

import pytest

from core.entidades import CajaSesion, Devolucion, LineaDevolucion, LineaVenta, Pago, Venta
from core.servicio_reportes import ReporteCajero, ServicioReportes, SesionNoEncontrada

DESDE = datetime(2026, 6, 25, 0, 0)
HASTA = datetime(2026, 6, 26, 0, 0)


def _venta(id, usuario_id, total, impuestos=Decimal("0"), estado="pagada"):
    linea = LineaVenta(producto_id=1, descripcion="X", cantidad_o_peso=Decimal("1"),
                       precio_unit=total, impuesto=impuestos, subtotal=total, venta_id=id, id=id)
    return Venta(fecha=datetime(2026, 6, 25, 10, 0), lineas=(linea,), total=total,
                 total_impuestos=impuestos, usuario_id=usuario_id, estado=estado, id=id)


def _dev(usuario_id, total, reembolsos=()):
    return Devolucion(
        venta_id=1, fecha=datetime(2026, 6, 25, 12, 0),
        lineas=(LineaDevolucion(producto_id=1, cantidad_o_peso=Decimal("1"),
                                impuesto=Decimal("0"), subtotal=total, venta_linea_id=1),),
        total=total, total_impuestos=Decimal("0"), reembolsos=reembolsos, usuario_id=usuario_id)


class _FakeVentas:
    def __init__(self, ventas, pagos, pagos_por_venta=None):
        self._ventas = ventas
        self._pagos = pagos
        self._ppv = pagos_por_venta or {}
    def ventas_en(self, desde, hasta):
        return list(self._ventas)
    def pagos_en(self, desde, hasta):
        return list(self._pagos)
    def ventas_de_sesion(self, sesion_id):
        return list(self._ventas)
    def pagos_de(self, venta_id):
        return list(self._ppv.get(venta_id, []))


class _FakeDevoluciones:
    def __init__(self, devs):
        self._devs = devs
    def devoluciones_en(self, desde, hasta):
        return list(self._devs)
    def de_sesion(self, sesion_id):
        return list(self._devs)


class _FakeSesiones:
    def __init__(self, sesion):
        self._sesion = sesion
    def por_id(self, id):
        return self._sesion if self._sesion and self._sesion.id == id else None


def test_por_cajero_agrupa_totales_devoluciones_y_por_medio():
    ventas = [_venta(1, 10, Decimal("7000"), Decimal("1118")),
              _venta(2, 10, Decimal("5000")),
              _venta(3, 20, Decimal("3000"))]
    pagos = [Pago(medio_pago_id=1, monto=Decimal("7000"), venta_id=1),
             Pago(medio_pago_id=2, monto=Decimal("5000"), venta_id=2),
             Pago(medio_pago_id=1, monto=Decimal("3000"), venta_id=3)]
    devs = [_dev(10, Decimal("2000"), (Pago(medio_pago_id=1, monto=Decimal("2000")),))]
    svc = ServicioReportes(_FakeVentas(ventas, pagos), _FakeDevoluciones(devs),
                           None, _FakeSesiones(None))
    por = {c.usuario_id: c for c in svc.por_cajero(DESDE, HASTA)}
    assert por[10].num_ventas == 2
    assert por[10].total == Decimal("12000")
    assert por[10].total_impuestos == Decimal("1118")
    assert por[10].total_devoluciones == Decimal("2000")
    assert por[10].neto == Decimal("10000")                       # 12000 - 2000
    assert por[10].por_medio == {1: Decimal("5000"), 2: Decimal("5000")}  # medio1: 7000-2000
    assert por[20].num_ventas == 1
    assert por[20].total == Decimal("3000")
    assert por[20].por_medio == {1: Decimal("3000")}


def test_por_cajero_usuario_nulo_va_al_final():
    ventas = [_venta(1, None, Decimal("1000")), _venta(2, 5, Decimal("2000"))]
    svc = ServicioReportes(_FakeVentas(ventas, []), _FakeDevoluciones([]),
                           None, _FakeSesiones(None))
    assert [c.usuario_id for c in svc.por_cajero(DESDE, HASTA)] == [5, None]


def test_por_cajero_ignora_pago_de_venta_fuera_del_conjunto():
    ventas = [_venta(1, 10, Decimal("7000"))]
    pagos = [Pago(medio_pago_id=1, monto=Decimal("7000"), venta_id=1),
             Pago(medio_pago_id=1, monto=Decimal("9999"), venta_id=99)]  # huérfano
    svc = ServicioReportes(_FakeVentas(ventas, pagos), _FakeDevoluciones([]),
                           None, _FakeSesiones(None))
    por = {c.usuario_id: c for c in svc.por_cajero(DESDE, HASTA)}
    assert por[10].por_medio == {1: Decimal("7000")}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/test_reportes_por_cajero.py -v`
Expected: FAIL con `ImportError: cannot import name 'ReporteCajero'`.

- [ ] **Step 3: Write minimal implementation**

En `src/core/servicio_reportes.py`, añadir el dataclass tras `ReporteVentas` (junto a los demás `@dataclass`):

```python
@dataclass(frozen=True)
class ReporteCajero:
    usuario_id: int | None
    num_ventas: int
    total: Decimal
    total_impuestos: Decimal
    total_devoluciones: Decimal
    neto: Decimal
    por_medio: dict[int, Decimal]
```

Y añadir a la clase `ServicioReportes` el método público y el helper privado:

```python
    def por_cajero(self, desde: datetime, hasta: datetime) -> tuple[ReporteCajero, ...]:
        vs = self._ventas.ventas_en(desde, hasta)
        usuario_de_venta = {v.id: v.usuario_id for v in vs}
        pagos = [(usuario_de_venta[p.venta_id], p)
                 for p in self._ventas.pagos_en(desde, hasta)
                 if p.venta_id in usuario_de_venta]
        devs = self._devoluciones.devoluciones_en(desde, hasta)
        return self._por_cajero(vs, pagos, devs)

    def _por_cajero(self, vs, pagos, devs) -> tuple[ReporteCajero, ...]:
        agg: dict[int | None, dict] = {}

        def bucket(uid: int | None) -> dict:
            return agg.setdefault(
                uid, {"num": 0, "total": CERO, "imp": CERO, "dev": CERO, "medio": {}})

        for v in vs:
            b = bucket(v.usuario_id)
            b["num"] += 1
            b["total"] += v.total
            b["imp"] += v.total_impuestos
        for uid, p in pagos:
            m = bucket(uid)["medio"]
            m[p.medio_pago_id] = m.get(p.medio_pago_id, CERO) + p.monto
        for d in devs:
            b = bucket(d.usuario_id)
            b["dev"] += d.total
            for r in d.reembolsos:
                m = b["medio"]
                m[r.medio_pago_id] = m.get(r.medio_pago_id, CERO) - r.monto
        reportes = [
            ReporteCajero(usuario_id=uid, num_ventas=b["num"], total=b["total"],
                          total_impuestos=b["imp"], total_devoluciones=b["dev"],
                          neto=b["total"] - b["dev"], por_medio=b["medio"])
            for uid, b in agg.items()]
        return tuple(sorted(reportes,
                            key=lambda r: (r.usuario_id is None, r.usuario_id or 0)))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/core/test_reportes_por_cajero.py -v`
Expected: PASS (3 tests). El test de sesión de RPTFAC.2 aún no existe.

- [ ] **Step 5: Commit**

```bash
git add src/core/servicio_reportes.py tests/core/test_reportes_por_cajero.py
git commit -m "feat(reportes): ReporteCajero + por_cajero por rango (RPTFAC.1)"
```

---

### Task RPTFAC.2: `por_cajero_de_sesion(sesion_id)` en core/servicio_reportes

**Files:**
- Modify: `src/core/servicio_reportes.py`
- Test: `tests/core/test_reportes_por_cajero.py` (añade tests al archivo de RPTFAC.1)

**Interfaces:**
- Consumes: `RepositorioCajaSesiones.por_id(id) -> CajaSesion|None`, `RepositorioVentas.ventas_de_sesion(sesion_id) -> list[Venta]`, `RepositorioVentas.pagos_de(venta_id) -> list[Pago]`, `RepositorioDevoluciones.de_sesion(sesion_id) -> list[Devolucion]`, helper `_por_cajero` (RPTFAC.1), excepción `SesionNoEncontrada` (ya existe).
- Produces: `ServicioReportes.por_cajero_de_sesion(sesion_id: int) -> tuple[ReporteCajero, ...]`.

- [ ] **Step 1: Write the failing test**

Añadir al final de `tests/core/test_reportes_por_cajero.py`:

```python
def test_por_cajero_de_sesion_usa_pagos_de_por_venta():
    sesion = CajaSesion(apertura_fecha=datetime(2026, 6, 25, 9, 0),
                        monto_inicial=Decimal("0"), estado="abierta", id=7)
    ventas = [_venta(1, 10, Decimal("7000")), _venta(2, 20, Decimal("5000"))]
    ppv = {1: [Pago(medio_pago_id=1, monto=Decimal("7000"), venta_id=1)],
           2: [Pago(medio_pago_id=2, monto=Decimal("5000"), venta_id=2)]}
    svc = ServicioReportes(_FakeVentas(ventas, [], pagos_por_venta=ppv),
                           _FakeDevoluciones([]), None, _FakeSesiones(sesion))
    por = {c.usuario_id: c for c in svc.por_cajero_de_sesion(7)}
    assert por[10].num_ventas == 1
    assert por[10].por_medio == {1: Decimal("7000")}
    assert por[20].por_medio == {2: Decimal("5000")}


def test_por_cajero_de_sesion_inexistente_falla():
    svc = ServicioReportes(_FakeVentas([], []), _FakeDevoluciones([]),
                           None, _FakeSesiones(None))
    with pytest.raises(SesionNoEncontrada):
        svc.por_cajero_de_sesion(999)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/test_reportes_por_cajero.py::test_por_cajero_de_sesion_usa_pagos_de_por_venta -v`
Expected: FAIL con `AttributeError: 'ServicioReportes' object has no attribute 'por_cajero_de_sesion'`.

- [ ] **Step 3: Write minimal implementation**

En `src/core/servicio_reportes.py`, añadir a `ServicioReportes` (tras `por_cajero`):

```python
    def por_cajero_de_sesion(self, sesion_id: int) -> tuple[ReporteCajero, ...]:
        if self._sesiones.por_id(sesion_id) is None:
            raise SesionNoEncontrada(f"sesion de caja inexistente: {sesion_id}")
        vs = self._ventas.ventas_de_sesion(sesion_id)
        pagos = [(v.usuario_id, p) for v in vs for p in self._ventas.pagos_de(v.id)]
        devs = self._devoluciones.de_sesion(sesion_id)
        return self._por_cajero(vs, pagos, devs)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/core/test_reportes_por_cajero.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add src/core/servicio_reportes.py tests/core/test_reportes_por_cajero.py
git commit -m "feat(reportes): por_cajero_de_sesion (RPTFAC.2)"
```

---

### Task RPTFAC.3: `facturas(desde, hasta)` en core/servicio_reportes

**Files:**
- Modify: `src/core/servicio_reportes.py`
- Test: `tests/core/test_reportes_facturas.py`

**Interfaces:**
- Consumes: `RepositorioVentas.ventas_en(desde, hasta) -> list[Venta]` (ya excluye anuladas).
- Produces: `ServicioReportes.facturas(desde: datetime, hasta: datetime) -> tuple[Venta, ...]`, ordenado por `(fecha, id)`.

- [ ] **Step 1: Write the failing test**

Create `tests/core/test_reportes_facturas.py`:

```python
from datetime import datetime
from decimal import Decimal

from core.entidades import LineaVenta, Venta
from core.servicio_reportes import ServicioReportes

DESDE = datetime(2026, 6, 25, 0, 0)
HASTA = datetime(2026, 6, 26, 0, 0)


def _venta(id, hora, estado="pagada"):
    total = Decimal("1000")
    linea = LineaVenta(producto_id=1, descripcion="X", cantidad_o_peso=Decimal("1"),
                       precio_unit=total, impuesto=Decimal("0"), subtotal=total,
                       venta_id=id, id=id)
    return Venta(fecha=datetime(2026, 6, 25, hora, 0), lineas=(linea,), total=total,
                 total_impuestos=Decimal("0"), estado=estado, id=id)


class _FakeVentas:
    def __init__(self, ventas):
        self._ventas = ventas
    def ventas_en(self, desde, hasta):
        return list(self._ventas)


class _FakeDevoluciones:
    def devoluciones_en(self, desde, hasta):
        return []


def test_facturas_delega_en_ventas_en_y_ordena_por_fecha():
    ventas = [_venta(2, 11), _venta(1, 10, estado="devuelta_parcial")]
    svc = ServicioReportes(_FakeVentas(ventas), _FakeDevoluciones(), None, None)
    r = svc.facturas(DESDE, HASTA)
    assert [v.id for v in r] == [1, 2]
    assert r[0].estado == "devuelta_parcial"          # no filtra por estado (solo ordena)
    assert isinstance(r, tuple)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/core/test_reportes_facturas.py -v`
Expected: FAIL con `AttributeError: 'ServicioReportes' object has no attribute 'facturas'`.

- [ ] **Step 3: Write minimal implementation**

En `src/core/servicio_reportes.py`, añadir a `ServicioReportes`:

```python
    def facturas(self, desde: datetime, hasta: datetime) -> tuple[Venta, ...]:
        vs = self._ventas.ventas_en(desde, hasta)
        return tuple(sorted(vs, key=lambda v: (v.fecha, v.id or 0)))
```

Añadir `Venta` al import de `core.entidades` en la cabecera del archivo (junto a `Arqueo, CajaSesion, MovimientoInventario`):

```python
from core.entidades import Arqueo, CajaSesion, MovimientoInventario, Venta
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/core/test_reportes_facturas.py -v`
Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add src/core/servicio_reportes.py tests/core/test_reportes_facturas.py
git commit -m "feat(reportes): facturas(desde, hasta) ordenadas (RPTFAC.3)"
```

---

### Task RPTFAC.4: Pestaña "Por factura" (listado + detalle) en caja/pantalla_reportes

**Files:**
- Modify: `src/caja/pantalla_reportes.py`
- Test: `tests/caja/test_pantalla_reportes_factura.py`

**Interfaces:**
- Consumes: `ContextoApp.svc_reportes.facturas(desde, hasta)` (RPTFAC.3), `ctx.repo_usuarios.por_id`, `ctx.repo_clientes.por_id`, `ctx.repo_ventas.pagos_de`, `ctx.repo_medios_pago.por_id`, `caja.formato.formato_moneda`.
- Produces: en `PantallaReportes` — atributos `self._tabla_factura: QTableWidget` (7 cols), `self._detalle_factura: QTableWidget` (4 cols), `self._facturas: tuple[Venta, ...]`; método `self._mostrar_detalle_factura()`; el listado se rellena dentro de `_consultar`.

- [ ] **Step 1: Write the failing test**

Create `tests/caja/test_pantalla_reportes_factura.py`:

```python
import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime  # noqa: E402
from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from caja.bootstrap import ADMIN_POR_DEFECTO  # noqa: E402
from caja.contexto import ContextoApp  # noqa: E402
from caja.pantalla_reportes import PantallaReportes  # noqa: E402
from core.entidades import LineaVenta, Pago, Venta  # noqa: E402


def _ctx_con_venta():
    ctx = ContextoApp.crear(":memory:")
    u = ctx.svc_usuarios.autenticar(*ADMIN_POR_DEFECTO)
    linea = LineaVenta(producto_id=1, descripcion="Café", cantidad_o_peso=Decimal("1"),
                       precio_unit=Decimal("7000"), impuesto=Decimal("1118"),
                       subtotal=Decimal("7000"))
    venta = Venta(fecha=datetime.now(), lineas=(linea,), total=Decimal("7000"),
                  total_impuestos=Decimal("1118"), usuario_id=u.id)
    ctx.repo_ventas.guardar(venta, [Pago(medio_pago_id=1, monto=Decimal("7000"))])
    return ctx, u


def test_pestana_factura_lista_la_venta_con_cajero():
    _app = QApplication.instance() or QApplication([])
    ctx, u = _ctx_con_venta()
    win = PantallaReportes(ctx)
    win.al_mostrar()
    assert win._tabla_factura.rowCount() == 1
    assert win._tabla_factura.item(0, 2).text() == u.nombre     # columna Cajero
    assert win._tabla_factura.item(0, 3).text() == "—"          # sin cliente


def test_seleccionar_factura_muestra_lineas_y_pagos():
    _app = QApplication.instance() or QApplication([])
    ctx, _ = _ctx_con_venta()
    win = PantallaReportes(ctx)
    win.al_mostrar()
    win._tabla_factura.selectRow(0)
    # 1 línea + 1 pago
    assert win._detalle_factura.rowCount() == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/caja/test_pantalla_reportes_factura.py -v`
Expected: FAIL con `AttributeError: 'PantallaReportes' object has no attribute '_tabla_factura'`.

- [ ] **Step 3: Write minimal implementation**

En `src/caja/pantalla_reportes.py`:

1) Ampliar el import de widgets para incluir `QAbstractItemView`:

```python
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDateEdit, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)
```

(`QComboBox` se usa en RPTFAC.5; se importa ya para no re-tocar la línea.)

2) En `__init__`, tras crear `tab_inv` y antes de construir `tabs`, añadir la pestaña "Por factura":

```python
        # Pestaña "Por factura"
        self._facturas: tuple = ()
        self._tabla_factura = QTableWidget(0, 7)
        self._tabla_factura.setHorizontalHeaderLabels(
            ["#", "Fecha", "Cajero", "Cliente", "Total", "IVA", "Estado"])
        self._tabla_factura.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla_factura.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tabla_factura.setSelectionMode(QAbstractItemView.SingleSelection)
        self._tabla_factura.itemSelectionChanged.connect(self._mostrar_detalle_factura)
        self._detalle_factura = QTableWidget(0, 4)
        self._detalle_factura.setHorizontalHeaderLabels(
            ["Detalle", "Cant/Peso", "Subtotal", "IVA"])
        self._detalle_factura.setEditTriggers(QTableWidget.NoEditTriggers)
        tab_fac = QWidget(); lf = QVBoxLayout(tab_fac)
        lf.addWidget(self._tabla_factura); lf.addWidget(QLabel("Detalle de la factura"))
        lf.addWidget(self._detalle_factura)
```

3) Registrar la pestaña en el `QTabWidget` (tras `tabs.addTab(tab_inv, "Inventario")`):

```python
        tabs.addTab(tab_fac, "Por factura")
```

4) Al final de `_consultar`, tras rellenar inventario, poblar el listado de facturas:

```python
        self._facturas = self._ctx.svc_reportes.facturas(desde, hasta)
        self._tabla_factura.setRowCount(0)
        for v in self._facturas:
            cajero = self._ctx.repo_usuarios.por_id(v.usuario_id) if v.usuario_id else None
            cliente = self._ctx.repo_clientes.por_id(v.cliente_id) if v.cliente_id else None
            fila = self._tabla_factura.rowCount()
            self._tabla_factura.insertRow(fila)
            valores = [
                str(v.id), v.fecha.strftime("%Y-%m-%d %H:%M"),
                cajero.nombre if cajero else "Sin cajero",
                cliente.nombre if cliente else "—",
                formato_moneda(v.total), formato_moneda(v.total_impuestos), v.estado]
            for col, texto in enumerate(valores):
                self._tabla_factura.setItem(fila, col, QTableWidgetItem(texto))
        self._detalle_factura.setRowCount(0)
```

5) Añadir el método `_mostrar_detalle_factura` a la clase:

```python
    def _mostrar_detalle_factura(self) -> None:
        fila = self._tabla_factura.currentRow()
        self._detalle_factura.setRowCount(0)
        if not (0 <= fila < len(self._facturas)):
            return
        v = self._facturas[fila]
        for ln in v.lineas:
            r = self._detalle_factura.rowCount()
            self._detalle_factura.insertRow(r)
            for col, texto in enumerate((ln.descripcion, str(ln.cantidad_o_peso),
                                         formato_moneda(ln.subtotal),
                                         formato_moneda(ln.impuesto))):
                self._detalle_factura.setItem(r, col, QTableWidgetItem(texto))
        for p in self._ctx.repo_ventas.pagos_de(v.id):
            medio = self._ctx.repo_medios_pago.por_id(p.medio_pago_id)
            r = self._detalle_factura.rowCount()
            self._detalle_factura.insertRow(r)
            nombre = medio.nombre if medio else f"#{p.medio_pago_id}"
            self._detalle_factura.setItem(r, 0, QTableWidgetItem(f"Pago · {nombre}"))
            self._detalle_factura.setItem(r, 2, QTableWidgetItem(formato_moneda(p.monto)))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/caja/test_pantalla_reportes_factura.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/caja/pantalla_reportes.py tests/caja/test_pantalla_reportes_factura.py
git commit -m "feat(reportes): pestaña Por factura con listado y detalle (RPTFAC.4)"
```

---

### Task RPTFAC.5: Pestaña "Por cajero" (rango + selector de sesión + por-medio) en caja/pantalla_reportes

**Files:**
- Modify: `src/caja/pantalla_reportes.py`
- Test: `tests/caja/test_pantalla_reportes_cajero.py`

**Interfaces:**
- Consumes: `ctx.svc_reportes.por_cajero(desde, hasta)` (RPTFAC.1), `ctx.svc_reportes.por_cajero_de_sesion(sesion_id)` (RPTFAC.2), `ctx.repo_usuarios.por_id`, `ctx.repo_medios_pago.por_id`, `ctx.repo_sesiones.listar() -> list[CajaSesion]`, `caja.formato.formato_moneda`. `QComboBox` ya importado en RPTFAC.4.
- Produces: en `PantallaReportes` — `self._tabla_cajero: QTableWidget` (5 cols), `self._fuente_cajero: QComboBox`; método `self._consultar_cajero()`; el combo se repuebla dentro de `_consultar`.

- [ ] **Step 1: Write the failing test**

Create `tests/caja/test_pantalla_reportes_cajero.py`:

```python
import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime  # noqa: E402
from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from caja.bootstrap import ADMIN_POR_DEFECTO  # noqa: E402
from caja.contexto import ContextoApp  # noqa: E402
from caja.pantalla_reportes import PantallaReportes  # noqa: E402
from core.entidades import LineaVenta, Pago, Venta  # noqa: E402


def _guardar_venta(ctx, usuario_id, total=Decimal("7000")):
    linea = LineaVenta(producto_id=1, descripcion="Café", cantidad_o_peso=Decimal("1"),
                       precio_unit=total, impuesto=Decimal("0"), subtotal=total)
    venta = Venta(fecha=datetime.now(), lineas=(linea,), total=total,
                  total_impuestos=Decimal("0"), usuario_id=usuario_id)
    ctx.repo_ventas.guardar(venta, [Pago(medio_pago_id=1, monto=total)])


def test_pestana_cajero_muestra_neto_por_cajero():
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    u = ctx.svc_usuarios.autenticar(*ADMIN_POR_DEFECTO)
    _guardar_venta(ctx, u.id)
    win = PantallaReportes(ctx)
    win.al_mostrar()
    assert win._tabla_cajero.rowCount() >= 1
    assert win._tabla_cajero.item(0, 0).text() == u.nombre
    assert win._tabla_cajero.item(0, 4).text() == "$ 7.000"      # Neto (formato_moneda: "$ 7.000")


def test_pestana_cajero_usuario_nulo_es_sin_cajero():
    _app = QApplication.instance() or QApplication([])
    ctx = ContextoApp.crear(":memory:")
    _guardar_venta(ctx, None)
    win = PantallaReportes(ctx)
    win.al_mostrar()
    assert win._tabla_cajero.item(0, 0).text() == "Sin cajero"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/caja/test_pantalla_reportes_cajero.py -v`
Expected: FAIL con `AttributeError: 'PantallaReportes' object has no attribute '_tabla_cajero'`.

- [ ] **Step 3: Write minimal implementation**

En `src/caja/pantalla_reportes.py`:

1) En `__init__`, tras el bloque de la pestaña "Por factura" y antes de construir `tabs`, añadir la pestaña "Por cajero":

```python
        # Pestaña "Por cajero"
        self._fuente_cajero = QComboBox()
        self._fuente_cajero.currentIndexChanged.connect(self._consultar_cajero)
        self._tabla_cajero = QTableWidget(0, 5)
        self._tabla_cajero.setHorizontalHeaderLabels(
            ["Cajero", "# Ventas", "Total", "Devoluciones", "Neto"])
        self._tabla_cajero.setEditTriggers(QTableWidget.NoEditTriggers)
        tab_caj = QWidget(); lc = QVBoxLayout(tab_caj)
        barra_caj = QHBoxLayout()
        barra_caj.addWidget(QLabel("Fuente")); barra_caj.addWidget(self._fuente_cajero)
        barra_caj.addStretch(1)
        lc.addLayout(barra_caj); lc.addWidget(self._tabla_cajero)
```

2) Registrar la pestaña (tras `tabs.addTab(tab_fac, "Por factura")`):

```python
        tabs.addTab(tab_caj, "Por cajero")
```

3) Al final de `_consultar`, tras poblar facturas, repoblar el combo de fuente. Usar un flag para no disparar `_consultar_cajero` en cadena mientras se llena el combo:

```python
        self._fuente_cajero.blockSignals(True)
        self._fuente_cajero.clear()
        self._fuente_cajero.addItem("Rango de fechas", None)
        for s in self._ctx.repo_sesiones.listar():
            etiqueta = f"Sesión #{s.id} · {s.apertura_fecha.strftime('%Y-%m-%d %H:%M')}"
            self._fuente_cajero.addItem(etiqueta, s.id)
        self._fuente_cajero.blockSignals(False)
        self._consultar_cajero()
```

4) Añadir el método `_consultar_cajero` a la clase:

```python
    def _consultar_cajero(self) -> None:
        sesion_id = self._fuente_cajero.currentData()
        if sesion_id is None:
            desde, hasta = self._rango()
            filas = self._ctx.svc_reportes.por_cajero(desde, hasta)
        else:
            filas = self._ctx.svc_reportes.por_cajero_de_sesion(sesion_id)
        self._tabla_cajero.setRowCount(0)
        for c in filas:
            cajero = self._ctx.repo_usuarios.por_id(c.usuario_id) if c.usuario_id else None
            fila = self._tabla_cajero.rowCount()
            self._tabla_cajero.insertRow(fila)
            valores = [
                cajero.nombre if cajero else "Sin cajero", str(c.num_ventas),
                formato_moneda(c.total), formato_moneda(c.total_devoluciones),
                formato_moneda(c.neto)]
            for col, texto in enumerate(valores):
                self._tabla_cajero.setItem(fila, col, QTableWidgetItem(texto))
            for medio_id, monto in c.por_medio.items():
                medio = self._ctx.repo_medios_pago.por_id(medio_id)
                nombre = medio.nombre if medio else f"#{medio_id}"
                sub = self._tabla_cajero.rowCount()
                self._tabla_cajero.insertRow(sub)
                self._tabla_cajero.setItem(sub, 0, QTableWidgetItem(f"    {nombre}"))
                self._tabla_cajero.setItem(sub, 4, QTableWidgetItem(formato_moneda(monto)))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/caja/test_pantalla_reportes_cajero.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Run full suite and commit**

Run: `python -m pytest -q`
Expected: PASS (269 = 259 base + 10 nuevos; ajustar si algún test añade/omite casos).

```bash
git add src/caja/pantalla_reportes.py tests/caja/test_pantalla_reportes_cajero.py
git commit -m "feat(reportes): pestaña Por cajero con selector de sesión (RPTFAC.5)"
```

---

## Cierre del epic

- [ ] Actualizar la fila de reportes en `docs/README-pos.md` (Estado actual) para reflejar las pestañas "Por factura" y "Por cajero" y los métodos nuevos de `ServicioReportes`.
- [ ] Verificar suite completa verde: `python -m pytest -q`.

## Self-review (cobertura de la spec)

- Por factura (listado + detalle, todas menos anuladas con estado) → RPTFAC.3 (core) + RPTFAC.4 (UI). ✅
- Por cajero rango (agregado + por medio, usuario nulo al final, neto con devoluciones) → RPTFAC.1. ✅
- Por cajero sesión (cruce por turno) → RPTFAC.2 + selector en RPTFAC.5. ✅
- `ReporteCajero` como única estructura nueva; sin `FacturaResumen` → RPTFAC.1 / spec. ✅
- Sin métodos de repo nuevos ni SQL nueva; `core` sin Qt/SQLite → todas las tasks usan puertos existentes. ✅
- Acceso libre (sin `ver_reportes`) → no hay task de permisos, por diseño. ✅
- Atribución de devoluciones al cajero que procesó → RPTFAC.1 (`d.usuario_id`) + regla en Global Constraints. ✅
