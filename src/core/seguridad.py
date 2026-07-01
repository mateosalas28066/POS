"""Hash y verificación de contraseñas. Python puro (stdlib)."""
from __future__ import annotations

import hashlib
import hmac
import secrets

_ALGO = "pbkdf2_sha256"
_ITERACIONES = 200_000


def hash_password(password: str) -> str:
    sal = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(sal), _ITERACIONES)
    return f"{_ALGO}${_ITERACIONES}${sal}${dk.hex()}"


def verificar(password: str, codificado: str) -> bool:
    try:
        algo, iteraciones, sal, hash_hex = codificado.split("$")
        if algo != _ALGO:
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(sal), int(iteraciones))
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(dk.hex(), hash_hex)
