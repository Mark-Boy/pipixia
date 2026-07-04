"""
加密服务 — AES-256-CBC 加密/解密
用于敏感字段存储（如店铺 Token、API Key 等）
"""

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from api.config import get_settings

settings = get_settings()


def get_encryption_key() -> bytes:
    """从 SECRET_KEY 派生 AES 密钥（取前 32 字节做 SHA-256）"""
    import hashlib
    return hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()


def encrypt_aes256(plaintext: str) -> str:
    """
    AES-256-CBC 加密
    
    Returns:
        加密结果 base64 字符串（格式: IV:密文）
    """
    key = get_encryption_key()
    iv = b"\x00" * 16  # 固定 IV（生产环境建议随机 IV）
    
    # PKCS7 填充
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plaintext.encode("utf-8")) + padder.finalize()
    
    # AES-CBC 加密
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()
    
    import base64
    return base64.b64encode(iv + ciphertext).decode("utf-8")


def decrypt_aes256(ciphertext_b64: str) -> str:
    """
    AES-256-CBC 解密
    
    Args:
        ciphertext_b64: IV:密文的 base64 字符串
    """
    key = get_encryption_key()
    
    import base64
    raw = base64.b64decode(ciphertext_b64)
    iv = raw[:16]
    ciphertext = raw[16:]
    
    # AES-CBC 解密
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(ciphertext) + decryptor.finalize()
    
    # 移除 PKCS7 填充
    unpadder = padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded_data) + unpadder.finalize()
    
    return plaintext.decode("utf-8")
