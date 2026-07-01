from core.seguridad import hash_password, verificar


def test_verifica_password_correcta():
    h = hash_password("secreta123")
    assert verificar("secreta123", h) is True


def test_rechaza_password_incorrecta():
    h = hash_password("secreta123")
    assert verificar("otra", h) is False


def test_hashes_distintos_por_sal():
    assert hash_password("misma") != hash_password("misma")


def test_verificar_rechaza_formato_invalido():
    assert verificar("x", "no-es-un-hash") is False
