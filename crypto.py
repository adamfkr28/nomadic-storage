from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import os

def generate_key():
    """Bikin kunci 256-bit (32 byte) acak."""
    return os.urandom(32)

def derive_key_from_password(password, salt=None):
    """
    Turunin kunci 256-bit dari password pake PBKDF2.
    Kalau salt gak dikasih, bikin salt baru (16 byte).
    Return: (key, salt)
    """
    if salt is None:
        salt = os.urandom(16)

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,              # 256-bit
        salt=salt,
        iterations=100_000,     # 100 ribu iterasi
        backend=default_backend()
    )

    key = kdf.derive(password.encode("utf-8"))
    return key, salt

def encrypt_shard(data, key):
    """Enkripsi shard pakai AES-256-GCM (authenticated encryption)."""
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, data, None)
    return nonce + ciphertext

def decrypt_shard(encrypted_data, key):
    """Dekripsi shard pakai AES-256-GCM. Gagal kalau kunci salah / data korup."""
    nonce = encrypted_data[:12]
    ciphertext = encrypted_data[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)