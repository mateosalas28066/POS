"""core debe ser importable como paquete aislado (sin depender de inventario/ventas)."""
import ast
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def test_pyproject_declara_pos_core():
    data = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["name"] == "pos-core"
    paquetes = data["tool"]["setuptools"]["packages"]["find"]["include"]
    assert "core*" in paquetes  # solo core (+ subpaquetes), no inventario/ventas/caja


def test_core_no_importa_capas_externas():
    """Regla hexagonal: core no importa inventario/ventas/caja/facturacion_dian."""
    prohibido = {"inventario", "ventas", "caja", "facturacion_dian", "sync_pdv"}
    for py in (RAIZ / "src" / "core").rglob("*.py"):
        arbol = ast.parse(py.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ImportFrom) and nodo.module:
                raiz = nodo.module.split(".")[0]
                assert raiz not in prohibido, f"{py.name} importa {nodo.module}"
