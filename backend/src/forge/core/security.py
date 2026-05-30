"""Utilidades de seguridad (cifrado de credenciales sensibles)."""

from cryptography.fernet import Fernet, InvalidToken

from forge.core.config import get_settings


def encrypt_value(plaintext: str) -> str:
    """
    Cifrar un valor con Fernet.

    Args:
        plaintext: Texto plano a cifrar

    Returns:
        Texto cifrado como string (base64)
    """
    settings = get_settings()
    f = Fernet(settings.encryption_key.encode())
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """
    Descifrar un valor con Fernet.

    Args:
        ciphertext: Texto cifrado (base64)

    Returns:
        Texto plano

    Raises:
        InvalidToken: Si la clave es incorrecta o el texto está corrupto
    """
    settings = get_settings()
    f = Fernet(settings.encryption_key.encode())
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken as e:
        raise ValueError("No se pudo descifrar: clave inválida o texto corrupto") from e


def generate_encryption_key() -> str:
    """
    Generar una nueva clave de cifrado Fernet.

    Use esta función para generar el valor de ENCRYPTION_KEY en .env:

    ```python
    from forge.core.security import generate_encryption_key
    print(generate_encryption_key())
    ```

    Returns:
        Clave de cifrado como string (base64)
    """
    return Fernet.generate_key().decode()
