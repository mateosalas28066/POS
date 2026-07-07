import time

from sync_pdv.hilo_sincronizacion import HiloSincronizacion


class _ClienteFake:
    def __init__(self):
        self.llamadas = 0

    def sincronizar(self, limite: int = 100) -> int:
        self.llamadas += 1
        return 0


class _ClienteQueFalla:
    def __init__(self):
        self.llamadas = 0

    def sincronizar(self, limite: int = 100) -> int:
        self.llamadas += 1
        raise ConnectionError("backend caído")


def test_sincroniza_inmediatamente_al_iniciar():
    cliente = _ClienteFake()
    hilo = HiloSincronizacion(cliente, intervalo_segundos=5)
    hilo.iniciar()
    time.sleep(0.05)
    hilo.detener()
    assert cliente.llamadas >= 1


def test_repite_segun_intervalo():
    cliente = _ClienteFake()
    hilo = HiloSincronizacion(cliente, intervalo_segundos=0.02)
    hilo.iniciar()
    time.sleep(0.15)
    hilo.detener()
    assert cliente.llamadas >= 2


def test_detener_no_espera_el_intervalo_completo():
    cliente = _ClienteFake()
    hilo = HiloSincronizacion(cliente, intervalo_segundos=5)
    hilo.iniciar()
    time.sleep(0.02)
    inicio = time.monotonic()
    hilo.detener()
    assert time.monotonic() - inicio < 1.0


def test_errores_de_red_no_matan_el_hilo():
    cliente = _ClienteQueFalla()
    hilo = HiloSincronizacion(cliente, intervalo_segundos=0.02)
    hilo.iniciar()
    time.sleep(0.15)
    hilo.detener()
    assert cliente.llamadas >= 2  # siguió reintentando pese al error
