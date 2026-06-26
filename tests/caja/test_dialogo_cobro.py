import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.entidades import MedioPago  # noqa: E402
from caja.dialogos.dialogo_cobro import DialogoCobro  # noqa: E402

MEDIOS = [MedioPago(nombre="Efectivo", id=1), MedioPago(nombre="Tarjeta", id=2)]


def test_cobro_exacto_un_medio():
    _app = QApplication.instance() or QApplication([])
    d = DialogoCobro(Decimal("10000"), MEDIOS, modo="cobro", efectivo_id=1)
    d._montos[1].setValue(10000)
    assert d._validar() is None
    pagos = d.pagos()
    assert sum(p.monto for p in pagos) == Decimal("10000")
    assert d.vuelto() == Decimal("0")


def test_cobro_con_vuelto_ajusta_efectivo():
    _app = QApplication.instance() or QApplication([])
    d = DialogoCobro(Decimal("10000"), MEDIOS, modo="cobro", efectivo_id=1)
    d._montos[1].setValue(15000)  # paga 15000 en efectivo
    assert d._validar() is None
    pagos = d.pagos()
    assert sum(p.monto for p in pagos) == Decimal("10000")  # registrado = total
    assert d.vuelto() == Decimal("5000")


def test_cobro_insuficiente_da_error():
    _app = QApplication.instance() or QApplication([])
    d = DialogoCobro(Decimal("10000"), MEDIOS, modo="cobro", efectivo_id=1)
    d._montos[1].setValue(8000)
    assert d._validar() is not None


def test_reembolso_exige_suma_exacta():
    _app = QApplication.instance() or QApplication([])
    d = DialogoCobro(Decimal("7000"), MEDIOS, modo="reembolso", efectivo_id=1)
    d._montos[1].setValue(7000)
    assert d._validar() is None
    d._montos[1].setValue(8000)
    assert d._validar() is not None
