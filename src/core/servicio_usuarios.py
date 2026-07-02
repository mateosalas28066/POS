"""Servicio de usuarios: crear y autenticar. Python puro vía puerto + seguridad."""
from __future__ import annotations

from core.entidades import Usuario
from core.puertos import RepositorioUsuarios
from core.seguridad import hash_password, verificar


class UsuarioDuplicado(ValueError):
    pass


class CredencialInvalida(ValueError):
    pass


class ServicioUsuarios:
    def __init__(self, repo: RepositorioUsuarios) -> None:
        self._repo = repo

    def crear(self, nombre: str, password: str, rol: str = "cajero") -> Usuario:
        if not nombre.strip():
            raise ValueError("el nombre es obligatorio")
        if not password:
            raise ValueError("la contraseña es obligatoria")
        if self._repo.por_nombre(nombre) is not None:
            raise UsuarioDuplicado(f"ya existe usuario {nombre!r}")
        return self._repo.guardar(Usuario(nombre=nombre, rol=rol), hash_password(password))

    def autenticar(self, nombre: str, password: str) -> Usuario | None:
        cred = self._repo.credencial(nombre)
        if cred is None:
            return None
        usuario, hash_ = cred
        return usuario if verificar(password, hash_) else None

    def cambiar_password(self, nombre: str, actual: str, nueva: str) -> None:
        """Autoservicio: el usuario cambia su propia contraseña probando la actual."""
        if not nueva:
            raise ValueError("la contraseña nueva es obligatoria")
        usuario = self.autenticar(nombre, actual)
        if usuario is None:
            raise CredencialInvalida("la contraseña actual no es correcta")
        self._repo.actualizar_password(usuario.id, hash_password(nueva))

    def listar(self) -> list[Usuario]:
        return self._repo.listar()
