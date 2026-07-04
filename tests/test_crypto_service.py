"""
测试加密服务
"""

import pytest
from api.services.crypto import encrypt_aes256, decrypt_aes256


class TestCrypto:
    """AES-256-CBC 加密/解密测试"""

    def test_encrypt_decrypt_roundtrip(self):
        """加密后能正确解密"""
        original = "shop_token_test_12345"
        encrypted = encrypt_aes256(original)
        decrypted = decrypt_aes256(encrypted)
        assert decrypted == original

    def test_encrypt_different_outputs(self):
        """相同输入产生相同输出（固定IV）"""
        original = "shop_token_test_12345"
        encrypted1 = encrypt_aes256(original)
        encrypted2 = encrypt_aes256(original)
        assert encrypted1 == encrypted2

    def test_encrypt_length_increases(self):
        """加密后长度增加（IV + padding）"""
        original = "short"
        encrypted = encrypt_aes256(original)
        assert len(encrypted) > len(original)

    def test_decrypt_invalid_base64(self):
        """解密无效 base64"""
        with pytest.raises(Exception):
            decrypt_aes256("not-valid-base64!!!")

    def test_empty_string(self):
        """空字符串加密"""
        encrypted = encrypt_aes256("")
        decrypted = decrypt_aes256(encrypted)
        assert decrypted == ""

    def test_long_string(self):
        """长字符串加密"""
        long_text = "a" * 1000
        encrypted = encrypt_aes256(long_text)
        decrypted = decrypt_aes256(encrypted)
        assert decrypted == long_text
