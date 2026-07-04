# 测试文档

## 运行测试

```bash
# 安装测试依赖
pip install pytest

# 运行全部测试
pytest

# 运行指定模块
pytest tests/test_auth_service.py
pytest tests/test_crypto_service.py
```

## 测试覆盖范围

| 模块 | 文件 | 覆盖内容 |
|------|------|----------|
| 认证服务 | test_auth_service.py | Token 创建/验证、密码哈希、过期 |
| 加密服务 | test_crypto_service.py | AES-256 加解密、空字符串、长文本 |

## 后续测试计划

- [ ] 路由层集成测试（auth, shops, products）
- [ ] Schema 验证测试
- [ ] Celery 任务测试
- [ ] Docker 集成测试
