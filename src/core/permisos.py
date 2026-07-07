"""Permisos por rol. Python puro. admin puede todo; cajero todo salvo lo restringido."""
from __future__ import annotations

ACCION_GESTIONAR_USUARIOS = "gestionar_usuarios"
ACCION_EDITAR_PRODUCTOS = "editar_productos"
ACCION_DESCUENTO_MANUAL = "aplicar_descuento_manual"
ACCION_GESTIONAR_PROMOCIONES = "gestionar_promociones"
ACCION_GESTIONAR_INVENTARIO = "gestionar_inventario_multiubicacion"
ACCION_CONFIRMAR_TRASLADO = "confirmar_traslado"

PERMISOS_ADMIN = frozenset({
    ACCION_GESTIONAR_USUARIOS, ACCION_EDITAR_PRODUCTOS, ACCION_DESCUENTO_MANUAL,
    ACCION_GESTIONAR_INVENTARIO, ACCION_CONFIRMAR_TRASLADO})


def puede(rol: str, accion: str) -> bool:
    return rol == "admin" or accion not in PERMISOS_ADMIN
