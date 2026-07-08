# Shopee API 集成文档

> 基于 **Open API Developer Guide v2.1 (20220722)**

---

## 项目概述

跨境电商自动上架工具 — Shopee 平台集成

- ✅ 店铺信息获取 (OAuth 授权)
- ✅ 商品信息 (创建/更新/删除/列表/搜索)
- ✅ 自动采集 (1688/拼多多)
- ✅ 自动上传到 Shopee
- ✅ 库存同步
- ✅ 每分钟自动汇报进度
- ❌ **不包含报关功能**

---

## 技术栈

- **Python 3.11+**
- **FastAPI** — REST API
- **SQLAlchemy** — ORM
- **Shopee Open API v2.0** — 官方 API

---

## 架构

```
┌─────────────────────────────────────────────────────────┐
│                    API Server (FastAPI)                   │
│                                                         │
│  /api/v1/shopee/*          Shopee API 路由               │
│  /api/v1/shops             店铺管理                      │
│  /api/v1/products          商品管理                      │
│  /api/v1/listings          上架记录                      │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                  Services Layer                           │
│                                                         │
│  shopee_v2.py   — Shopee API v2.0 客户端                │
│  shopee_sync.py — 自动采集 + 上传服务                    │
│  scheduler.py   — 定时调度器 (每分钟)                    │
│  translator.py  — AI 翻译 (泰语)                        │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                   Data Models                             │
│                                                         │
│  Shop        — 店铺 (Token 加密存储)                    │
│  Product     — 商品 (中/泰双语)                         │
│  Listing     — 上架记录                                  │
│  Translate   — 翻译记录                                  │
│  ProductVariation — 规格/变体                           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## API 端点

### 店铺相关

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/shopee/shop-info?shop_id=1` | 获取店铺信息 |
| POST | `/api/v1/shopee/authorize?shop_id=xxx` | 生成 OAuth 授权链接 |
| POST | `/api/v1/shopee/oauth/callback` | OAuth 回调处理 |

### 商品相关

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/shopee/products` | 获取商品列表 |
| GET | `/api/v1/shopee/listings` | 获取上架记录 |

### 同步相关

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/shopee/list` | 自动采集 + 上传 |
| POST | `/api/v1/shopee/sync-stock` | 同步库存到 Shopee |
| POST | `/api/v1/shopee/sync-products` | 从 Shopee 同步商品列表 |
| GET | `/api/v1/shopee/status` | 获取同步状态 |

### 调度器

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/shopee/start-scheduler` | 启动调度器 |
| GET | `/api/v1/shopee/scheduler/status` | 调度器状态 |
| POST | `/api/v1/shopee/scheduler/stop` | 停止调度器 |

---

## OAuth 授权流程

根据文档 Step 5.3:

1. 调用 `POST /authorize?shop_id=xxx&callback_url=yyy` 获取授权链接
2. 用户点击授权链接，用 Shopee 店铺账号登录
3. 回调 `/oauth/callback?shop_id=xxx&code=xxx&state=xxx`
4. 服务端用 code 换取 access_token
5. 保存 access_token (AES-256 加密) 到数据库

> ⚠️ 授权有效期 **365 天**，到期需重新授权

---

## 自动采集 + 上传流程

```
1. 采集商品 (1688/拼多多)
   ↓
2. AI 翻译标题/描述 → 泰语
   ↓
3. 价格换算 (CNY → THB) + 利润计算
   ↓
4. 上传图片到 Shopee
   ↓
5. 创建/更新 Shopee 商品
   ↓
6. 记录上架结果
```

---

## 调度器

- **运行频率**: 每分钟
- **执行内容**:
  - 自动上架待处理商品
  - 同步库存到 Shopee
  - 每 5 分钟同步商品列表
  - 发送进度报告 (控制台 + Telegram)

---

## 环境变量

```bash
# Shopee API
SHOPEE_APP_KEY=your_app_key_here
SHOPEE_SECRET=your_secret_here
SHOPEE_MARKET_ID=146          # 146=TH, 1=VN, 2=SG, 3=MY, 6=PH

# 开关
SHOPEE_SIGNATURE_ENABLED=false

# 告警 (可选)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

---

## 沙盒测试

所有 API 默认使用沙盒环境 (`test-stable.shopee.com`)

- 测试店铺: 最多 8 个本地 + 9 个跨境
- OTP: `123456`
- 卖家后台: `https://seller.test-stable.shopee.co.th/`

---

## 测试

```bash
cd api
# 运行测试
python -m pytest tests/test_shopee_v2.py -v

# 运行所有测试
python -m pytest tests/ -v
```

---

## 不包含的功能

- ❌ 报关功能 (Customs Declaration)
- ❌ 面单打印 (Label Printing) — 基础版
- ❌ 营销工具 (Campaign Management)
