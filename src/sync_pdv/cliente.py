"""Cliente de sincronización: sube pendientes del outbox a la nube (idempotente por uuid)."""
from __future__ import annotations

from dataclasses import asdict
from typing import Protocol

from sync_pdv.outbox import RepositorioOutboxSQLite


class TransporteSync(Protocol):
    def push(self, eventos: list[dict]) -> list[str]: ...
    def pull_catalogo(self, local_id: str) -> dict: ...


class ClienteSync:
    def __init__(self, outbox: RepositorioOutboxSQLite, transporte: TransporteSync,
                 replica=None, local_id: str | None = None) -> None:
        self._outbox = outbox
        self._transporte = transporte
        self._replica = replica
        self._local_id = local_id

    def sincronizar(self, limite: int = 100) -> int:
        pendientes = self._outbox.pendientes(limite)
        aceptados: list[str] = []
        if pendientes:
            aceptados = self._transporte.push([asdict(e) for e in pendientes])
            if aceptados:
                self._outbox.marcar_enviados(aceptados)
        if self._replica is not None and self._local_id:
            snap = self._transporte.pull_catalogo(self._local_id)
            self._replica.aplicar_catalogo(snap)
        return len(aceptados)


class TransporteHTTP:
    """POST del lote a /sync/push con Authorization: Bearer <local_id>:<token>."""

    def __init__(self, url: str, local_id: str, token: str) -> None:
        self._base = url.rstrip("/")
        self._url = self._base + "/sync/push"
        self._auth = f"Bearer {local_id}:{token}"

    def push(self, eventos: list[dict]) -> list[str]:
        import urllib.request
        import json
        peticion = urllib.request.Request(
            self._url, data=json.dumps({"eventos": eventos}).encode(),
            headers={"Authorization": self._auth, "Content-Type": "application/json"})
        with urllib.request.urlopen(peticion, timeout=10.0) as r:
            return json.loads(r.read())["aceptados"]

    def pull_catalogo(self, local_id: str) -> dict:
        import urllib.request
        import json
        peticion = urllib.request.Request(
            self._base + f"/sync/catalogo?local_id={local_id}",
            headers={"Authorization": self._auth})
        with urllib.request.urlopen(peticion, timeout=10.0) as r:
            return json.loads(r.read())
