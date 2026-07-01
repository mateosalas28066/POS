"""Servicio del maestro de clientes. Python puro: valida y persiste vía puerto."""
from __future__ import annotations

from core.entidades import Cliente
from core.puertos import RepositorioClientes

IDENTIFICACION_CONSUMIDOR_FINAL = "222222222222"


class ClienteDuplicado(ValueError):
    pass


class ClienteBloqueado(ValueError):
    pass


class ServicioClientes:
    """Reglas del maestro de clientes sobre un RepositorioClientes."""

    def __init__(self, repo: RepositorioClientes) -> None:
        self._repo = repo

    def crear(self, identificacion: str, nombre: str, contacto: str | None = None, *,
              tipo_documento: str | None = None, regimen: str | None = None,
              tipo_responsabilidad: str | None = None) -> Cliente:
        if not identificacion.strip():
            raise ValueError("la identificación es obligatoria")
        if not nombre.strip():
            raise ValueError("el nombre es obligatorio")
        if self._repo.por_identificacion(identificacion) is not None:
            raise ClienteDuplicado(
                f"ya existe cliente con identificación {identificacion}")
        return self._repo.guardar(Cliente(
            identificacion=identificacion, nombre=nombre, contacto=contacto,
            tipo_documento=tipo_documento, regimen=regimen,
            tipo_responsabilidad=tipo_responsabilidad))

    def actualizar(self, cliente: Cliente) -> Cliente:
        if cliente.id is None:
            raise ValueError("no se puede actualizar un cliente sin id")
        actual = self._repo.por_id(cliente.id)
        if actual is not None and actual.bloqueado_edicion:
            raise ClienteBloqueado(f"cliente {cliente.id} bloqueado para edición")
        return self._repo.actualizar(cliente)

    def buscar(self, identificacion: str) -> Cliente | None:
        return self._repo.por_identificacion(identificacion)

    def listar(self) -> list[Cliente]:
        return self._repo.listar()

    def consumidor_final(self) -> Cliente:
        cliente = self._repo.por_identificacion(IDENTIFICACION_CONSUMIDOR_FINAL)
        if cliente is None:
            raise LookupError("consumidor final no sembrado; aplica las migraciones")
        return cliente
