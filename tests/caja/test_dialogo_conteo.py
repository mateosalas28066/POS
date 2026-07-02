# tests/caja/test_dialogo_conteo.py
import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from decimal import Decimal  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from caja.dialogos.dialogo_conteo import DialogoConteoEfectivo  # noqa: E402


def test_total_refleja_lo_tecleado():
    _app = QApplication.instance() or QApplication([])
    d = DialogoConteoEfectivo()
    d._spins[50000].setValue(2)
    d._spins[1000].setValue(3)
    assert d.total() == Decimal("103000")


def test_total_inicial_es_cero():
    _app = QApplication.instance() or QApplication([])
    d = DialogoConteoEfectivo()
    assert d.total() == Decimal("0")


def test_prellenado_con_desglose_previo():
    _app = QApplication.instance() or QApplication([])
    d = DialogoConteoEfectivo(desglose={50000: 2, 1000: 3})
    assert d._spins[50000].value() == 2
    assert d._spins[1000].value() == 3
    assert d.total() == Decimal("103000")


def test_desglose_devuelve_lo_tecleado():
    _app = QApplication.instance() or QApplication([])
    d = DialogoConteoEfectivo()
    d._spins[50000].setValue(1)
    assert d.desglose()[50000] == 1
    assert d.desglose()[1000] == 0
