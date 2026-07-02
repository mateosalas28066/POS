"""Servicio del maestro de proveedores. Python puro: valida y persiste vía puerto."""
from __future__ import annotations

from core.entidades import Proveedor
from core.puertos import RepositorioProveedores


class ProveedorDuplicado(ValueError):
    pass


class ProveedorBloqueado(ValueError):
    pass


class ServicioProveedores:
    """Reglas del maestro de proveedores sobre un RepositorioProveedores."""

    def __init__(self, repo: RepositorioProveedores) -> None:
        self._repo = repo

    def crear(self, identificacion: str, nombre: str, contacto: str | None = None) -> Proveedor:
        if not identificacion.strip():
            raise ValueError("la identificación es obligatoria")
        if not nombre.strip():
            raise ValueError("el nombre es obligatorio")
        if self._repo.por_identificacion(identificacion) is not None:
            raise ProveedorDuplicado(
                f"ya existe proveedor con identificación {identificacion}")
        return self._repo.guardar(Proveedor(
            identificacion=identificacion, nombre=nombre, contacto=contacto))

    def actualizar(self, proveedor: Proveedor) -> Proveedor:
        if proveedor.id is None:
            raise ValueError("no se puede actualizar un proveedor sin id")
        actual = self._repo.por_id(proveedor.id)
        if actual is not None and actual.bloqueado_edicion:
            raise ProveedorBloqueado(f"proveedor {proveedor.id} bloqueado para edición")
        return self._repo.actualizar(proveedor)

    def buscar(self, identificacion: str) -> Proveedor | None:
        return self._repo.por_identificacion(identificacion)

    def listar(self) -> list[Proveedor]:
        return self._repo.listar()
