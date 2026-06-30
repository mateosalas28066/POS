"""Decodificación de códigos GS1 de peso variable (EAN-13) y adaptador LectorPeso."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class FormatoGS1:
    prefijos: tuple[str, ...] = ("2",)  # primer dígito que marca peso variable
    ini_codigo: int = 1
    fin_codigo: int = 6   # codigo = ean[ini_codigo:fin_codigo] (5 dígitos)
    ini_valor: int = 7
    fin_valor: int = 12   # valor embebido = ean[ini_valor:fin_valor] (5 dígitos)
    decimales_valor: int = 3  # gramos -> kg (solo aplica en modo peso)
    valor_es_precio: bool = False  # True: el valor embebido es el precio total, no el peso


FORMATO_PESO_DEFECTO = FormatoGS1()


@dataclass(frozen=True)
class ResultadoGS1:
    codigo_producto: str
    peso_kg: Decimal     # interpretación como peso (valor / 10**decimales_valor)
    valor_crudo: int     # los dígitos de valor como entero, sin escalar (sirve para modo precio)


def _digito_control_ean13(doce: str) -> int:
    suma = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(doce))
    return (10 - suma % 10) % 10


def es_peso_variable(codigo: str, formato: FormatoGS1 = FORMATO_PESO_DEFECTO) -> bool:
    """¿El código escaneado es un EAN-13 de peso variable (etiqueta de balanza)?"""
    return len(codigo) == 13 and codigo.isdigit() and codigo[0] in formato.prefijos


def decodificar_gs1(codigo: str, formato: FormatoGS1 = FORMATO_PESO_DEFECTO) -> ResultadoGS1:
    if len(codigo) != 13 or not codigo.isdigit():
        raise ValueError(f"EAN-13 inválido: {codigo!r}")
    if codigo[0] not in formato.prefijos:
        raise ValueError(f"prefijo {codigo[0]!r} no es de peso variable")
    if _digito_control_ean13(codigo[:12]) != int(codigo[12]):
        raise ValueError("dígito de control EAN-13 incorrecto")
    crudo = codigo[formato.ini_valor:formato.fin_valor]
    peso_kg = Decimal(crudo) / (Decimal(10) ** formato.decimales_valor)
    return ResultadoGS1(codigo[formato.ini_codigo:formato.fin_codigo], peso_kg, int(crudo))


class CodigoPesoGS1:
    """Adaptador LectorPeso: obtiene el peso de un código GS1 ya escaneado."""

    def __init__(self, codigo: str, formato: FormatoGS1 = FORMATO_PESO_DEFECTO) -> None:
        self._resultado = decodificar_gs1(codigo, formato)

    @property
    def codigo_producto(self) -> str:
        return self._resultado.codigo_producto

    def leer_peso(self) -> Decimal:
        return self._resultado.peso_kg
