# 📁 文件说明

> 项目文件路径与对应说明索引

---

## 目录结构

```
pipixia/
├── README.md                  # 项目总览
├── .env.example               # 环境变量模板
├── docker-compose.yml         # Docker 编排配置
├── Makefile                   # 构建命令
│
├── api/                       # FastAPI 后端
│   ├── main.py                # FastAPI 应用入口，路由注册
│   ├── config.py              # Pydantic Settings 配置管理
│   ├── database.py            # SQLAlchemy 异步数据库会话
│   ├── services/              # 业务逻辑层
│   │   ├── auth.py            # JWT 认证（Token 创建/验证/刷新/密码哈希）
│   │   └── crypto.py          # AES-256 加密（店铺 Token 加解密）
│   ├── models/                # SQLAlchemy 数据模型
│   │   ├── __init__.py        # 模型统一导出
│   │   ├── user.py            # 用户模型
│   │   ├── shop.py            # 店铺模型
│   │   ├── product.py         # 商品模型
│   │   ├── listing.py         # 上架记录模型
│   │   ├── translate.py       # 翻译记录模型
│   │   ├── risk_log.py        # 风控日志模型
│   │   └── profit_calibration.py  # 利润校准模型
│   ├── schemas/               # Pydantic 请求/响应 Schema
│   │   ├── __init__.py        # Schema 统一导出
│   │   ├── user.py            # 用户 Schema
│   │   ├── shop.py            # 店铺 Schema
│   │   ├── product.py         # 商品 Schema
│   │   └── audit.py           # 审核 Schema
│   └── routers/               # API 路由层
│       ├── __init__.py        # 路由统一导出
│       ├── auth.py            # 认证路由（登录/注册/刷新/登出）
│       ├── shops.py           # 店铺 CRUD 路由
│       ├── products.py        # 商品 CRUD + 导入 + 翻译 + 利润核算
│       ├── audit.py           # 审核队列 + 审核操作
│       ├── listings.py        # 上架记录 CRUD + 重试
│       ├── settings.py        # 系统设置 + 风控词库
│       ├── reports.py         # 日报 + 财务 + 利润校准报告
│       ├── media.py           # 图片上传/下载/删除
│       └── webhooks.py        # Shopee Webhook 接收
│
├── worker/                    # Celery Worker
│   ├── celery_app.py          # Celery 应用配置
│   └── tasks.py               # 任务定义（翻译/上架/同步等）
│
├── migrations/                # Alembic 数据库迁移
│   ├── env.py                 # 迁移环境配置
│   └── versions/
│       └── 0001_initial_migration.py  # 初始表结构迁移
│
├── scripts/
│   └── init_db.py             # 数据库初始化脚本
│
├── config/                    # 配置文件
│   ├── settings.yaml          # 应用设置
│   ├── llm.yaml               # LLM 配置
│   ├── categories.yaml        # 类目映射
│   ├── risk_words.json        # 风控敏感词库
│   └── prompts.yaml           # AI Prompt 模板
│
├── tests/                     # 单元测试
│   ├── test_auth_service.py   # 认证服务测试
│   └── test_crypto_service.py # 加密服务测试
│
├── 开发任务清单_P0-P1.md      # P0-P1 任务清单
├── 开发优先级计划.md          # 开发优先级计划
└── 文件说明/                  # 本目录
    ├── README.md              # 本文件（文件索引）
```

---

## 核心文件速查

| 文件路径 | 功能模块 | 关键内容 |
|----------|----------|----------|
| `api/main.py` | 应用入口 | FastAPI 实例、CORS 中间件、所有路由注册 |
| `api/services/auth.py` | JWT 认证 | create_access_token, decode_token, get_password_hash, verify_password |
| `api/services/crypto.py` | 加密服务 | encrypt_aes256, decrypt_aes256 |
| `api/database.py` | 数据库 | AsyncSession 会话管理 |
| `api/config.py` | 配置 | Settings 类，加载 .env 环境变量 |
| `api/routers/auth.py` | 认证路由 | POST /login, /register, /refresh, /logout, /me |
| `api/routers/shops.py` | 店铺路由 | CRUD + 解密 Token 查询 |
| `api/routers/products.py` | 商品路由 | CRUD + 导入 + 翻译触发 + 利润核算 |
| `api/routers/audit.py` | 审核路由 | 审核队列 + 通过/拒绝 + 批量操作 |
| `api/routers/listings.py` | 上架路由 | 上架记录 CRUD + 重试 |
| `api/routers/webhooks.py` | Webhook | Shopee 订单/聊天/评价/库存事件接收 |
| `api/routers/reports.py` | 报表路由 | 日报 + 财务对账 + 利润校准 + Dashboard 汇总 |
| `api/routers/media.py` | 媒体路由 | 图片上传（OSS） + 下载 + 删除 |
| `api/routers/settings.py` | 设置路由 | 系统配置 + 风控词库管理 |
| `worker/tasks.py` | 任务队列 | 翻译/上架/图片处理/库存同步/Celery 定时任务 |
| `migrations/versions/0001_initial_migration.py` | 数据库迁移 | 7 张表的 DDL 创建 |
| `scripts/init_db.py` | 初始化 | 创建超级管理员 + 加载默认配置 |
