"""Permisos por rol. Python puro. admin puede todo; cajero todo salvo lo restringido."""
from __future__ import annotations

ACCION_GESTIONAR_USUARIOS = "gestionar_usuarios"
ACCION_EDITAR_PRODUCTOS = "editar_productos"
ACCION_DESCUENTO_MANUAL = "aplicar_descuento_manual"

PERMISOS_ADMIN = frozenset({
    ACCION_GESTIONAR_USUARIOS, ACCION_EDITAR_PRODUCTOS, ACCION_DESCUENTO_MANUAL})


def puede(rol: str, accion: str) -> bool:
    return rol == "admin" or accion not in PERMISOS_ADMIN
