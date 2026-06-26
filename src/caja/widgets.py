"""Widgets reutilizables. Solo composición Qt; estilo en tema.qss."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFrame, QLabel, QToolButton, QVBoxLayout

from caja.formato import formato_moneda
from core.entidades import Producto


class TarjetaProducto(QFrame):
    """Card clickable con nombre, precio y categoría de un producto."""

    seleccionado = Signal(object)

    def __init__(self, producto: Producto, nombre_categoria: str = "") -> None:
        super().__init__()
        self._producto = producto
        self.setObjectName("card")
        self.setCursor(Qt.PointingHandCursor)

        nombre = QLabel(producto.nombre)
        nombre.setWordWrap(True)
        precio = QLabel(formato_moneda(producto.precio))
        precio.setObjectName("kpi-valor")
        cat = QLabel(nombre_categoria or "—")
        cat.setObjectName("secundario")

        layout = QVBoxLayout(self)
        layout.addWidget(nombre)
        layout.addWidget(precio)
        layout.addWidget(cat)

    def _emitir(self) -> None:
        self.seleccionado.emit(self._producto)

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt API)
        self._emitir()
        super().mousePressEvent(event)


class TarjetaKpi(QFrame):
    """Card de indicador: título, valor grande y subtítulo opcional."""

    def __init__(self, titulo: str, valor: str = "", subtitulo: str = "") -> None:
        super().__init__()
        self.setObjectName("card")
        self._titulo = QLabel(titulo)
        self._titulo.setObjectName("secundario")
        self._valor = QLabel(valor)
        self._valor.setObjectName("kpi-valor")
        self._subtitulo = QLabel(subtitulo)
        self._subtitulo.setObjectName("muted")

        layout = QVBoxLayout(self)
        layout.addWidget(self._titulo)
        layout.addWidget(self._valor)
        layout.addWidget(self._subtitulo)

    def set_valor(self, texto: str) -> None:
        self._valor.setText(texto)

    def set_subtitulo(self, texto: str) -> None:
        self._subtitulo.setText(texto)

    def set_estado(self, estado: str) -> None:
        """estado ∈ {'normal','positivo','alerta'} — cambia color del valor."""
        nombre = "kpi-valor" if estado == "normal" else estado
        self._valor.setObjectName(nombre)
        self._valor.style().unpolish(self._valor)
        self._valor.style().polish(self._valor)


class BotonRail(QToolButton):
    """Botón del rail de navegación: icono + tooltip, checkable exclusivo."""

    def __init__(self, ruta_icono: str, tooltip: str) -> None:
        super().__init__()
        self.setObjectName("rail")
        self.setCheckable(True)
        self.setToolTip(tooltip)
        self.setIcon(QIcon(ruta_icono))
        self.setIconSize(QSize(24, 24))
        self.setToolButtonStyle(Qt.ToolButtonIconOnly)
