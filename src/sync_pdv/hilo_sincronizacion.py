"""Sincronización periódica en background: llama ClienteSync.sincronizar() cada
`intervalo_segundos` hasta detenerse. Usa threading (stdlib), sin acoplar sync_pdv
a Qt — quien la use (la app de caja) decide cuándo arrancarla y con qué conexión."""
from __future__ import annotations

import threading

from sync_pdv.cliente import ClienteSync


class HiloSincronizacion:
    def __init__(self, cliente: ClienteSync, intervalo_segundos: float = 30.0) -> None:
        self._cliente = cliente
        self._intervalo = intervalo_segundos
        self._detener = threading.Event()
        self._hilo: threading.Thread | None = None

    def iniciar(self) -> None:
        if self._hilo is not None:
            return
        self._hilo = threading.Thread(target=self._loop, daemon=True)
        self._hilo.start()

    def detener(self) -> None:
        self._detener.set()
        if self._hilo is not None:
            self._hilo.join(timeout=self._intervalo + 1)

    def _loop(self) -> None:
        while not self._detener.is_set():
            try:
                self._cliente.sincronizar()
            except Exception:
                pass  # red caída / backend abajo: el POS sigue vendiendo, se reintenta el próximo ciclo
            self._detener.wait(self._intervalo)
