"""Bandeja de traslados pendientes (entradas por confirmar en esta ubicación)."""
from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from caja.formato import formato_cantidad

_COLS = ["Producto", "Cantidad", "Desde (ubicación)", "Fecha"]


class DialogoBandejaPendientes(QDialog):
    def __init__(self, ctx, parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._pendientes: list[dict] = []
        self.setWindowTitle("Traslados pendientes de confirmar")

        self._tabla = QTableWidget(0, len(_COLS))
        self._tabla.setHorizontalHeaderLabels(_COLS)
        self._tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla.setSelectionBehavior(QTableWidget.SelectRows)

        self._boton_confirmar = QPushButton("Confirmar")
        self._boton_confirmar.clicked.connect(self._confirmar_seleccionado)
        self._boton_cerrar = QPushButton("Cerrar")
        self._boton_cerrar.clicked.connect(self.accept)

        botones = QHBoxLayout()
        botones.addStretch(1)
        botones.addWidget(self._boton_confirmar)
        botones.addWidget(self._boton_cerrar)

        layout = QVBoxLayout(self)
        layout.addWidget(self._tabla)
        layout.addLayout(botones)

        self._recargar()

    def _recargar(self) -> None:
        ubicacion_id = int(self._ctx.almacen_id)
        self._pendientes = self._ctx.repo_movimientos_ubicacion.pendientes(ubicacion_id)
        self._tabla.setRowCount(0)
        for mov in self._pendientes:
            fila = self._tabla.rowCount()
            self._tabla.insertRow(fila)
            celdas = [str(mov["producto_id"]), formato_cantidad(mov["cantidad"], ""),
                     self._origen(mov), str(mov["fecha"])]
            for col, texto in enumerate(celdas):
                self._tabla.setItem(fila, col, QTableWidgetItem(texto))

    def _origen(self, mov: dict) -> str:
        """La entrada pendiente tiene origen_id=None (el origen vive en la salida del
        grupo). Si esa salida está en la BD local, muestra su ubicación; si no (caso
        cross-local: el destino no sincroniza la salida del origen), 'Traslado entrante'."""
        origen = mov.get("origen_id")
        if origen is None and mov.get("grupo_uuid"):
            for m in self._ctx.repo_movimientos_ubicacion.movimientos_grupo(mov["grupo_uuid"]):
                if m.get("origen_id") is not None:
                    origen = m["origen_id"]
                    break
        return f"Ubicación {origen}" if origen is not None else "Traslado entrante"

    @Slot()
    def _confirmar_seleccionado(self) -> None:
        fila = self._tabla.currentRow()
        if not (0 <= fila < len(self._pendientes)):
            return
        mov = self._pendientes[fila]
        self._ctx.repo_movimientos_ubicacion.confirmar(mov["uuid"])
        confirmado = dict(mov)
        confirmado["estado"] = "confirmado"
        confirmado["actualizado_en"] = datetime.now(timezone.utc).isoformat()
        self._ctx.encolar_movimiento(confirmado)
        self._recargar()
