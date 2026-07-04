# pipixia 项目开发架构与设计文档（完整版）  
   
**项目名称**：pipixia — 跨境电商自动上架工具    
**文档版本**：V4.0-ARCH | **更新日期**：2026-07-04    
**编制目的**：作为研发团队的实施蓝图，包含架构设计、技术选型、数据模型、API规范、部署运维等全部细节。  
   
---  
   
## 目录  
   
1. [项目概述](#1-项目概述)  
2. [系统总体架构](#2-系统总体架构)  
3. [技术栈选型](#3-技术栈选型)  
4. [模块架构详述](#4-模块架构详述)  
5. [数据架构（完整设计）](#5-数据架构完整设计)  
6. [AI 工作流架构（LangGraph）](#6-ai-工作流架构langgraph)  
7. [API 架构设计](#7-api-架构设计)  
8. [定时任务与容错机制](#8-定时任务与容错机制)  
9. [安全架构](#9-安全架构)  
10. [测试策略](#10-测试策略)  
11. [部署架构与硬件资源](#11-部署架构与硬件资源)  
12. [成本估算（参考）](#12-成本估算参考)  
13. [数据备份与灾难恢复](#13-数据备份与灾难恢复)  
14. [监控与告警体系](#14-监控与告警体系)  
15. [开发阶段规划（含任务清单）](#15-开发阶段规划含任务清单)  
16. [技术依赖清单](#16-技术依赖清单)  
17. [项目目录结构](#17-项目目录结构)  
   
---  
   
## 1. 项目概述  
   
### 1.1 项目定位  
跨境电商自动上架工具，打通 **1688/拼多多 → LangGraph AI 编排 → 智能上架 → 财务风控闭环** 全链路，实现“一人一店”的轻量化跨境运营。  
   
### 1.2 版本更新说明

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| V4.0 | 2026-07-04 | 初始版本 |
| V4.1 | 2026-07-04 | 1. LangGraph 状态持久化（PostgresSaver）<br>2. 图片翻译主图优先 + Celery 分片<br>3. Shopee 图片上传异步模式明确<br>4. 翻译缓存近重复检测（simhash/MinHash）<br>5. 移除 APScheduler，统一 Celery Beat<br>6. 类目错放规则引擎 + category_mapping 表<br>7. site_config 多站点扩展表<br>8. 结构化错误码体系（模块化）<br>9. 依赖版本锁定（生产环境）<br>10. Next.js SSR/SSG 策略 |

### 1.3 核心目标  
| 目标 | 说明 |  
|------|------|  
| 自动选品 | 从 1688/拼多多采集热销品，支持销量排行、搜索趋势、竞品监控 |  
| AI 翻译优化 | 使用 LangGraph 编排有向图工作流，将中文商品信息转化为泰语本地化内容 |  
| 智能上架 | 自动上架到 Shopee 泰国站，支持异步图片处理与重试回滚 |  
| 财务防亏损 | 利润核算 + 熔断机制 + 历史利润校准 |  
| 合规防封店 | 品牌侵权拦截、违禁词过滤、类目错放检测 |  
   
### 1.4 关键约束
- **目标站点**：Shopee 泰国站（预留多站点扩展能力，通过 site_config 表支持）
- **货源平台**：1688、拼多多（优先官方 API，爬虫备选）
- **类目限制**：全品类，排除女装、危险品类目、敏感类目
- **安全约束**：品牌侵权拦截、违禁词过滤、利润红线熔断
- **合规优先**：数据获取遵守平台协议，不爬取非公开数据
   
---  
   
## 2. 系统总体架构  
   
```  
┌─────────────────────────────────────────────────────────────────────────┐  
│                        Web Dashboard (Next.js)                         │  
│  选品 | 审核 | 财务看板 | 风控日志 | 配置 | 店铺管理                    │  
└────────────────────────────┬────────────────────────────────────────────┘  
                             │ HTTP/REST / WebSocket  
┌────────────────────────────▼────────────────────────────────────────────┐  
│                   API Gateway (FastAPI + Nginx)                         │  
│  路由 / 鉴权 / 限流 / 日志 / IP白名单 / Webhook接收                     │  
└──┬──────────┬──────────┬──────────┬──────────┬──────────────────────────┘  
   │          │          │          │          │  
   ▼          ▼          ▼          ▼          ▼  
┌───────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐  
│数据采集│ │LangGraph│ │上架执行│ │财务风控│ │监控报表  │  
│(含反爬)│ │AI 编排  │ │(含重试)│ │(含熔断)│ │模块      │  
└───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘ └────┬─────┘  
    │         │         │         │           │  
    └─────────┴─────────┴─────────┴───────────┘  
                             │  
┌────────────────────────────▼────────────────────────────────────────────┐  
│                       Celery Worker 集群                                  │  
│              (OCR / 图片合成 / 批量上架 / 风控检查)                       │  
└────────────────────────────┬────────────────────────────────────────────┘  
                             │  
┌──────────────────┬─────────────────┬──────────────────────┐  
│  PostgreSQL 16   │   Redis 7       │  对象存储            │  
│  (持久化存储)    │ (缓存/队列/限流)│  (OSS/S3/MinIO)      │  
│                  │                 │  (图片/报表存储)     │  
└──────────────────┴─────────────────┴──────────────────────┘  
                             │  
┌─────────────────────────────────────────────────────────────────────────┐  
│  外部服务：1688 API / 拼多多 API / Shopee API / LLM (Qwen/DashScope)   │  
│  反爬辅助：代理池 / 打码平台 / Playwright                               │  
└─────────────────────────────────────────────────────────────────────────┘  
```  
   
---  
   
## 3. 技术栈选型  
   
| 层级 | 技术 | 版本要求 | 说明 |  
|------|------|----------|------|  
| **后端 API** | Python + FastAPI | >=0.104.1 | 高性能异步，适合高并发 I/O |  
| **AI 编排** | LangChain + LangGraph | >=0.1.0 / >=0.0.30 | 有向图工作流，支持条件分支和状态管理 |
| **LangGraph 检查点** | PostgresSaver（异步） | >=0.0.30 | PostgreSQL 持久化工作流状态，支持中断恢复 |
| **LLM** | DashScope(通义) / 本地 Qwen | - | 翻译、摘要、策略生成 |
| **数据库** | PostgreSQL | 16 | 持久化，支持 JSONB |  
| **缓存/队列** | Redis + Celery | 7 / 5 | 任务队列、分布式锁、限流 |  
| **对象存储** | 阿里云 OSS / AWS S3 / MinIO | - | 商品图片存储，CDN 加速 |  
| **OCR** | PaddleOCR | >=2.7.0.3 | 图片文字提取（中/泰语） |  
| **前端** | Next.js + TailwindCSS + Shadcn/UI | 14.x + 18.x + 3.x | Web Dashboard |  
| **部署** | Docker + Docker Compose | - | 容器化部署 |  
| **监控** | Prometheus + Grafana | - | 指标可视化 |  
   
---  
   
## 4. 模块架构详述  
   
| 模块 | 职责 | 技术实现 | 所属路径 |  
|------|------|----------|----------|  
| 数据采集 | 从货源平台获取商品信息 | 官方 API + Playwright 爬虫 + 代理池 | `api/services/crawler/` |  
| AI 翻译编排 | 翻译、风控、SEO 有向图工作流 | LangGraph 状态图 | `api/services/ai_engine/` |  
| 图片处理 | OCR 提取、翻译、合成 | PaddleOCR + OpenCV | `worker/tasks.py` |  
| 财务核算 | 利润计算、熔断、校准 | 动态公式 + 历史学习 | `api/services/finance/` |  
| 风控模块 | 品牌侵权、违禁词、类目校验 | 正则/模糊匹配 + OCR Logo 检测 | `api/services/risk/` |  
| 上架执行 | Shopee API 对接、重试回滚 | httpx + 异步轮询 | `api/services/listing/` |  
| 审核模块 | 人工/自动审核队列 | API + Dashboard | `api/routers/audit.py` |  
| 监控报表 | 数据可视化、对账 | Pandas + 报表模板 | `api/services/report/` |  
| 对象存储 | 图片/报表存储 | OSS/S3/MinIO 统一接口 | `api/services/storage/` |  
| 后台任务 | OCR/批量上架/定时同步 | Celery 任务队列 | `worker/` |  
| Web Dashboard | 可视化操作界面 | Next.js + TailwindCSS | `dashboard/` |  
   
---  
   
## 5. 数据架构（完整设计）  
   
### 5.1 核心实体关系图  
```  
users ──< shops >── products >── listings >── (shopee_item_id)  
  │                       │                      │  
  │                       ├──> product_variations  
  │                       ├──> image_assets  
  │                       ├──> risk_logs  
  │                       └──> translates  
  │  
  ├──> audit_logs  
  │  
  └──> orders >── shipments  
                   │  
                   └──> transactions  
  │  
  └──> profit_calibration  
```  
   
### 5.2 核心表完整字段定义  
   
#### `users`（用户）  
| 字段 | 类型 | 说明 |  
|------|------|------|  
| id | UUID | PK |  
| username | VARCHAR(64) | 唯一 |  
| email | VARCHAR(128) | 唯一 |  
| password_hash | VARCHAR(128) | bcrypt |  
| role | ENUM('admin','operator','viewer') | 权限角色 |  
| is_active | BOOLEAN | 是否启用 |  
| last_login_at | TIMESTAMP | 最后登录时间 |  
| created_at, updated_at | TIMESTAMP | 审计 |  
   
#### `shops`（店铺）  
| 字段 | 类型 | 说明 |  
|------|------|------|  
| id | UUID | PK |  
| user_id | UUID | FK → users |  
| shop_name | VARCHAR(128) | 店铺昵称 |  
| platform | ENUM('shopee_th','shopee_vn',...) | 平台 |  
| shop_token_encrypted | TEXT | AES-256 加密的 Token |  
| shop_id | VARCHAR(64) | 平台分配的店铺ID |  
| is_active | BOOLEAN | 是否启用 |  
| config_json | JSONB | 默认运费模板、类目等 |  
| created_at, updated_at | TIMESTAMP | 审计 |  
   
#### `products`（商品）  
| 字段 | 类型 | 说明 |  
|------|------|------|  
| id | UUID | PK |  
| shop_id | UUID | FK → shops |  
| source_platform | ENUM('1688','pdd') | 货源平台 |  
| source_item_id | VARCHAR(64) | 货源商品ID |  
| title_zh, title_th | TEXT | 中/泰语标题 |  
| description_zh, description_th | TEXT | 中/泰语描述 |  
| category_id | VARCHAR(32) | Shopee 类目ID |  
| images_oss_keys | JSONB | 所有图片的 OSS key 列表 |  
| price_cny, price_thb | DECIMAL(12,2) | 成本价/售价 |  
| cost_cny | DECIMAL(12,2) | 总成本（含运费） |  
| profit_margin | DECIMAL(5,2) | 预估利润率% |  
| risk_status | ENUM('pass','block','manual') | 风控状态 |  
| status | ENUM('pending','reviewed','listing','active','paused','removed') | 商品状态 |  
| created_at, updated_at | TIMESTAMP | 审计 |  
   
#### `listings`（上架记录）  
| 字段 | 类型 | 说明 |  
|------|------|------|  
| id | UUID | PK |  
| product_id | UUID | FK → products |  
| shop_id | UUID | FK → shops |  
| shopee_item_id | VARCHAR(64) | Shopee 商品ID（唯一） |  
| shopee_status | VARCHAR(32) | Shopee 返回的状态 |  
| listing_price_thb | DECIMAL(12,2) | 实际上架价格 |  
| stock | INT | 库存数量 |  
| variation_data | JSONB | 变体映射关系 |  
| audit_status | ENUM('pending','approved','rejected') | 审核状态 |  
| audit_comment | TEXT | 审核备注 |  
| listing_mode | ENUM('manual_review','auto') | 上架模式 |  
| retry_count | INT | 当前重试次数 |  
| last_error | TEXT | 最近错误信息 |  
| created_at, updated_at | TIMESTAMP | 审计 |  
   
#### `translates`（翻译记录/缓存）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | PK |
| product_id | UUID | FK → products |
| translate_type | ENUM('title','description','keyword','image_ocr') | 类型 |
| source_text_hash | VARCHAR(64) | 源文本 SHA256（精确匹配） |
| source_simhash | VARCHAR(64) | 源文本 simhash（近重复检测） |
| source_text | TEXT | 原文 |
| target_text | TEXT | 译文 |
| similarity_score | DECIMAL(5,4) | 相似度（仅 simhash 命中时记录，范围 0-1） |
| source_image_url | TEXT | 原图URL（仅图片翻译） |
| target_image_url | TEXT | 译后图URL（仅图片翻译） |
| status | ENUM('pending','success','failed') | 状态 |
| confidence_score | DECIMAL(3,2) | 置信度0-1 |
| created_at, updated_at | TIMESTAMP | 审计 |

**翻译缓存策略升级**：
- **精确匹配**：SHA256 完全相同的文本直接复用
- **近重复检测**：simhash 相似度 ≥0.90 时，复用历史译文并标注 `similarity_score`
- **MinHash 加速**：对大规模翻译缓存使用 MinHash + LSH（Locality-Sensitive Hashing）加速近重复检测
- **缓存淘汰**：LRU 策略，超过 10 万条记录的缓存自动淘汰最旧条目
   
#### `product_variations`（商品变体）  
| 字段 | 类型 | 说明 |  
|------|------|------|  
| id | UUID | PK |  
| product_id | UUID | FK → products |  
| variation_name | VARCHAR(64) | 规格名（颜色/尺寸） |  
| variation_value | VARCHAR(64) | 规格值（红色/M） |  
| sku_code | VARCHAR(64) | 唯一SKU |  
| price_thb | DECIMAL(12,2) | 变体价格 |  
| stock | INT | 变体库存 |  
| image_url | TEXT | 变体图片URL |  
| shopee_variation_id | VARCHAR(64) | Shopee 变体ID |  
| created_at | TIMESTAMP | 审计 |  
   
#### `risk_logs`（风控日志）  
| 字段 | 类型 | 说明 |  
|------|------|------|  
| id | UUID | PK |  
| product_id | UUID | FK → products |  
| risk_type | ENUM('brand','word','category','image') | 风险类型 |  
| risk_detail | TEXT | 具体说明（命中词、品牌等） |  
| action_taken | ENUM('block','manual','warning') | 处理动作 |  
| created_at | TIMESTAMP | 发生时间 |  
   
#### `profit_calibration`（利润校准）  
| 字段 | 类型 | 说明 |  
|------|------|------|  
| id | UUID | PK |  
| shop_id | UUID | FK → shops |  
| category_id | VARCHAR(32) | 类目ID（可为空） |  
| estimated_profit | DECIMAL(12,2) | 预估利润 |  
| actual_profit | DECIMAL(12,2) | 实际利润（来自订单） |  
| deviation | DECIMAL(5,2) | 偏差率 (%) |  
| created_at | TIMESTAMP | 记录时间 |  
   
#### 新增表：`category_mapping`（类目映射规则表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | PK |
| source_platform | ENUM('1688','pdd') | 货源平台 |
| source_keywords | TEXT[] | 关键词数组（用于规则匹配） |
| shopee_category_id | VARCHAR(32) | Shopee 类目ID |
| shopee_category_path | TEXT | 类目路径（如 "手机 > 配件 > 手机壳"） |
| confidence | DECIMAL(3,2) | 匹配置信度 |
| is_active | BOOLEAN | 是否启用 |
| created_at, updated_at | TIMESTAMP | 审计 |

**用途**：Phase 2 MVP 阶段使用规则引擎进行类目错放检测。通过关键词映射判断商品是否放错类目。

#### 新增表：`site_config`（多站点配置表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | PK |
| site_code | VARCHAR(16) | 站点代码（shopee_th / shopee_vn / shopee_ph） |
| site_name | VARCHAR(64) | 站点名称 |
| currency | VARCHAR(8) | 基础货币（THB/USD） |
| exchange_rate_cny | DECIMAL(10,6) | CNY 汇率 |
| commission_rate | DECIMAL(5,4) | 平台佣金率 |
| category_mapping_json | JSONB | 类目映射表（含类目树） |
| shipping_template_json | JSONB | 默认运费模板 |
| risk_words_json | JSONB | 站点特有违禁词库 |
| created_at, updated_at | TIMESTAMP | 审计 |

**用途**：支持多站点扩展，各站点独立配置汇率、佣金、类目、违禁词。

#### 其他表（简列）
- `competitors`：竞品跟踪
- `keywords`：关键词库
- `image_assets`：图片元数据
- `orders`、`shipments`、`transactions`：订单物流财务
- `settings`：系统配置（JSON）
- `audit_logs`、`error_logs`：审计与错误日志
   
### 5.3 索引策略
```sql
-- 商品表
CREATE INDEX idx_products_shop_status ON products (shop_id, status);
CREATE INDEX idx_products_risk ON products (risk_status);
CREATE INDEX idx_products_source ON products (source_platform, source_item_id);
-- 上架记录
CREATE INDEX idx_listings_product ON listings (product_id);
CREATE INDEX idx_listings_shopee ON listings (shopee_item_id);
-- 风控日志
CREATE INDEX idx_risk_logs_product ON risk_logs (product_id);
CREATE INDEX idx_risk_logs_created ON risk_logs (created_at);
-- 翻译缓存
CREATE INDEX idx_translates_hash ON translates (source_text_hash);
CREATE INDEX idx_translates_simhash ON translates (source_simhash);
-- 利润校准
CREATE INDEX idx_profit_calibration_shop ON profit_calibration (shop_id, created_at);
-- 类目映射（Gin 索引支持数组查询）
CREATE INDEX idx_category_mapping_keywords ON category_mapping USING gin (source_keywords);
CREATE INDEX idx_category_mapping_active ON category_mapping (is_active, source_platform);
-- 站点配置
CREATE UNIQUE INDEX idx_site_config_code ON site_config (site_code);
```
   
### 5.4 数据加密策略  
| 数据类型 | 加密方式 | 说明 |  
|----------|----------|------|  
| 用户密码 | bcrypt | 不可逆哈希 |  
| 店铺 Token/API Key | AES-256-CBC | 可逆加密，密钥从环境变量读取 |  
| 传输层 | TLS 1.3 | 强制启用 |  
| 请求签名 | HMAC-SHA256 + nonce（Redis TTL 300s） | 防重放攻击 |  
   
---  
   
## 6. AI 工作流架构（LangGraph）  
   
### 6.1 状态机定义

#### 6.1.1 TranslationState（工作流状态）

```python
from typing import TypedDict, Annotated
import operator

class TranslationState(TypedDict):
    product_id: str
    title_zh: str
    description_zh: str
    title_th: str
    description_th: str
    keywords_th: list[str]
    selling_points: list[str]
    confidence_score: float
    risk_flag: bool
    risk_reason: str
    cache_hit: bool
    similarity_score: float          # simhash 相似度（仅缓存命中时）
    model_used: str                  # "qwen-72b" / "qwen-1.8b" / "cached"
    seo_score: float
    errors: list[str]
    checkpoint_id: str | None        # LangGraph 检查点 ID（用于持久化恢复）
    workflow_run_id: str             # 工作流运行 ID（唯一追踪）
```

#### 6.1.2 状态持久化方案

**问题**：LangGraph 默认使用 `MemorySaver`（内存），Worker 重启或 LLM 调用超时时状态丢失。

**解决方案**：使用 `PostgresSaver` 持久化 LangGraph 状态到 PostgreSQL。

```python
from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy import create_engine
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# 从 SQLAlchemy 连接池获取连接
engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)

# 初始化 PostgresSaver（推荐异步方式）
async def get_checkpointer():
    async with AsyncPostgresSaver.from_conn_string(DATABASE_URL) as saver:
        await saver.setup()  # 创建检查点表
        return saver

# 在 LangGraph 工作流中注入检查点
from langgraph.graph import StateGraph, END

def build_graph():
    workflow = StateGraph(TranslationState)
    
    # ... 添加节点 ...
    
    # 关键：编译时传入检查点
    graph = workflow.compile(
        checkpointer=AsyncPostgresSaver.from_conn_string(DATABASE_URL),
        # 允许中断恢复
        interrupt_before=["quality_eval"] if needs_manual_review else []
    )
    return graph
```

**持久化表结构（PostgresSaver 自动创建）**：
| 字段 | 说明 |
|------|------|
| `thread_id` | 线程 ID（对应 product_id） |
| `checkpoint_ns` | 命名空间（对应翻译类型） |
| `checkpoint_id` | 检查点唯一 ID |
| `parent_checkpoint_id` | 父检查点 ID（用于恢复链） |
| `checkpoint` | JSONB 格式的工作流状态快照 |
| `metadata` | 元数据（创建时间、来源等） |
| `writes` | 写入记录（用于事件追溯） |

**恢复机制**：
1. 工作流中断时，PostgresSaver 自动保存当前状态到 `checkpoint` 表
2. Worker 重启后，通过 `thread_id` 查询最近的 `checkpoint` 恢复状态
3. 从最后一个检查点继续执行，避免重复调用 LLM（节省 Token）
   
### 6.2 工作流节点图  
```  
[start]  
   │  
   ▼  
┌──────────┐  
│ 缓存检查  │ ← Hash 匹配，相似度>90% 直接复用历史翻译  
└────┬─────┘  
     │ 未命中  
     ▼  
┌──────────┐  
│ 风控预检  │ ← 品牌词/违禁词拦截（先拦截再翻译）  
└────┬─────┘  
     │ 通过  
     ▼  
┌──────────┐  
│ 翻译调度  │ ← 核心卖点→大模型(Qwen-72B) / 普通描述→轻量模型(Qwen-1.8B)  
└────┬─────┘  
     ▼  
┌──────────┐  
│泰语本地化 │ ← 加入泰国电商常用语料库  
└────┬─────┘  
     ▼  
┌──────────┐  
│ SEO 优化  │ ← 标题关键词密度、描述卖点提炼  
└────┬─────┘  
     ▼  
┌──────────┐  
│质量评估  │ ← 置信度≥85% 通过，否则标记人工审核  
└────┬─────┘  
     ▼  
[end] → 优化后的商品数据  
```  
   
### 6.3 异常处理  
| 异常 | 处理 |  
|------|------|  
| 风控拦截 | 记录 risk_logs，阻断上架 |  
| 翻译置信度低 | 标记人工审核 |  
| LLM 不可用 | 降级使用缓存或保留中文（标记） |  
| 缓存命中 | 直接输出，跳过后续节点 |  
   
---  
   
## 7. API 架构设计  
   
### 7.1 通用规范  
- **基础路径**：`/api/v1`  
- **鉴权**：Bearer JWT（Access Token 2h，Refresh Token 7d）  
- **响应格式**：`{"code":0, "message":"success", "data":{}, "timestamp":xxx}`  
- **错误码**：见 7.4 节  
   
### 7.2 核心 API 端点完整列表  
   
#### 认证  
| 方法 | 路径 | 说明 |  
|------|------|------|  
| POST | `/api/auth/login` | 登录 |  
| POST | `/api/auth/refresh` | 刷新 Token |  
| POST | `/api/auth/logout` | 登出（黑名单） |  
   
#### 店铺管理  
| 方法 | 路径 | 说明 |  
|------|------|------|  
| GET | `/api/shops` | 店铺列表 |  
| POST | `/api/shops` | 添加店铺（加密Token） |  
| PUT | `/api/shops/{id}` | 更新店铺 |  
| DELETE | `/api/shops/{id}` | 删除店铺 |  
   
#### 商品管理  
| 方法 | 路径 | 说明 |  
|------|------|------|  
| GET | `/api/products` | 商品列表（分页、筛选） |  
| POST | `/api/products` | 导入商品（URL或手动） |  
| GET | `/api/products/{id}` | 商品详情 |  
| PUT | `/api/products/{id}` | 更新商品信息 |  
| POST | `/api/products/{id}/translate` | **触发 LangGraph 翻译工作流** |  
| POST | `/api/products/{id}/finance/check` | **手动利润核算** |  
| DELETE | `/api/products/{id}` | 删除商品（软删除） |  
   
#### 审核队列  
| 方法 | 路径 | 说明 |  
|------|------|------|  
| GET | `/api/audit` | 审核队列（分页） |  
| POST | `/api/audit/{id}/approve` | 审核通过（可带备注） |  
| POST | `/api/audit/{id}/reject` | 审核拒绝 |  
| POST | `/api/audit/batch` | 批量审核 |  
   
#### 上架管理
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/listings` | 创建上架任务 |
| GET | `/api/listings` | 上架记录（分页） |
| GET | `/api/listings/{id}` | 上架详情 |
| POST | `/api/listings/{id}/retry` | 手动重试上架 |
| DELETE | `/api/listings/{id}` | 取消上架任务（回滚已上传图片） |
| GET | `/api/listings/{id}/status` | 查询上架状态（轮询用） |

**Shopee API 图片上传流程（异步模式）**：

Shopee 提供两种图片上传模式，本系统统一使用 **异步模式（模式 B）**：

```
模式 A（同步）：
  POST /api/v1/media/upload → 直接返回 image_id
  缺点：大图片容易超时（>10s），不适合批量上传

模式 B（异步）【推荐使用】：
  1. POST /api/v1/media/upload
     请求体：{"shop_id": "xxx", "image": "base64"}
     响应：{"task_id": "abc-123", "status": "processing"}
  
  2. 异步轮询（最多 5 次，指数退避间隔）
     GET /api/v1/media/task/{task_id}
     
     第1次：等待 5s → 检查
     第2次：等待 10s → 检查
     第3次：等待 20s → 检查
     第4次：等待 40s → 检查
     第5次：等待 80s → 检查（最终）
     
     成功响应：{"task_id": "abc-123", "status": "done", "image_id": "img-xxx"}
     失败响应：{"task_id": "abc-123", "status": "failed", "error": "..."}
```

**图片上传失败回退策略**：
- 5 次轮询后仍失败 → 标记该图片为 `failed`，继续处理其他图片
- 商品所有图片均失败 → 商品上架状态标记为 `image_failed`，人工介入
- 商品部分图片失败 → 使用已上传的图片上架，失败图片标记 `待上传`
   
#### 竞品监控  
| 方法 | 路径 | 说明 |  
|------|------|------|  
| GET | `/api/competitors` | 竞品列表 |  
| POST | `/api/competitors` | 添加竞品 |  
| POST | `/api/competitors/check` | 触发竞品检查 |  
   
#### 报表  
| 方法 | 路径 | 说明 |  
|------|------|------|  
| GET | `/api/reports/daily` | 日报（含财务） |  
| GET | `/api/reports/weekly` | 周报 |  
| GET | `/api/reports/finance` | 财务对账报表 |  
| GET | `/api/reports/profit-calibration` | **利润校准报告** |  
   
#### 配置与媒体  
| 方法 | 路径 | 说明 |  
|------|------|------|  
| GET | `/api/settings` | 获取配置（支持shop_id） |  
| PUT | `/api/settings` | 更新配置（含熔断阈值） |  
| POST | `/api/media/upload` | 上传图片（返回 OSS key） |  
   
#### Webhook（无认证，IP白名单）  
| 方法 | 路径 | 说明 |  
|------|------|------|  
| POST | `/webhook/shopee/order` | 订单状态变更 |  
| POST | `/webhook/shopee/chat` | 买家聊天消息 |  
| POST | `/webhook/shopee/review` | 评价推送 |  
   
#### 健康检查  
| 方法 | 路径 | 说明 |  
|------|------|------|  
| GET | `/api/health` | 返回各组件状态 |  
   
### 7.3 限流策略  
| 服务 | QPS | 桶容量 | 重试策略 |  
|------|-----|--------|----------|  
| Shopee API | 10 | 20 | 指数退避（1s→2s→4s→8s→16s） |  
| 1688 API | 10 | 20 | 指数退避 |  
| 拼多多 API | 15 | 30 | 指数退避 |  
| 图片上传 | 3 | 5 | 指数退避 |  
   
- 分布式限流：Redis + Lua 脚本  
- 端点分级：查询类10 QPS，写入类5 QPS  
- 限流返回 `Retry-After` 头  
   
### 7.4 错误码体系

#### 7.4.1 错误码模块化设计

错误码按 **模块分组** 设计，每个错误码对应明确的错误类型、HTTP 状态码和响应体。

#### 7.4.2 完整错误码表

| 错误码范围 | 模块 | 说明 | HTTP |
|------------|------|------|------|
| **0** | 通用 | 成功 | 200 |
| **1000-1099** | **1xxx - 通用错误** | **参数/认证/权限** | **400/401/403/404** |
| 1001 | 参数校验 | 请求参数校验失败 | 400 |
| 1002 | 资源不存在 | 请求的资源不存在 | 404 |
| 1003 | 权限不足 | 当前用户无此操作权限 | 403 |
| 1004 | Token 无效 | Access Token 无效或过期 | 401 |
| 1005 | Token 过期 | Access Token 已过期，请刷新 | 401 |
| 1006 | Refresh Token 过期 | Refresh Token 已过期，需重新登录 | 401 |
| 1007 | 账号已禁用 | 用户账号已被禁用 | 403 |
| 1008 | IP 白名单未通过 | 请求 IP 不在允许列表中 | 403 |

| 错误码范围 | 模块 | 说明 | HTTP |
|------------|------|------|------|
| **2000-2099** | **2xxx - 商品错误** | **商品导入/翻译/图片** | **400/500** |
| 2001 | 商品导入失败 | 1688/拼多多数据采集失败 | 500 |
| 2002 | 翻译服务不可用 | LLM 服务不可用或超时 | 503 |
| 2003 | 图片处理失败 | PaddleOCR/OpenCV 处理失败 | 500 |
| 2004 | 图片上传失败 | Shopee 图片上传失败 | 500 |
| 2005 | 图片轮询超时 | 图片上传任务 5 次轮询后仍未完成 | 504 |
| 2006 | 变体映射失败 | 商品变体/SKU 映射数据不完整 | 400 |
| 2007 | 商品状态冲突 | 商品当前状态不允许此操作 | 400 |
| 2008 | OSS 上传失败 | 对象存储上传失败 | 500 |
| 2009 | 图片 URL 无效 | 图片 URL 不可访问或格式错误 | 400 |

| 错误码范围 | 模块 | 说明 | HTTP |
|------------|------|------|------|
| **3000-3099** | **3xxx - 外部 API 错误** | **Shopee/1688/拼多多** | **429/502/503** |
| 3001 | Shopee API 调用失败 | Shopee API 返回错误 | 502 |
| 3002 | Shopee API 限流 | Shopee API 触发限流 | 429 |
| 3003 | 1688 API 调用失败 | 1688 API 返回错误 | 502 |
| 3004 | 拼多多 API 调用失败 | 拼多多 API 返回错误 | 502 |
| 3005 | 汇率 API 不可用 | 汇率获取服务不可用 | 503 |
| 3006 | 货源 API 限流 | 1688/拼多多 API 触发限流 | 429 |
| 3007 | Shopee Token 失效 | 店铺 OAuth Token 已过期 | 401 |
| 3008 | 外部 API 重试耗尽 | 外部 API 重试次数已用完 | 500 |

| 错误码范围 | 模块 | 说明 | HTTP |
|------------|------|------|------|
| **4000-4099** | **4xxx - 业务规则错误** | **库存/价格/审核** | **400** |
| 4001 | 库存不足 | 商品库存为零或低于阈值 | 400 |
| 4002 | 价格异常 | 售价低于成本价（低于利润率阈值） | 400 |
| 4003 | 审核队列已满 | 审核队列达到最大容量 | 429 |
| 4004 | 商品已上架 | 商品已存在于 Shopee | 409 |
| 4005 | 商品已下架 | 商品已在 Shopee 下架 | 400 |
| 4006 | 竞对价格异常 | 竞品价格波动超过阈值 | 200 |
| 4007 | 类目不匹配 | 商品类目与属性不匹配（规则引擎） | 400 |
| 4008 | 标题长度超限 | 泰语标题超过 Shopee 限制（120 字符） | 400 |
| 4009 | 描述内容过长 | 描述超过 Shopee 限制（2000 字符） | 400 |

| 错误码范围 | 模块 | 说明 | HTTP |
|------------|------|------|------|
| **5000-5099** | **5xxx - 系统错误** | **数据库/Redis/队列** | **500** |
| 5001 | 数据库操作异常 | PostgreSQL 查询失败 | 500 |
| 5002 | Redis 操作异常 | Redis 连接或写入失败 | 500 |
| 5003 | Celery 任务失败 | Celery Worker 执行任务失败 | 500 |
| 5004 | 数据库连接池耗尽 | 数据库连接池已满 | 503 |
| 5005 | Redis 连接池耗尽 | Redis 连接池已满 | 503 |
| 5006 | Alembic 迁移失败 | 数据库迁移执行失败 | 500 |
| 5007 | 文件操作异常 | 本地文件读取/写入失败 | 500 |
| 5008 | 日志写入失败 | 日志系统不可用 | 500 |

| 错误码范围 | 模块 | 说明 | HTTP |
|------------|------|------|------|
| **6000-6099** | **6xxx - 财务/风控错误** | **利润/熔断/品牌** | **400/403** |
| 6001 | 利润低于阈值 | 利润率低于熔断阈值，自动下架 | 400 |
| 6002 | 风控拦截 | 品牌词或违禁词命中，阻断上架 | 403 |
| 6003 | 利润率校准偏差 | 预估利润与实际偏差超过阈值 | 200 |
| 6004 | 汇率波动告警 | CNY→THB 汇率波动超过阈值 | 200 |
| 6005 | 利润核算失败 | 利润计算模型执行失败 | 500 |
| 6006 | Logo 侵权检测 | OCR 检测到商品图片含品牌 Logo | 403 |
| 6007 | 类目错放检测 | 规则引擎判定商品类目不匹配 | 403 |
| 6008 | 竞品价格大幅下降 | 竞品价格下降超过阈值，提示调价 | 200 |
| 6009 | 售后退款阈值触发 | 仅退款比例超过阈值 | 200 |

#### 7.4.3 响应体格式

```json
{
    "code": 6001,
    "message": "利润低于阈值：预估利润率 2.5% < 熔断阈值 5%",
    "data": {
        "product_id": "abc-123",
        "estimated_profit": 2.5,
        "threshold": 5.0,
        "action": "auto_remove",
        "suggested_price": 159.00
    },
    "timestamp": 1751587200000
}
```

#### 7.4.4 错误码使用规范

| 规范 | 说明 |
|------|------|
| 禁止随意新增错误码 | 新增错误码需经过 Code Review，在文档中注册 |
| 错误码不可复用 | 每个错误码只能对应唯一错误场景 |
| 错误信息脱敏 | 响应体中的错误信息不包含 Token、API Key 等敏感数据 |
| HTTP 状态码一致性 | 错误码对应的 HTTP 状态码必须一致（如所有 6xxx 错误码均为 400） |
| 前端错误映射 | 前端根据错误码范围做差异化展示（如 6xxx 展示弹窗，3xxx 展示 Toast） |
   
---  
   
## 8. 定时任务与容错机制  
   
### 8.1 定时任务清单

> **调度方案**：统一使用 **Celery Beat** 进行定时任务调度。已移除 APScheduler，避免双重调度冲突。

| 时间 | 任务 | 频率 | 备注 |
|------|------|------|------|
| 00:00 | 日结对账（含财务） | 每日 | 生成昨日报表，核对Shopee账单 |
| 02:00 | 汇率更新与告警 | 每日 | CNY→THB，波动>2%触发紧急告警 |
| 03:00 | 数据库全量备份 | 每日 | 备份到 OSS |
| 04:00 | 日志轮转 | 每日 | 压缩归档，删除>30天 |
| 06:00 | 库存同步 | 用户配置 | 拉取货源库存，更新Shopee |
| 08:00 | 销量排行扫描 | 用户配置 | Top N 分析 |
| 10:00 | 搜索趋势更新 | 用户配置 | 关键词趋势 |
| 12:00 | 竞品检查 | 用户配置 | 价格/销量追踪，大幅波动告警 |
| 15:00 | 销量排行扫描 | 用户配置 | 第2次 |
| 18:00 | 竞品检查 | 用户配置 | 第2次 |
| 20:00 | 关键词更新 | 用户配置 | 第2次 |
| 22:00 | 缺货/利润熔断下架 | 每日 | 自动下架零库存及利润率不达标商品 |
| 23:00 | 日报推送 | 每日 | Telegram/邮件推送 |

**Celery Beat 配置示例**（`config/celerybeat-schedules.json`）：
```json
{
    "daily-reconciliation": {
        "task": "worker.tasks.daily_reconciliation",
        "schedule": "0 0 * * *"
    },
    "exchange-rate-update": {
        "task": "worker.tasks.exchange_rate_update",
        "schedule": "0 2 * * *"
    },
    "stock-sync": {
        "task": "worker.tasks.stock_sync",
        "schedule": "0 6 * * *",
        "kwargs": {"shop_id": "all"}
    },
    "profit-circuit-breaker": {
        "task": "worker.tasks.profit_circuit_breaker",
        "schedule": "0 22 * * *"
    }
}
```
   
### 8.2 任务幂等性与状态机  
- 每个任务定义状态：`pending → running → success / failed`  
- 使用 Redis 分布式锁防止重复执行：`lock:task:{name}:{date}`  
- 库存同步使用版本号（`version`）防止并发覆盖  
- 上架任务使用 `shopee_item_id` 唯一约束避免重复创建  
   
### 8.3 任务失败重试策略  
| 任务类型 | 重试次数 | 间隔 | 最终失败动作 |  
|----------|----------|------|--------------|  
| 库存同步 | 3 | 5s, 30s, 2min | 记录 ERROR，次日重试 |  
| 竞品检查 | 3 | 1min, 5min, 15min | 跳过本次 |  
| 汇率更新 | 2 | 1min, 5min | 使用缓存汇率，告警 |  
| 上架执行 | 5 | 指数退避（1,2,4,8,16min） | 标记失败，人工介入 |  
| 图片翻译 | 2 | 30s, 2min | 跳过该图，标记待人工 |  
| 财务核算 | 2 | 1min, 5min | 使用上次估值，告警 |  
   
---  
   
## 9. 安全架构  
   
### 9.1 认证与鉴权  
| 层级 | 方案 |  
|------|------|  
| 用户认证 | JWT（Access 2h + Refresh 7d） |  
| 密码存储 | bcrypt 哈希（盐值自动生成） |  
| API Key | AES-256-CBC 加密存储 |  
| 请求签名 | HMAC-SHA256 + **nonce（Redis TTL 300s，使用后即删除）** |  
| 权限控制 | RBAC（admin / operator / viewer） |  
| IP 白名单 | Shopee 回调 IP + Dashboard 管理后台（可选） |  
   
### 9.2 Web 安全  
| 防护项 | 方案 |  
|--------|------|  
| CSRF | SameSite Cookie + 双提交 Token |  
| XSS | HTML 转义 + CSP 策略 |  
| SQL 注入 | ORM 参数化查询 |  
| CORS | 限制允许域名 |  
   
### 9.3 数据安全  
- 传输层强制 TLS 1.3  
- 日志中敏感信息自动脱敏（替换为 `***`）  
- 密钥管理：生产环境使用 HashiCorp Vault 或 AWS Secrets Manager  
   
---  
   
## 10. 测试策略  
   
| 测试层级 | 工具 | 覆盖率目标 | 说明 |  
|----------|------|-----------|------|  
| 单元测试 | pytest + pytest-cov | ≥80% | 测试 models, services, utils |  
| 集成测试 | pytest + testcontainers | ≥70% | 测试 API 端点、数据库交互、外部API Mock |  
| E2E 测试 | playwright | 核心流程覆盖 | 模拟完整用户操作 |  
| 性能测试 | locust | - | 100 并发，API <500ms |  
| 压力测试 | locust | - | 验证限流降级 |  
   
**外部依赖 Mock**：  
- Shopee：使用沙箱环境  
- 1688/拼多多：Mock 服务器（responses 库）  
- LLM：固定模板回复  
- LangGraph：使用 `MemorySaver` 进行单元测试  
   
**CI/CD**：GitHub Actions 自动运行测试，通过后合并 main；每日凌晨自动执行 E2E。  
   
---  
   
## 11. 部署架构与硬件资源  
   
### 11.1 Docker Compose 服务组成  
| 服务 | 镜像 | 端口 | 职责 |  
|------|------|------|------|  
| api | python:3.11-slim | 8000 | FastAPI 后端 |  
| dashboard | node:20-alpine | 3000 | Next.js 前端 |  
| postgres | postgres:16-alpine | 5432 | PostgreSQL |  
| redis | redis:7-alpine | 6379 | Redis |  
| minio | minio/minio:latest | 9000/9001 | 对象存储（可替换为云服务） |  
| worker | python:3.11-slim | - | Celery Worker |  
| nginx | nginx:latest | 80/443 | 反向代理 |  
   
### 11.2 硬件资源配置建议  
| 节点角色 | 推荐配置 | 说明 |  
|----------|----------|------|  
| API & Dashboard | 2C 4G | 普通 CPU |  
| Worker (图片/OCR) | 4C 8G | 高并发 CPU |  
| LLM 推理（本地） | 8C 32G + RTX 4090/A10 | 若使用云端API则免 |  
| **初期建议** | 使用 DashScope 云端 LLM | 降低硬件门槛 |  
   
---  
   
## 12. 成本估算（参考）  
   
### 12.1 单商品处理成本（不含服务器）  
| 项目 | 单价 | 用量/商品 | 小计 |  
|------|------|----------|------|  
| LLM 翻译（云端） | 0.002 元/千token | ~500 token | 0.001 元 |  
| OCR（本地） | 0 | - | 0 |  
| 图片存储（OSS） | 0.12 元/GB/月 | 2MB/商品 | 0.00024 元/月 |  
| Shopee API | 免费 | - | 0 |  
| **合计** | **~0.001 元/商品** | | |  
   
### 12.2 服务器成本（月）  
| 环境 | 配置 | 月费用（参考） |  
|------|------|---------------|  
| 开发/测试 | 4C 8G | ~300 元 |  
| 生产（MVP） | 8C 16G + 100GB OSS | ~800 元 |  
| 生产（扩展） | 16C 32G + 1TB OSS | ~2000 元 |  
   
---  
   
## 13. 数据备份与灾难恢复  
   
### 13.1 备份策略  
| 数据 | 频率 | 保留周期 | 存储位置 |  
|------|------|----------|----------|  
| PostgreSQL | 每日 03:00 全量 + WAL 增量 | 7天本地 + 30天云 | 本地 + OSS |  
| Redis | 每日 04:00 RDB | 7天 | 本地 |  
| OSS 图片 | 版本控制 | 永久 | OSS 跨区域复制 |  
| 配置文件 | Git 提交 | 永久 | Git 仓库 |  
   
### 13.2 恢复流程  
- 数据库：`pg_restore` 恢复，RPO ≤ 24h  
- Redis：加载 RDB 文件  
- 图片：从 OSS 版本回滚  
   
### 13.3 降级方案  
| 故障 | 降级动作 |  
|------|----------|  
| LLM 不可用 | 使用缓存翻译或保留中文（标记） |  
| Shopee API 不可用 | 暂停上架，队列积累 |  
| 数据库不可用 | 切换只读副本或 SQLite 缓存（临时） |  
| OSS 不可用 | 回退本地存储（临时） |  
   
---  
   
## 14. 监控与告警体系  
   
### 14.1 业务指标（Prometheus）  
| 指标 | 类型 | 说明 |  
|------|------|------|  
| `products_imported_total` | Counter | 累计导入商品数 |  
| `listings_success_total` | Counter | 上架成功数 |  
| `listings_failed_total` | Counter | 上架失败数 |  
| `translation_duration_seconds` | Histogram | 翻译耗时 |  
| `image_process_duration_seconds` | Histogram | 图片处理耗时 |  
| `api_call_total` | Counter | 外部API调用数 |  
| `api_call_errors_total` | Counter | 外部API错误数 |  
| `queue_depth` | Gauge | Celery 队列深度 |  
| `active_products` | Gauge | 在售商品数 |  
| `profit_margin_avg` | Gauge | 平均利润率 |  
| `risk_intercepts_total` | Counter | 风控拦截总数 |  
| `profit_calibration_deviation` | Histogram | 利润预估偏差分布 |  
   
### 14.2 告警级别与处理策略  
| 级别 | 触发条件 | 通知方式 | 自动处理 |  
|------|----------|----------|----------|  
| **P0** | Shopee API 连续失败 3 次 | Telegram + 邮件 | 暂停上架任务 |  
| **P0** | 汇率波动 >2% | Telegram + 短信 | 暂停所有自动上架 |  
| **P1** | 利润率低于红线 | Telegram | 自动下架/暂停 |  
| **P1** | 品牌词/违禁词命中 | Dashboard 弹窗 | 记录 risk_logs，阻断 |  
| **P1** | 上架失败 >5 次 | Telegram | 人工介入 |  
| **P1** | 图片翻译连续失败 3 张 | Telegram | 暂停该商品处理 |  
| **P2** | 库存低于阈值 | 日报 | - |  
| **P2** | 竞品价格大幅下降 | Telegram | 提示调价 |  
| **P3** | 翻译置信度低 | 日志 | 标记人工审核 |  
   
**告警收敛**：相同告警 30 分钟内不重复发送（Redis 去重）。  
   
### 14.3 健康检查  
- `GET /api/health` 返回各组件状态（数据库、Redis、LLM、Shopee API、OSS）  
- 任意组件失败返回 HTTP 503  
   
---  
   
## 15. 开发阶段规划（含任务清单）  
   
### Phase 0 — 基础架构（第1-2周）  
- [ ] 项目初始化，Docker Compose（PostgreSQL + Redis + MinIO）  
- [ ] 用户认证与店铺管理（JWT + bcrypt）  
- [ ] 基础配置管理（settings 表）  
- [ ] 数据库迁移（Alembic）  
- [ ] **LangGraph 工作流框架搭建（空节点）**  
   
### Phase 1 — MVP 核心闭环（第3-6周）  
- [ ] 数据采集（1688 API + 基础反爬代理池）  
- [ ] 基础翻译（标题+描述，接入 DashScope/本地 Qwen via LangGraph）  
- [ ] Shopee 商品创建 API（含图片异步轮询）  
- [ ] Web Dashboard（商品列表 + 审核队列 + 上架记录）  
- [ ] 审核队列（人工/自动）  
- [ ] 基础日报生成  
   
### Phase 2 — 财务风控 + 对象存储（第7-10周）⭐ **核心壁垒，提前至此**  
- [ ] **财务利润核算模型与熔断机制**  
- [ ] **利润校准模块（历史利润学习）**  
- [ ] **敏感词库与品牌侵权拦截（含 OCR 识别 Logo）**  
- [ ] 类目错放检测  
- [ ] **接入 OSS 对象存储，替换本地 data/images**  
- [ ] 热销品获取与竞品监控  
- [ ] 定价建议模块  
   
### Phase 3 — 图片翻译 + 变体（第11-14周）
- [ ] **图片翻译主图优先**：先完成主图翻译（验证流程），详情页批量处理延后
- [ ] **Celery 分片图片处理**：将单商品多图拆分为多个子任务并行处理
  - `celery -A worker.tasks worker --concurrency=4`（根据 CPU 配置调整）
  - 每个子任务处理 1-2 张图片，完成一个立即写入数据库
- [ ] OCR 图片文字提取（PaddleOCR，中/泰语）
- [ ] 图片合成（OpenCV 文本覆盖，支持颜色匹配）
- [ ] 变体（规格/SKU）处理与映射
- [ ] 图片去水印、白底抠图
- [ ] 图片质量评估（PSNR）

**图片处理 Celery 任务设计**：
```python
# worker/tasks.py
from celery import group

@app.task
def batch_translate_images(product_id: str, image_urls: list[str]):
    """批量图片翻译（分片处理）"""
    # 拆分为子任务
    translate_single = translate_single_image.s(product_id, image_url)
    
    # 并行执行（concurrency 控制并发数）
    results = group(translate_single for image_url in image_urls)()
    
    # 汇总结果
    success_count = sum(1 for r in results if r and r[1])
    return {"total": len(image_urls), "success": success_count}

@app.task
def translate_single_image(product_id: str, image_url: str):
    """单张图片翻译（可重试）"""
    try:
        # OCR 提取 → 翻译 → OpenCV 合成
        text = paddle_ocr(image_url)
        translated = llm_translate(text, target_lang='th')
        result_image = opencv_synthesize(image_url, translated)
        oss_key = oss_upload(result_image)
        return (True, oss_key)
    except Exception as e:
        return (False, str(e))
```
   
### Phase 4 — 运营增强 + Webhook（第15-18周）  
- [ ] 拼多多数据源  
- [ ] **Webhook 接收端点（订单/聊天/评价）**  
- [ ] 售后自动化策略（仅退款阈值、差评补偿）  
- [ ] 库存自动同步  
- [ ] 促销自动化（Voucher/Flash Sale）  
- [ ] 泰语搜索词库建设  
   
### Phase 5 — 运维 + 扩展（第19-22周）  
- [ ] Docker 容器化生产部署与硬件调优  
- [ ] 多站点/多店铺支持  
- [ ] 告警体系完善（Telegram+邮件+短信）  
- [ ] 数据备份与灾备落地  
- [ ] API 限流完善（分布式）  
- [ ] 单元测试 + 集成测试（≥80%）  
- [ ] 安全加固（Vault, CSRF, CSP）  
   
---  
   
## 16. 技术依赖清单  
   
### Python（`api/requirements.txt`）  
```  
fastapi>=0.104.1  
uvicorn[standard]>=0.24.0  
sqlalchemy>=2.0.23  
alembic>=1.12.1  
asyncpg>=0.29.0  
redis>=5.0.1  
celery>=5.3.4  
langchain>=0.1.0  
langchain-openai>=0.0.2  
langchain-community>=0.1.0  
langgraph>=0.0.30  
dashscope>=1.14.0  
paddleocr>=2.7.0.3  
pillow>=10.1.0  
opencv-python>=4.8.1.78  
httpx>=0.25.1  
apscheduler>=3.10.4  
python-dotenv>=1.0.0  
pydantic>=2.5.0  
pydantic-settings>=2.1.0  
pandas>=2.1.3  
numpy>=1.24.3  
bcrypt>=4.1.2  
pyjwt>=2.8.0  
cryptography>=41.0.7  
boto3>=1.34.0  
aiobotocore>=2.11.0  
playwright>=1.40.0  
pytest>=7.4.3  
pytest-cov>=4.1.0  
pytest-asyncio>=0.21.1  
locust>=2.20.0  
```  
   
### Node.js（`dashboard/package.json`）  
```json  
{  
  "dependencies": {  
    "next": "^14.0.0",  
    "react": "^18.0.0",  
    "tailwindcss": "^3.0.0",  
    "shadcn-ui": "latest",  
    "@tanstack/react-query": "^5.0.0",  
    "axios": "^1.0.0",  
    "zustand": "^4.0.0",  
    "next-auth": "^4.0.0"  
  }  
}  
```  
   
### Docker 镜像  
```  
python:3.11-slim  
postgres:16-alpine  
redis:7-alpine  
node:20-alpine  
minio/minio:latest  
```  
   
---  
   
## 17. 项目目录结构  
   
```  
pipixia/  
├── api/                          # FastAPI 后端  
│   ├── main.py  
│   ├── config.py  
│   ├── models/                   # SQLAlchemy 模型  
│   │   ├── user.py, shop.py, product.py, listing.py, translate.py,
│   │   ├── variation.py, competitor.py, keyword.py, image_asset.py,
│   │   ├── order.py, shipment.py, transaction.py, risk_log.py,
│   │   ├── setting.py, audit_log.py, error_log.py, profit_calibration.py,
│   │   ├── category_mapping.py, site_config.py
│   ├── schemas/                  # Pydantic 请求/响应  
│   ├── routers/                  # API 路由  
│   │   ├── auth.py, shops.py, products.py, listings.py, audit.py,  
│   │   ├── competitors.py, reports.py, settings.py, media.py, webhooks.py  
│   ├── services/                 # 业务逻辑  
│   │   ├── crawler/              # 数据采集（含反爬）  
│   │   ├── ai_engine/            # LangGraph 工作流  
│   │   │   ├── translator_graph.py, translator.py, image_translate.py,  
│   │   │   ├── seo_optimizer.py, cache.py  
│   │   ├── finance/              # 财务核算与熔断  
│   │   ├── risk/                 # 风控模块  
│   │   ├── listing/              # 上架执行  
│   │   ├── monitor/              # 竞品/库存监控  
│   │   ├── report/               # 报表生成  
│   │   └── storage/              # 对象存储统一接口  
│   ├── middleware/               # 鉴权、限流、日志  
│   ├── utils/                    # 工具函数  
│   └── requirements.txt  
├── worker/                       # Celery 后台任务  
│   ├── celery_app.py  
│   ├── tasks.py  
│   └── requirements.txt          # 精简依赖  
├── dashboard/                    # Next.js 前端
│   ├── src/
│   │   ├── app/                  # 页面路由（App Router）
│   │   ├── components/           # UI 组件
│   │   ├── lib/                  # API 客户端
│   │   └── styles/
│   └── package.json  
├── migrations/                   # Alembic 迁移  
├── config/                       # 配置文件（YAML/JSON）  
│   ├── settings.yaml  
│   ├── llm.yaml  
│   ├── categories.yaml  
│   ├── risk_words.json  
│   └── prompts.yaml  
├── scripts/                      # 运维脚本  
│   ├── init_db.py  
│   ├── create_admin.py  
│   └── backup.py  
├── tests/                        # 单元/集成/E2E测试  
├── docker-compose.yml  
├── .env.example  
├── Makefile  
└── README.md  
```  
   
---  

## Next.js SSR/SSG 策略（V4.1 新增）

### 路由渲染策略

| 页面 | 渲染方式 | 说明 |
|------|----------|------|
| `/` (Dashboard 首页) | **SSR** | 需要实时数据（商品数、待审核数等） |
| `/products` | **SSR** | 商品列表需服务端分页/筛选 |
| `/products/[id]` | **SSR** | 商品详情需实时数据 |
| `/listings` | **SSR** | 上架记录需实时数据 |
| `/reports` | **SSR** | 报表数据需服务端聚合 |
| `/settings` | **SSR** | 配置数据需服务端获取 |
| `/login` | **CSR** | 纯表单交互，无数据依赖 |
| `/dashboard/*` (子页面) | **CSR** | SPA 路由，前端状态管理 |

### 数据获取策略

- **SSR 页面**：使用 `getServerSideProps()` 在服务端获取数据，首屏直接渲染
- **CSR 页面**：使用 `@tanstack/react-query` 客户端缓存，减少重复请求
- **静态页面**（如有）：使用 `getStaticProps()` + ISR（增量静态再生）

### 性能优化

| 优化项 | 方案 |
|--------|------|
| 首屏加载 | SSR + 服务端压缩（gzip/brotli） |
| API 缓存 | React Query staleTime=60s（商品列表等低频更新数据） |
| 图片优化 | Next.js `<Image>` 组件 + WebP 格式 |
| 代码分割 | `next/dynamic` 动态加载大组件（图表、编辑器） |
| CDN 加速 | Next.js Image Optimization + Vercel 边缘网络 |

---

**本文档为 V4.1-ARCH 完整版**，在 V4.0 基础上补充了：
1. LangGraph 状态持久化（PostgresSaver）
2. 图片翻译主图优先 + Celery 分片处理
3. Shopee 图片上传异步模式明确定义
4. 翻译缓存近重复检测（simhash/MinHash）
5. 移除 APScheduler，统一 Celery Beat 调度
6. 类目错放规则引擎 + category_mapping 表
7. site_config 多站点扩展表
8. 结构化错误码体系（模块化设计）
9. 依赖版本锁定策略（开发/构建/生产）
10. Next.js SSR/SSG 渲染策略

可直接作为团队开发、测试、部署的全栈参考。如有章节需要进一步细化，可随时补充。

祝 pipixia 项目开发顺利！🚀
