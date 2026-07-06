"""Descarga fotos genéricas de cada producto demo y las convierte a .ico.

Herramienta de build (NO se ejecuta en runtime). Busca en Wikimedia Commons
—fuente con licencia libre—, recorta cuadrado centrado, redimensiona y guarda
un .ico pequeño en src/caja/recursos/productos/<codigo_barras>.ico. Idempotente:
no re-descarga un producto cuyo .ico ya existe (usar --forzar para rehacer).

Uso:  python scripts/generar_iconos_productos.py [--forzar]
"""
from __future__ import annotations

import io
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

DESTINO = Path(__file__).resolve().parent.parent / "src" / "caja" / "recursos" / "productos"
LADO = 128  # px del .ico cuadrado
UA = "pos-siesa-remake/1.0 (generador de iconos de producto; contacto: local)"
API = "https://commons.wikimedia.org/w/api.php"

# codigo_barras -> término de búsqueda en Commons (inglés = más resultados)
BUSQUEDAS = {
    "00190": "raw beef meat cut butcher",
    "00121": "pork trotter raw",
    "7700001": "raw chicken breast",
    "7700002": "ground beef minced meat",
    "7700003": "red apple fruit",
    "7700004": "banana fruit",
    "7700005": "potato tuber",
    "7700006": "white rice grain",
    "7000006": "green cucumbers",
}
# archivos fijados por título cuando la búsqueda no da una buena foto genérica
FIJADOS = {
    "7000006": "File:Green Cucumbers.JPG",
}
NOMBRES = {
    "00190": "Ampolleta (res)", "00121": "Pezuña de cerdo",
    "7700001": "Pechuga de pollo", "7700002": "Carne molida",
    "7700003": "Manzana roja", "7700004": "Banano",
    "7700005": "Papa pastusa", "7700006": "Arroz 500g",
    "7000006": "Pepino",
}
EXT_OK = (".jpg", ".jpeg", ".png")


def _get(url: str, reintentos: int = 5) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for intento in range(reintentos):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and intento < reintentos - 1:
                espera = 2 ** intento * 3  # 3, 6, 12, 24 s
                print(f"  429: espero {espera}s y reintento…")
                time.sleep(espera)
                continue
            raise
    raise RuntimeError("agotados los reintentos")


def buscar_imagen(termino: str) -> tuple[str, str, str] | None:
    """Devuelve (url_thumbnail, titulo, licencia) del primer archivo apto, o None."""
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": termino, "gsrnamespace": "6", "gsrlimit": "12",
        "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": str(LADO * 2),
    }
    datos = json.loads(_get(f"{API}?{urllib.parse.urlencode(params)}"))
    paginas = datos.get("query", {}).get("pages", {})
    # respeta el orden de relevancia de la búsqueda
    for pag in sorted(paginas.values(), key=lambda p: p.get("index", 999)):
        info = (pag.get("imageinfo") or [{}])[0]
        thumb = info.get("thumburl")
        titulo = pag.get("title", "")
        if not thumb or not titulo.lower().endswith(EXT_OK):
            continue
        meta = info.get("extmetadata", {})
        lic = meta.get("LicenseShortName", {}).get("value", "desconocida")
        return thumb, titulo, lic
    return None


def imagen_por_titulo(titulo: str) -> tuple[str, str, str] | None:
    """Resuelve (url_thumbnail, titulo, licencia) de un archivo Commons por su título."""
    params = {
        "action": "query", "format": "json", "titles": titulo,
        "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": str(LADO * 2),
    }
    datos = json.loads(_get(f"{API}?{urllib.parse.urlencode(params)}"))
    pag = next(iter(datos.get("query", {}).get("pages", {}).values()), {})
    info = (pag.get("imageinfo") or [{}])[0]
    thumb = info.get("thumburl")
    if not thumb:
        return None
    lic = info.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "desconocida")
    return thumb, pag.get("title", titulo), lic


def a_ico(datos: bytes, ruta: Path) -> None:
    img = Image.open(io.BytesIO(datos)).convert("RGBA")
    lado = min(img.size)
    izq = (img.width - lado) // 2
    arr = (img.height - lado) // 2
    img = img.crop((izq, arr, izq + lado, arr + lado)).resize((LADO, LADO), Image.LANCZOS)
    img.save(ruta, format="ICO", sizes=[(LADO, LADO)])


RUTA_CREDITOS = DESTINO / "CREDITOS.md"


def creditos_previos() -> dict[str, str]:
    """Lee las filas de crédito ya existentes: {codigo: fila markdown}."""
    filas: dict[str, str] = {}
    if not RUTA_CREDITOS.exists():
        return filas
    for linea in RUTA_CREDITOS.read_text(encoding="utf-8").splitlines():
        for codigo in BUSQUEDAS:
            if f"`{codigo}.ico`" in linea:
                filas[codigo] = linea
    return filas


def main() -> int:
    forzar = "--forzar" in sys.argv
    DESTINO.mkdir(parents=True, exist_ok=True)
    # arranca de los créditos previos para no perder los .ico que se omiten
    filas = creditos_previos()
    fallidos = []
    for codigo, termino in BUSQUEDAS.items():
        ruta = DESTINO / f"{codigo}.ico"
        if ruta.exists() and not forzar:
            print(f"= {codigo} {NOMBRES[codigo]}: ya existe, se omite")
            continue
        time.sleep(2)  # throttle amable con la API de Commons
        try:
            hallazgo = (imagen_por_titulo(FIJADOS[codigo]) if codigo in FIJADOS
                        else buscar_imagen(termino))
            if hallazgo is None:
                raise RuntimeError("sin resultados aptos")
            thumb, titulo, lic = hallazgo
            a_ico(_get(thumb), ruta)
            filas[codigo] = f"| {NOMBRES[codigo]} | `{codigo}.ico` | {titulo} | {lic} |"
            print(f"+ {codigo} {NOMBRES[codigo]}: {titulo} ({lic})")
        except Exception as exc:  # noqa: BLE001 - herramienta de build, reporta y sigue
            fallidos.append(codigo)
            print(f"! {codigo} {NOMBRES[codigo]}: FALLÓ ({exc})", file=sys.stderr)
    if filas:
        cab = ["# Créditos de imágenes de producto", "",
               "Fuente: Wikimedia Commons. Cada archivo conserva su licencia original.", "",
               "| Producto | Archivo .ico | Origen (Commons) | Licencia |",
               "|---|---|---|---|"]
        orden = [filas[c] for c in BUSQUEDAS if c in filas]
        RUTA_CREDITOS.write_text("\n".join(cab + orden) + "\n", encoding="utf-8")
    if fallidos:
        print(f"\nFallaron: {', '.join(fallidos)}", file=sys.stderr)
        return 1
    print("\nListo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
