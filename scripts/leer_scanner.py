"""Captura y decodifica en vivo lo que envía un scanner/balanza por puerto serial.

Herramienta de diagnóstico (no forma parte del POS): sirve para ver exactamente qué
bytes manda el lector — prefijos, terminador (\\r / \\n / ninguno) y si el código es un
EAN-13 de peso variable — antes de decidir configuración de hardware o ajuste de formato.

Uso:
    python -m scripts.leer_scanner COM6            # o: python scripts/leer_scanner.py COM6
    POS_SCANNER_PORT=COM6 python scripts/leer_scanner.py
    python scripts/leer_scanner.py COM6 --baud 9600 --segundos 30

Escaneá el producto de prueba y compará lo crudo (repr + hex) contra el EAN-13 esperado.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# permitir importar core.* sin instalar el paquete
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from core.perifericos.gs1 import decodificar_gs1, es_peso_variable  # noqa: E402


def _analizar(codigo: str) -> str:
    """Una línea legible: ¿es peso variable?, y si sí, producto + peso extraídos."""
    if not codigo:
        return "  (vacío)"
    if not es_peso_variable(codigo):
        extra = "" if len(codigo) == 13 else f"  [len={len(codigo)}, no 13]"
        return f"  → NO es peso variable; se buscaría como código de barras tal cual{extra}"
    try:
        r = decodificar_gs1(codigo)
    except ValueError as exc:
        return f"  → peso variable pero inválido: {exc}"
    return f"  → peso variable: producto={r.codigo_producto!r}  peso={r.peso_kg} kg  valor_crudo={r.valor_crudo}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Captura cruda de un scanner serial.")
    parser.add_argument("puerto", nargs="?", default=os.environ.get("POS_SCANNER_PORT"),
                        help="Puerto serial (ej. COM6). Por defecto $POS_SCANNER_PORT.")
    parser.add_argument("--baud", type=int, default=int(os.environ.get("POS_SCANNER_BAUD", "9600")))
    parser.add_argument("--segundos", type=float, default=30.0,
                        help="Cuánto escuchar antes de salir (Ctrl-C corta antes).")
    args = parser.parse_args(argv)

    if not args.puerto:
        parser.error("indicá el puerto (arg o $POS_SCANNER_PORT), ej. COM6")

    try:
        import serial  # type: ignore[import-not-found]
    except ImportError:
        print("Falta pyserial:  pip install pyserial", file=sys.stderr)
        return 2

    try:
        s = serial.Serial(args.puerto, baudrate=args.baud, timeout=0.2)
    except serial.SerialException as exc:
        print(f"No se pudo abrir {args.puerto} @ {args.baud}: {exc}", file=sys.stderr)
        print("¿Hay otra ventana/POS usando el puerto? Cerrala y reintentá.", file=sys.stderr)
        return 2

    print(f"Escuchando {args.puerto} @ {args.baud} baud por {args.segundos:.0f}s. Escaneá ahora… (Ctrl-C para salir)\n")
    fin = time.time() + args.segundos
    buffer = bytearray()
    try:
        while time.time() < fin:
            datos = s.read(s.in_waiting or 1)
            if not datos:
                continue
            # 1) lo verdaderamente crudo de esta lectura: revela prefijos y terminador
            print(f"crudo: {datos!r}   hex: {datos.hex(' ')}")
            # 2) reconstruir líneas como lo hace el POS (\\r y \\n separan escaneos)
            buffer.extend(datos)
            partes = bytes(buffer).replace(b"\r", b"\n").split(b"\n")
            buffer = bytearray(partes[-1])
            for parte in partes[:-1]:
                codigo = parte.decode("ascii", errors="replace").strip()
                if codigo:
                    print(f"línea: {codigo!r}")
                    print(_analizar(codigo))
    except KeyboardInterrupt:
        print("\n(cortado)")
    finally:
        s.close()

    if buffer:
        resto = bytes(buffer).decode("ascii", errors="replace").strip()
        print(f"\n⚠ Quedó texto SIN terminador (\\r/\\n) en el buffer: {resto!r}")
        print("  Si esto pasa entre escaneos, el POS pega este resto con el siguiente código.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
