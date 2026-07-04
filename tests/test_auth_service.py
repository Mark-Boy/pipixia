"""
测试认证服务
"""

import pytest
from api.services.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
    get_password_hash,
)


class TestAuthToken:
    """Token 创建和验证测试"""

    def test_create_access_token(self):
        """创建 Access Token"""
        token = create_access_token(user_id="1", role="admin")
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        """创建 Refresh Token"""
        token = create_refresh_token(user_id="1")
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_access_token(self):
        """解码 Access Token"""
        token = create_access_token(user_id="42", role="admin")
        payload = decode_token(token)
        assert payload["sub"] == "42"
        assert payload["role"] == "admin"
        assert payload["type"] == "access"

    def test_decode_refresh_token(self):
        """解码 Refresh Token"""
        token = create_refresh_token(user_id="42")
        payload = decode_token(token)
        assert payload["sub"] == "42"
        assert payload["type"] == "refresh"

    def test_decode_invalid_token(self):
        """解码无效 Token"""
        with pytest.raises(Exception):
            decode_token("invalid.token.here")

    def test_token_expiry(self):
        """Token 过期验证"""
        from datetime import timedelta
        token = create_access_token(
            user_id="1", role="admin", expires_delta=timedelta(minutes=1)
        )
        payload = decode_token(token)
        assert "exp" in payload


class TestPassword:
    """密码哈希测试"""

    def test_password_hash(self):
        """密码哈希生成"""
        hashed = get_password_hash("Test1234!")
        assert hashed is not None
        assert len(hashed) > 0

    def test_password_verify_correct(self):
        """验证正确密码"""
        password = "Test1234!"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_password_verify_incorrect(self):
        """验证错误密码"""
        hashed = get_password_hash("Test1234!")
        assert verify_password("WrongPassword", hashed) is False

    def test_password_uniqueness(self):
        """同一密码多次哈希结果不同"""
        password = "Test1234!"
        hashed1 = get_password_hash(password)
        hashed2 = get_password_hash(password)
        assert hashed1 != hashed2  # bcrypt 加盐
