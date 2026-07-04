# 项目设计文档：pipixia —— 跨境电商自动上架工具 (V4.0 完整版)

**项目定位**：1688/拼多多 → Shopee 泰国站 | 自动选品 → LangGraph AI 编排 → 智能上架 → 财务风控闭环  
**文档版本**：V4.0 | **更新日期**：2026-07-04 | **维护者**：pipixia 研发团队  
**开发工具**：LangChain + LangGraph（AI 工作流编排）

---

## 目录

1. [项目概述](#一项目概述)
2. [系统架构](#二系统架构)
3. [功能模块设计](#三功能模块设计)
   - 3.1 数据采集（含反爬）
   - 3.2 热销品获取
   - 3.3 AI 翻译/优化（LangGraph 编排）
   - 3.4 图片翻译与对象存储
   - 3.5 财务与利润核算（熔断机制）
   - 3.6 风控与合规（防封店）
   - 3.7 审核模块
   - 3.8 上架执行（含 Webhook 监听）
   - 3.9 库存同步
   - 3.10 订单与售后自动化
   - 3.11 促销活动
   - 3.12 监控报表
4. [合规与法律风险](#四合规与法律风险)
5. [数据库设计](#五数据库设计)
6. [定时任务与容错](#六定时任务与容错)
7. [API 设计详规](#七api-设计详规)
8. [错误码与告警体系](#八错误码与告警体系)
9. [API 速率控制策略](#九api-速率控制策略)
10. [国际化/本地化](#十国际化本地化)
11. [日志与监控](#十一日志与监控)
12. [安全设计](#十二安全设计)
13. [测试策略](#十三测试策略)
14. [硬件资源与部署评估](#十四硬件资源与部署评估)
15. [成本估算](#十五成本估算)
16. [数据备份与灾难恢复](#十六数据备份与灾难恢复)
17. [性能与扩展性](#十七性能与扩展性)
18. [开发优先级（Phase 规划）](#十八开发优先级phase-规划)
19. [技术依赖清单](#十九技术依赖清单)
20. [项目目录结构](#二十项目目录结构)
21. [附录：用户快速启动指南](#二十一附录用户快速启动指南)

---

## 一、项目概述

### 1.1 项目目标

开发一个跨境电商自动上架工具（pipixia），实现从 1688/拼多多采集商品，通过 **LangGraph 编排的 AI 工作流**翻译优化为泰语，自动上架到 Shopee 泰国站的全流程自动化。同时建立**财务防亏损模型**与**合规防封店机制**，确保业务安全、盈利，实现"一人一店"的轻量化跨境运营。

### 1.2 核心流程

```
数据采集(含反爬) → LangGraph AI 编排(缓存→风控→翻译→本地化→SEO) → 财务核算(利润熔断) → 商品审核 → 上架执行(Webhook监听) → 监控报表
```

### 1.3 关键约束

- **目标站点**：Shopee 泰国站（架构支持后续扩展多站点）
- **货源平台**：1688、拼多多（**优先官方 API**，爬虫作为备选）
- **类目限制**：全品类（排除女装、危险品类目、敏感类目）
- **运行环境**：初期本机 Docker 运行，后期迁移至云服务器集群
- **安全约束**：必须具备品牌侵权拦截、违禁词过滤、利润红线熔断机制
- **合规优先**：所有数据获取遵守平台协议，不得违规爬取非公开数据
- **AI 工具**：使用 LangChain + LangGraph 编排翻译、风控、SEO 优化的有向图工作流

---

## 二、系统架构

### 2.1 整体架构图（增强版）

```
┌─────────────────────────────────────────────────────────────────┐
│                      Web Dashboard (Next.js)                    │
│  选品 | 审核 | 财务看板 | 风控日志 | 配置 | 店铺管理            │
└────────────────────────────┬────────────────────────────────────┘
│ HTTP/REST / WebSocket
┌────────────────────────────▼────────────────────────────────────┐
│                    API Gateway (FastAPI + Nginx)                │
│        路由 / 鉴权 / 限流 / 日志 / IP白名单 / Webhook接收       │
└──┬──────────┬──────────┬──────────┬──────────┬─────────────────┘
│          │          │          │          │
▼          ▼          ▼          ▼          ▼
┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌──────────┐
│数据采集│ │LangGraph│ │上架执行│ │财务风控│ │监控报表  │
│(含反爬)│ │AI 编排  │ │(含重试)│ │(含熔断)│ │模块      │
└───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘ └────┬─────┘
│         │         │         │           │
└─────────┴─────────┴─────────┴───────────┘
│
┌───────────────┴───────────────┐
│      Celery Worker 集群        │
│  (OCR/图片合成/批量上架/风控)   │
└───────────────┬───────────────┘
│
┌───────────────────────────┼───────────────────────────┐
▼                           ▼                           ▼
┌──────────────┐      ┌─────────────────┐      ┌──────────────────┐
│  PostgreSQL  │      │   Redis         │      │  对象存储 (OSS/  │
│  (持久化)    │      │ (缓存/队列/限流) │      │  S3/MinIO)       │
└──────────────┘      └─────────────────┘      │  (图片/报表存储) │
└──────────────────┘
│                           │                           │
▼                           ▼                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  外部服务：1688 API / 拼多多 API / Shopee API / LLM (Qwen/DashScope)│
│  反爬辅助：代理池 / 打码平台 / Playwright                           │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 技术选型

| 模块 | 技术栈 | 说明 |
|------|--------|------|
| **后端框架** | Python + FastAPI | 高性能异步 API，适合高并发 I/O |
| **AI/LLM** | **LangChain + LangGraph** + DashScope(通义) / 本地 Qwen | 翻译、摘要、策略生成（LangGraph 编排有向图工作流） |
| **数据库** | PostgreSQL 16 | 持久化存储，支持 JSONB |
| **缓存/队列** | Redis 7 + Celery 5 | 任务队列、分布式锁、限流 |
| **对象存储** | 阿里云 OSS / AWS S3 / Cloudflare R2 | 存放商品图片，支持 CDN 加速 |
| **OCR** | PaddleOCR | 图片文字提取（中/泰语） |
| **反爬组件** | Playwright + 代理IP + 打码平台 | 应对 1688/PDD 滑块验证码及 IP 封禁 |
| **前端** | Next.js + TailwindCSS + Shadcn/UI | Web Dashboard |
| **任务调度** | APScheduler + Celery Beat | 定时任务触发 |
| **部署** | Docker + Docker Compose | 容器化部署 |
| **监控** | Prometheus + Grafana | 指标可视化 |
| **日志** | ELK (可选) 或 文件轮转 | 集中日志管理 |

---

## 三、功能模块设计

### 3.1 数据采集模块（含反爬策略）

**职责**：从货源平台获取商品信息，保障采集稳定性。

**支持的货源**：
- 1688（阿里巴巴批发）- **优先官方 API**
- 拼多多 - **优先官方 API**

**采集维度**：
- 商品标题、描述、价格、库存
- 商品图片（主图 + 详情页）
- 规格参数（颜色、尺码、重量等）
- 运费模板信息

**采集方式**：
- **官方 API**（首选）：1688 开放平台 API、拼多多开放平台 API
- **爬虫采集**（备选，需遵守 robots.txt）：
  - IP 代理池：对接第三方代理（如快代理、阿布云），单 IP 请求频率控制
  - 验证码识别：集成打码平台（如超级鹰）或本地 OCR 识别滑块/点选验证码
  - 账号池轮换：多 Cookie 账号轮换采集，降低单账号风控风险
  - Playwright 渲染：对动态加载页面使用无头浏览器

**采集频率**：用户自定义设置（支持手动触发、定时轮询）。

**限流与重试**：
- 令牌桶算法控制 QPS（1688 10 QPS，拼多多 15 QPS）
- 失败重试指数退避（1s → 2s → 4s → 8s）
- 连续失败 10 次触发告警并暂停该任务

---

### 3.2 热销品获取模块

**四种获取方式，用户可自主选择**：

**A. 销量排行**
- 从 Shopee 泰国站 Top Selling 榜单获取热销品
- 支持按类目筛选，时间范围（日/周/月）

**B. 搜索趋势**
- 基于关键词搜索热度获取潜在热销品
- 关键词来源：Shopee 搜索框联想词、第三方关键词工具（如 Google Trends）
- 支持长尾词挖掘

**C. 竞品监控**
- 监控指定竞品店铺的商品（需遵守平台公开数据政策）
- 追踪竞品价格/销量/评价变化
- 自动标记"有机会跟进"的商品

**D. 关键词热度**
- 基于搜索量大的关键词，反查热门商品
- 关键词分类：行业词、场景词、属性词
- 支持关键词趋势分析

---

### 3.3 AI 翻译/优化模块（LangGraph 编排）

**核心目标**：高质量、低成本地将中文商品信息转化为泰语本地化内容。

#### 3.3.1 LangGraph 工作流设计

使用 **LangGraph** 编排翻译、风控、SEO 优化的有向图工作流，支持条件分支、循环和状态管理：

```
┌─────────────────────────────────────────────────────────────┐
│                   LangGraph State Machine                   │
│                                                             │
│  [start]                                                    │
│     │                                                       │
│     ▼                                                       │
│  ┌─────────────┐                                            │
│  │ 缓存检查     │ ← Hash 匹配，命中则直接输出                │
│  └──────┬──────┘                                            │
│         │ 未命中                                             │
│         ▼                                                   │
│  ┌─────────────┐                                            │
│  │ 风控预检     │ ← 品牌词/违禁词拦截（先拦截再翻译）        │
│  └──────┬──────┘                                            │
│         │ 通过                                              │
│         ▼                                                   │
│  ┌─────────────┐                                            │
│  │ 翻译调度     │ ← 条件分支：核心卖点→大模型 / 普通描述→轻量模型 │
│  └──────┬──────┘                                            │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────┐                                            │
│  │ 泰语本地化   │ ← 加入泰国电商常用语料库                   │
│  └──────┬──────┘                                            │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────┐                                            │
│  │ SEO 优化     │ ← 标题关键词密度、描述卖点提炼             │
│  └──────┬──────┘                                            │
│         │                                                   │
│         ▼                                                   │
│  [end] → 优化后的商品数据                                    │
│                                                             │
│  异常路径：                                                  │
│  - 风控拦截 → 记录 risk_logs → 阻断上架                      │
│  - 翻译置信度低 → 标记人工审核                                │
│  - LLM 不可用 → 降级使用缓存或保留中文                        │
└─────────────────────────────────────────────────────────────┘
```

**LangGraph 状态定义（Python 伪代码）**：

```python
from langchain_core.messages import HumanMessage, AIMessage
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
    model_used: str  # "qwen-72b" / "qwen-1.8b" / "cached"
    seo_score: float
    errors: list[str]

def graph_builder():
    from langgraph.graph import StateGraph, END
    
    workflow = StateGraph(TranslationState)
    
    # 定义节点
    workflow.add_node("cache_check", cache_check_node)
    workflow.add_node("risk_precheck", risk_precheck_node)
    workflow.add_node("translate_title", translate_title_node)
    workflow.add_node("translate_desc", translate_desc_node)
    workflow.add_node("localize_th", localize_th_node)
    workflow.add_node("seo_optimize", seo_optimize_node)
    workflow.add_node("quality_eval", quality_eval_node)
    
    # 设置入口
    workflow.set_entry_point("cache_check")
    
    # 缓存检查 → 风控预检
    workflow.add_edge("cache_check", "risk_precheck")
    
    # 风控预检 → 翻译（条件边）
    workflow.add_conditional_edges(
        "risk_precheck",
        lambda state: "translate_title" if not state["risk_flag"] else "END",
        {"translate_title": "translate_title", "END": END}
    )
    
    # 顺序执行
    workflow.add_edge("translate_title", "translate_desc")
    workflow.add_edge("translate_desc", "localize_th")
    workflow.add_edge("localize_th", "seo_optimize")
    workflow.add_edge("seo_optimize", "quality_eval")
    
    # 质量评估 → 结束
    workflow.add_conditional_edges(
        "quality_eval",
        lambda state: "END" if state["confidence_score"] >= 0.85 else "END",
        {"END": END}
    )
    
    return workflow.compile()
```

#### 3.3.2 工作流程详解

```
原始商品数据
│
▼
┌─────────────────┐
│ 缓存检查 (Hash) │ ← 相似内容复用翻译结果，节省Token
└────────┬────────┘
│ (未命中)
▼
┌─────────────────┐
│ 风控预检         │ ← 品牌词/违禁词拦截（先拦截再翻译）
└────────┬────────┘
│
▼
┌─────────────────┐
│ 翻译调度         │ ← 核心卖点 → 大模型；普通描述 → 轻量模型
└────────┬────────┘
│
▼
┌─────────────────┐
│ 泰语本地化       │ ← 加入泰国电商常用语料库
└────────┬────────┘
│
▼
┌─────────────────┐
│ SEO 优化         │ ← 标题关键词密度、描述卖点提炼
└────────┬────────┘
│
▼
优化后的商品数据 → 财务核算 → 审核队列
```

**AI 能力清单**：

| 能力 | 说明 |
|------|------|
| 标题翻译 + SEO | 泰语标题翻译，融入热搜关键词 |
| 描述翻译 + 本地化 | 泰语描述，符合泰国消费者语境 |
| 卖点提炼 | 从原始描述中提取核心卖点 |
| 竞品定价分析 | 基于同类竞品给出建议定价 |
| 类目自动匹配 | 根据商品属性自动推荐 Shopee 类目 |
| 关键词推荐 | 推荐泰语热搜词、长尾词 |
| 图片翻译 | OCR → 翻译 → 合成（见下节） |

**LLM 调度优化**：

- **翻译缓存**：对商品描述进行 Hash（忽略空格、标点），相似度 >90% 时复用历史翻译结果，减少 Token 消耗
- **混合模型**：核心卖点、标题用高质量大模型（如 Qwen-72B 或 DashScope 通义千问），普通描述用轻量模型（如 Qwen-1.8B），平衡成本与质量
- **本地/云端切换**：优先使用本地部署的 Qwen（节省费用），若 GPU 资源不足则自动切换到云端 API（DashScope）
- **LangGraph 优势**：支持状态持久化、异常中断恢复、并行子图执行（如翻译和风控可并行）

---

### 3.4 图片翻译与存储模块（最关键）

**完整流程**：

1. **OCR 文字提取**：从商品图中提取中文文字区域（PaddleOCR）
2. **翻译**：将提取的文字翻译为泰语（复用翻译缓存）
3. **图片合成**：将泰语文本覆盖到原图对应位置（字体：TH Sarabun New）
4. **后处理**：颜色匹配、清晰度优化、自动白底抠图（U²-Net）
5. **质量评估**：PSNR 自动检测，低于阈值标记人工复核

**处理范围**：
- 主图（去水印/覆盖 LOGO）：使用 OpenCV `inpaint` 修复，复杂水印保留人工标记
- 详情页图片（批量处理，10-20 张/产品）
- 非中文图片（英文/日文也需翻译）

**图片规格适配**：
- Shopee 要求：JPG/PNG，≤5MB，推荐 1:1 比例
- 支持白底图自动抠图，提升商品展示效果
- 支持图片去重（感知哈希 dHash），避免重复上架

**图片存储（关键变更）**：
- **生产环境强制使用对象存储**（OSS / S3 / MinIO），禁止使用本地 `data/images/`
- 数据库仅保存 `oss_key`，图片通过 CDN 加速访问
- 本地仅作为临时处理缓存（24 小时自动清理）
- 支持多云容灾（主备切换）

**图片翻译失败降级**：
- 单张失败：保留原图，跳过翻译，标记"待人工"
- 连续 3 张失败：暂停该商品图片处理，触发告警

---

### 3.5 财务与利润核算模块（防亏损核心）

**职责**：确保每一笔上架都能盈利，避免隐性成本导致的亏损。

**利润计算公式**（动态计算）：

```text
预估利润 = 售价(THB)
- 采购成本(CNY) × 汇率
- 国内运费(CNY) × 汇率
- 跨境运费(THB) [按体积重/实重取大]
- 平台佣金(THB) [按类目比例]
- 交易手续费(THB) [约 2%]
- 活动服务费(THB) [如参与闪购]
- 汇率损耗缓冲 [预留 1%]
```

**熔断机制**：

- 当 **预估利润率 < 用户设定阈值（默认 15%）** 时，自动触发以下行为：
  1. 记录风控日志（`risk_logs`）
  2. 暂停该商品上架，标记为"利润不足"
  3. 发送 Telegram 告警
  4. 若商品已在售，则自动下架或调整为"缺货"状态（用户可配置）

**动态参数更新**：
- 汇率每日更新，波动 >2% 时触发紧急告警并暂停上架任务
- 货源价格变动（通过定时同步）实时更新成本，重新核算利润

**财务报表**：
- 每日生成利润报表（含实际利润 vs 预估利润对比）
- 自动对账 Shopee 账单，标记差异项
- **历史利润学习**：系统持续收集实际利润数据，校准预估模型的偏差，提高预测精度

---

### 3.6 风控与合规模块（防封店核心）

**职责**：在上架前拦截所有可能导致店铺违规或处罚的风险因素。

**敏感词拦截**：
- 内置泰国当地违禁词库（如赌博、色情、毒品相关）、大牌品牌词（Nike, Apple, Gucci 等）
- 支持正则匹配和模糊匹配，命中则记录 `risk_logs`，阻断上架
- 词库可在线更新（用户可添加自定义词）

**图片查重与鉴黄**：
- 使用感知哈希检测图片相似度，避免重复铺货
- 集成简易鉴黄模型（如 NSFW 检测），拦截违规图片

**类目错放检测**：
- 基于商品属性（如"材质"、"尺寸"）交叉验证类目匹配度
- 若置信度低于阈值，标记人工复审或阻止上架

**品牌侵权检测**：
- 标题/描述中识别知名品牌名称，若未授权则拦截
- 图片 OCR 识别 Logo 水印，比对品牌库

**操作审计**：
- 所有拦截动作记录审计日志（`audit_logs`），便于追溯

---

### 3.7 审核模块

**两种模式**（用户可配置）：

**A. 审核模式**（默认）
- AI 优化后的商品进入审核队列，用户逐条或批量审核
- 支持编辑（修改标题/价格/描述）后再通过
- 审核通过后自动触发上架

**B. 全自动模式**
- AI 优化后直接上架（需满足：翻译置信度≥85%、利润率≥阈值、风控无拦截）
- 异常自动回滚并告警

**审核规则（全部可配置）**：

| 规则 | 默认值 | 说明 |
|------|--------|------|
| 最低预估利润率 | 15% | 低于此值触发熔断 |
| 最小翻译置信度 | 85% | 低于此值进入人工审核 |
| 价格偏离阈值（vs 竞品） | ±30% | 超出范围需人工确认 |
| 图片数量下限 | 5 张 | 不足则拒绝上架 |
| 标题最小长度 | 20 字符 | 太短影响 SEO |
| 描述最小长度 | 100 字符 | 太短影响转化 |
| 关键词数量下限 | 3 个 | 自动推荐 |

---

### 3.8 上架执行模块（含 Webhook 监听）

**Shopee API 对接**：

| 功能 | API 端点 | 说明 |
|------|----------|------|
| 创建商品 | `POST /api/v1/product/add` | 需先上传图片获取 `image_id` |
| 更新商品 | `PUT /api/v1/product/{item_id}` | - |
| 图片上传 | `POST /api/v1/media/upload` | 异步返回 `image_id` |
| 变体管理 | `POST /api/v1/product/{item_id}/variation` | - |
| 价格/库存更新 | `PUT /api/v1/product/{item_id}/price` | - |

**上架字段映射（Shopee）**：

| 内部字段 | Shopee 字段 | 类型 | 必填 |
|----------|-------------|------|------|
| title_th | title | string | ✅ |
| description_th | description | string | ✅ |
| price_thb | price | number | ✅ |
| images[].oss_key | 先上传获得 image_id | array | ✅ |
| category_id | category_id | int | ✅ |
| brand | brand | string | - |
| condition | condition (new) | enum | ✅ |
| variations[].sku | variations | array | - |
| stock | stock | int | ✅ |
| shipping_template_id | shipping_template_id | int | ✅ |

**异步图片处理**：
- 调用图片上传 API 后，轮询获取 `image_id`（最多 5 次，间隔 2s）
- 获得所有 `image_id` 后再调用创建商品 API，确保一致性

**重试与回滚**：
- 上架失败重试 5 次（指数退避）
- 第 5 次失败标记为 `failed`，发 Telegram 告警
- 若已上传图片但商品创建失败，自动清理已上传图片（调用删除接口）

**Webhook 实时监听**（新增）：
- **订单状态变更**：`/webhook/shopee/order` — 收到后更新本地订单状态，触发发货流程
- **买家聊天消息**：`/webhook/shopee/chat` — 可接入 AI 自动回复（模板或 GPT）
- **评价推送**：`/webhook/shopee/review` — 自动回复好评，差评触发告警

---

### 3.9 库存同步模块

- 定时拉取货源库存（1688/拼多多），更新本地 `products.stock`
- 同步更新 Shopee 库存（调用更新接口）
- 库存下限预警（阈值可配置，Telegram/邮件通知）
- 库存归零策略：自动下架 / 标记缺货 / 允许超卖（用户可选）
- 多货源库存合并（取和或最小值，用户配置）

---

### 3.10 订单与售后自动化模块

**订单同步**：
- 通过 Webhook 实时接收订单，或定时拉取
- 自动在货源平台下单（调用 1688/拼多多 API 生成采购单）
- 获取物流单号后回填 Shopee（发货）

**售后自动化策略**（新增）：
- **仅退款阈值**：设定金额阈值（如 50 泰铢以下），买家申请退款时自动同意，无需退货（跨境退回运费高于货值）
- **差评补偿**：AI 分析差评内容（情感分析），若为产品质量问题，自动发送小额优惠券（通过 Shopee 聊聊）进行安抚，同时记录反馈用于改进描述
- **退货处理**：退货金额较高时，转入人工审核

---

### 3.11 促销活动模块

- Shopee Voucher 关联（上架时自动关联优惠券）
- Flash Sale 报名（价格符合时自动报名）
- Free Shipping 标签自动加入
- Bundle Deal 捆绑销售（手动配置）

---

### 3.12 监控报表模块

- 实时看板：今日上架数、成功/失败数、销售额、利润、平均利润率
- 日结对账报表（含财务对账）
- 竞品价格监控仪表盘（趋势图）
- 搜索趋势热力图
- 告警通知（Telegram / 邮件）

---

## 四、合规与法律风险

### 4.1 数据采集合规

- **优先使用官方 API**：1688 和拼多多均提供官方开发者 API，优先申请并使用
- **爬虫限制**：若必须使用爬虫，仅抓取公开可访问的数据，设置合理请求间隔（≥ 2 秒），遵守 robots.txt
- **严禁行为**：不得破解反爬机制、不得模拟登录抓取非公开数据、不得对目标平台造成服务压力

### 4.2 Shopee 平台政策

- 仔细阅读并遵守 Shopee 开发者协议（Developer Terms of Service）
- 自动化上架频率控制在 API 允许范围内，避免被认定为违规操作
- 不使用自动化工具进行刷单、虚假评价等违规行为

### 4.3 用户数据保护

- 用户店铺 Token/API Key 使用 AES-256 加密存储
- 所有用户数据归属于用户本人，系统不做二次利用
- 提供"数据导出"和"账号注销"功能，满足 GDPR 及当地法规

### 4.4 用户授权机制

- 首次使用需用户明确勾选《服务协议》和《隐私政策》
- 明确告知用户：系统会自动操作其店铺商品，风险由用户承担
- 建议用户使用子账号或受限权限 Token，降低风险

---

## 五、数据库设计（核心表扩展）

### 5.1 完整表结构（新增表已标注）

```sql
-- 用户表
users (id, username, email, password_hash, role, is_active, last_login_at, created_at, updated_at)
-- 店铺表（支持多店铺）
shops (id, user_id, shop_name, platform, shop_token_encrypted, shop_id, is_active, config_json, created_at, updated_at)
-- 商品表
products (id, shop_id, source_platform, source_item_id, title_zh, title_th, description_zh, description_th,
category_id, images_oss_keys_json, price_cny, price_thb, cost_cny, profit_margin,
risk_status, status, created_at, updated_at)
-- 上架记录表
listings (id, product_id, shop_id, shopee_item_id, shopee_status, listing_price_thb, stock,
variation_data_json, audit_status, audit_comment, listing_mode, retry_count, last_error, created_at, updated_at)
-- 翻译记录表（含缓存）
translates (id, product_id, translate_type, source_text_hash, source_text, target_text,
source_image_url, target_image_url, status, confidence_score, created_at, updated_at)
-- 商品变体表
product_variations (id, product_id, variation_name, variation_value, sku_code, price_thb, stock, image_url, shopee_variation_id)
-- 竞品表
competitors (id, product_id, shopee_item_id, shop_name, price_history_json, sales_history_json, rating, review_count, last_check_at)
-- 关键词表
keywords (id, keyword_zh, keyword_th, search_volume, trend, category, created_at)
-- 图片资产表（存储 OSS key）
image_assets (id, product_id, original_url, oss_key, type, status, hash, width, height, size, created_at)
-- 订单表（新增）
orders (id, shopee_order_sn, product_id, shop_id, order_amount_thb, platform_fee, actual_profit,
order_status, buyer_note, created_at, updated_at)
-- 物流表（新增）
shipments (id, order_id, source_tracking_no, local_warehouse_no, shopee_sls_no, shipping_status, created_at)
-- 财务流水表（新增）
transactions (id, type, amount, currency, related_order_id, description, created_at)
-- 风控拦截日志（新增）
risk_logs (id, product_id, risk_type, risk_detail, action_taken, created_at)
-- 系统配置表
settings (id, shop_id, config_key, config_value_json, config_type, description, updated_at)
-- 审计日志表
audit_logs (id, user_id, action, resource_type, resource_id, detail_json, ip_address, created_at)
-- 错误日志表
error_logs (id, error_type, error_message, stack_trace, context_json, resolved, created_at)
-- 利润校准表（新增）
profit_calibration (id, shop_id, category_id, estimated_profit, actual_profit, deviation, created_at)
```

### 5.2 索引建议

```sql
-- 商品表索引
CREATE INDEX idx_products_shop_status ON products (shop_id, status);
CREATE INDEX idx_products_risk_status ON products (risk_status);
CREATE INDEX idx_products_source ON products (source_platform, source_item_id);

-- 上架记录索引
CREATE INDEX idx_listings_product ON listings (product_id);
CREATE INDEX idx_listings_shopee ON listings (shopee_item_id);

-- 风控日志索引
CREATE INDEX idx_risk_logs_product ON risk_logs (product_id);
CREATE INDEX idx_risk_logs_created ON risk_logs (created_at);

-- 翻译缓存索引
CREATE INDEX idx_translates_hash ON translates (source_text_hash);

-- 利润校准索引
CREATE INDEX idx_profit_calibration_shop ON profit_calibration (shop_id, created_at);
```

---

## 六、定时任务与容错

### 6.1 定时任务清单（新增财务相关）

| 时间 | 任务名称 | 频率 | 备注 |
|------|----------|------|------|
| 00:00 | 日结对账（含财务） | 每日 | 生成昨日利润报表，核对 Shopee 账单 |
| 02:00 | 汇率更新与告警 | 每日 | CNY→THB，波动>2%触发紧急告警 |
| 03:00 | 数据库全量备份 | 每日 | 备份到 OSS |
| 04:00 | 日志轮转 | 每日 | 压缩归档，删除>30天 |
| 06:00 | 库存同步 | 用户配置 | 拉取货源库存，更新 Shopee |
| 08:00 | 销量排行扫描 | 用户配置 | Top N 分析 |
| 10:00 | 搜索趋势更新 | 用户配置 | 关键词趋势 |
| 12:00 | 竞品检查 | 用户配置 | 价格/销量追踪，大幅波动告警 |
| 15:00 | 销量排行扫描 | 用户配置 | 第2次 |
| 18:00 | 竞品检查 | 用户配置 | 第2次 |
| 20:00 | 关键词更新 | 用户配置 | 第2次 |
| 22:00 | 缺货/利润熔断下架 | 每日 | 自动下架零库存及利润率不达标的商品 |
| 23:00 | 日报推送（含财务汇总） | 每日 | Telegram/邮件推送 |

### 6.2 任务状态机与幂等性

- 每个任务定义状态：`pending → running → success/failed`
- 使用 Redis 分布式锁防止重复执行（`lock:task:{name}:{date}`）
- 库存同步使用版本号（`version`）防止并发覆盖
- 上架任务使用 `shopee_item_id` 唯一约束避免重复创建

### 6.3 任务失败重试策略

| 任务类型 | 重试次数 | 间隔 | 最终失败动作 |
|----------|----------|------|--------------|
| 库存同步 | 3 | 5s,30s,2min | 记录 ERROR，次日重试 |
| 竞品检查 | 3 | 1min,5min,15min | 跳过本次 |
| 汇率更新 | 2 | 1min,5min | 使用缓存汇率，告警 |
| 上架执行 | 5 | 1min,2min,4min,8min,16min | 标记失败，人工介入 |
| 图片翻译 | 2 | 30s,2min | 跳过该图，标记待人工 |
| 财务核算 | 2 | 1min,5min | 使用上次估值，告警 |

---

## 七、API 设计详规

### 7.1 通用规范

- **基础路径**：`/api/v1`
- **鉴权**：Bearer JWT（Access Token 2h，Refresh Token 7d）
- **响应格式**：`{"code":0, "message":"success", "data":{}, "timestamp":xxx}`

### 7.2 核心 API 端点（扩展版）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录 |
| POST | `/api/auth/refresh` | 刷新 Token |
| GET | `/api/shops` | 店铺列表 |
| POST | `/api/shops` | 添加店铺 |
| GET | `/api/products` | 商品列表（分页、筛选） |
| POST | `/api/products` | 导入商品（支持 URL 或手动） |
| POST | `/api/products/{id}/translate` | 触发 LangGraph 翻译工作流 |
| POST | `/api/products/{id}/finance/check` | 手动利润核算 |
| GET | `/api/audit` | 审核队列 |
| POST | `/api/audit/{id}/approve` | 审核通过 |
| POST | `/api/audit/{id}/reject` | 审核拒绝 |
| POST | `/api/listings` | 创建上架任务 |
| GET | `/api/listings` | 上架记录 |
| POST | `/api/listings/{id}/retry` | 手动重试 |
| GET | `/api/competitors` | 竞品列表 |
| POST | `/api/competitors/check` | 触发竞品检查 |
| GET | `/api/reports/daily` | 日报（含财务） |
| GET | `/api/reports/finance` | 财务对账报表 |
| GET | `/api/reports/profit-calibration` | 利润校准报告 |
| PUT | `/api/settings` | 更新配置（含熔断阈值） |
| POST | `/api/media/upload` | 上传图片（返回 OSS key） |

### 7.3 Webhook 接收端点（新增）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/webhook/shopee/order` | 接收订单状态变更 |
| POST | `/webhook/shopee/chat` | 接收买家聊天消息 |
| POST | `/webhook/shopee/review` | 接收评价推送 |

---

## 八、错误码与告警体系

### 8.1 业务错误码（部分）

| 错误码 | 说明 | HTTP |
|--------|------|------|
| 0 | 成功 | 200 |
| 1001 | 参数错误 | 400 |
| 1003 | 权限不足 | 403 |
| 1004 | Token 无效 | 401 |
| 2001 | 商品导入失败 | 500 |
| 2002 | 翻译服务不可用 | 503 |
| 2003 | 图片处理失败 | 500 |
| 3001 | Shopee API 失败 | 502 |
| 3002 | Shopee 限流 | 429 |
| 4001 | 库存不足 | 400 |
| 5001 | 数据库异常 | 500 |
| **6001** | **利润低于阈值（熔断）** | **400** |
| **6002** | **风控拦截（品牌/违禁）** | **400** |

### 8.2 告警级别与策略（扩展）

| 错误类型 | 级别 | 通知方式 | 自动处理 |
|----------|------|----------|----------|
| Shopee API 连续失败 3 次 | P0 | Telegram+邮件 | 暂停上架任务 |
| **汇率波动 >2%** | **P0** | **Telegram+短信** | **暂停所有自动上架** |
| **利润率低于红线** | **P1** | **Telegram** | **自动下架/暂停** |
| **品牌词/违禁词命中** | **P1** | **Dashboard 弹窗** | **记录 risk_logs，阻断** |
| 上架失败 >5 次 | P1 | Telegram | 人工介入 |
| 图片翻译连续失败 3 张 | P1 | Telegram | 暂停该商品处理 |
| 库存低于阈值 | P2 | 日报 | - |
| 竞品价格大幅下降 | P2 | Telegram | 提示调价 |
| 翻译置信度低 | P3 | 日志 | 标记人工审核 |
| API 限流 (429) | P1 | Telegram | 指数退避 |

**告警收敛**：相同告警 30 分钟内不重复发送（Redis 去重）。

---

## 九、API 速率控制策略

### 9.1 Shopee API

- QPS 限制：按 10 QPS 保守配置（桶容量 20，填充 10/s）
- 重试：指数退避（1s→2s→4s→8s→16s）
- 连续失败 10 次告警，暂停该端点 5 分钟
- 端点分级：查询类 10 QPS，写入类 5 QPS，图片上传 3 QPS

### 9.2 1688 API

- QPS：10，重试同上

### 9.3 拼多多 API

- QPS：15，重试同上

### 9.4 全局动态限流

- Redis + Lua 脚本实现分布式限流
- 不同端点独立配额，共享全局令牌池
- 限流时返回 `Retry-After` 头

---

## 十、国际化/本地化

### 泰语支持

- 字体：TH Sarabun New, Lekton, Noto Sans Thai
- 字符宽度动态计算，变音符号正常渲染
- 泰语电商语料库（包邮、正品、折扣等常用词）

### 汇率管理

- CNY → THB 每日更新（中国人民银行 + 泰国银行交叉验证）
- 失败使用缓存，标注"缓存数据"

### 多站点预留

- 数据库 `shops.platform` 字段支持 `shopee_vn`, `shopee_ph` 等
- 翻译模板按语言分离（`th`, `vi`, `id`）

---

## 十一、日志与监控

### 11.1 日志级别

- DEBUG（开发）、INFO、WARNING、ERROR、CRITICAL
- **敏感信息脱敏**：API Key、Token、密码自动替换为 `***`

### 11.2 日志轮转

- 按天轮转，保留 30 天，超过自动压缩归档
- 单文件最大 100MB

### 11.3 业务指标监控（Prometheus）

| 指标 | 类型 | 说明 |
|------|------|------|
| `products_imported_total` | Counter | 导入商品数 |
| `listings_success_total` | Counter | 上架成功数 |
| `listings_failed_total` | Counter | 上架失败数 |
| `translation_duration_seconds` | Histogram | 翻译耗时 |
| `image_process_duration_seconds` | Histogram | 图片处理耗时 |
| `api_call_total` | Counter | 外部 API 调用数 |
| `api_call_errors_total` | Counter | 外部 API 错误数 |
| `queue_depth` | Gauge | Celery 队列深度 |
| `active_products` | Gauge | 在售商品数 |
| **`profit_margin_avg`** | **Gauge** | **平均利润率** |
| **`risk_intercepts_total`** | **Counter** | **风控拦截总数** |
| **`profit_calibration_deviation`** | **Histogram** | **利润预估偏差分布** |

### 11.4 健康检查

- `GET /api/health` 返回各组件状态（数据库、Redis、LLM、Shopee API、OSS）
- 任何失败返回 503

---

## 十二、安全设计

### 12.1 API 鉴权

- JWT（Access 2h + Refresh 7d）
- API Key 加密存储（AES-256）
- 请求签名（HMAC-SHA256）防重放
  - **nonce**：每次请求生成随机字符串，存入 Redis，TTL 300 秒
  - **校验**：服务端检查 nonce 是否已使用，使用后立即删除

### 12.2 Web 安全

- CSRF 防护（SameSite Cookie + 双提交 Token）
- XSS 防护（HTML 转义 + CSP）
- SQL 注入防护（ORM 参数化）
- CORS 限制域名

### 12.3 数据加密

- 密码 bcrypt 哈希
- API Key AES-256-CBC 加密
- 传输层强制 TLS 1.3

### 12.4 权限控制（RBAC）

- **admin**：全部权限
- **operator**：商品导入、审核、上架、查看报表
- **viewer**：只读查看

### 12.5 IP 白名单

- Shopee 回调 IP 白名单
- Dashboard 管理后台 IP 白名单（可选）

### 12.6 密钥管理

- 生产环境使用 HashiCorp Vault 或 AWS Secrets Manager

---

## 十三、测试策略

### 13.1 测试层级

| 层级 | 工具 | 覆盖率目标 |
|------|------|-----------|
| 单元测试 | pytest + pytest-cov | ≥80% |
| 集成测试 | pytest + testcontainers | ≥70% |
| E2E 测试 | playwright | 核心流程覆盖 |
| 性能测试 | locust | 100 并发，API <500ms |
| 压力测试 | locust | 验证限流降级 |

### 13.2 外部依赖 Mock

- Shopee：沙箱环境
- 1688/拼多多：Mock 服务器（responses）
- LLM：固定模板回复
- LangGraph：使用 `langgraph.checkpoint.memory.MemorySaver` 进行单元测试

### 13.3 CI/CD

- GitHub Actions / GitLab CI 自动运行测试
- 测试通过合并 main
- 每日凌晨自动 E2E 测试

---

## 十四、硬件资源与部署评估

由于 AI 翻译和图片处理是算力密集型任务，生产环境需明确硬件要求：

| 节点角色 | 推荐配置 | 说明 |
|----------|----------|------|
| **API & Dashboard** | 2C 4G（普通 CPU） | 运行 FastAPI、Next.js、PostgreSQL、Redis |
| **Worker (图片/OCR)** | 4C 8G（高并发 CPU） | 运行 Celery、PaddleOCR、OpenCV 图片合成 |
| **LLM 推理（若本地部署）** | 8C 32G + **RTX 4090/A10 GPU** | 运行本地 Qwen 模型。若使用云端 API (DashScope)，则无需 GPU。 |

**初期建议**：使用云端 LLM API（DashScope）以降低硬件成本，待业务量增长后再考虑本地 GPU 部署。

---

## 十五、成本估算（月度）

### 15.1 单商品处理成本（不含服务器）

| 项目 | 单价 | 用量/商品 | 小计 |
|------|------|----------|------|
| LLM 翻译（云端 API） | 0.002 元/千 token | ~500 token | 0.001 元 |
| OCR（本地） | 0 | - | 0 |
| 图片存储（OSS） | 0.12 元/GB/月 | 2MB/商品 | 0.00024 元/月 |
| Shopee API 调用 | 免费 | - | 0 |
| **合计** | **~0.001 元/商品** | | |

### 15.2 服务器成本（参考）

| 环境 | 配置 | 月费用 |
|------|------|--------|
| 开发/测试 | 4C 8G | ~300 元 |
| 生产（MVP） | 8C 16G + 100GB OSS | ~800 元 |
| 生产（扩展） | 16C 32G + 1TB OSS | ~2000 元 |

若使用云端 LLM API，需额外支付约 0.002 元/商品（1万商品约 20 元）。

---

## 十六、数据备份与灾难恢复

### 16.1 备份策略

| 数据 | 频率 | 保留 | 位置 |
|------|------|------|------|
| PostgreSQL | 每日 03:00 全量 + WAL 增量 | 7天本地 + 30天云 | 本地 + OSS |
| Redis | 每日 04:00 RDB | 7天 | 本地 |
| OSS 图片 | 版本控制 | 永久 | OSS 跨区域复制 |
| 配置文件 | Git 提交 | 永久 | Git 仓库 |

### 16.2 恢复流程

- 数据库：`pg_restore` 恢复，RPO ≤ 24h
- Redis：加载 RDB
- 图片：从 OSS 版本回滚

### 16.3 降级方案

| 故障 | 降级动作 |
|------|----------|
| LLM 不可用 | 使用缓存翻译或保留中文（标记） |
| Shopee API 不可用 | 暂停上架，队列积累 |
| 数据库不可用 | 切换只读副本或 SQLite 缓存 |
| OSS 不可用 | 回退本地存储（临时） |

---

## 十七、性能与扩展性

### 17.1 吞吐量目标

- 单日处理商品数：≥1000（MVP），目标 5000
- API 响应时间：P95 <200ms，P99 <500ms
- 图片翻译平均耗时：<30s/商品

### 17.2 水平扩展方案

- API 无状态，可多实例 + Nginx 负载均衡
- Celery Worker 按队列类型独立扩展（翻译队列优先）
- PostgreSQL 主从复制，读分离
- Redis Cluster 高可用

### 17.3 瓶颈优化

| 瓶颈 | 优化 |
|------|------|
| OCR/图片合成 | GPU 加速（CUDA）或独立 Worker 池 |
| LLM 推理 | 使用 vLLM 框架，批处理 |
| Shopee 限流 | Redis 分布式限流，请求排队 |
| 数据库写入 | 批量写入，读写分离 |

---

## 十八、开发优先级（Phase 规划）

> **V4.0 调整说明**：根据分析建议，将财务风控提前到 Phase 2，图片翻译延后到 Phase 3，Webhook 延后到 Phase 4。

### Phase 0 — 基础架构（第1-2周）

- [ ] 项目初始化，Docker Compose（PostgreSQL + Redis + MinIO）
- [ ] 用户认证与店铺管理
- [ ] 基础配置管理
- [ ] 数据库迁移（Alembic）
- [ ] **LangGraph 工作流框架搭建**

### Phase 1 — MVP 核心闭环（第3-6周）

- [ ] 数据采集（1688 API + 基础反爬代理池）
- [ ] 基础翻译（标题+描述，接入 DashScope/本地 Qwen via LangGraph）
- [ ] Shopee 商品创建 API（含图片异步轮询）
- [ ] Web Dashboard（商品列表 + 审核队列 + 上架记录）
- [ ] 审核队列（人工/自动）
- [ ] 基础日报

### Phase 2 — 财务风控 + 对象存储（第7-10周）⭐ **核心壁垒，提前至此**

- [ ] **财务利润核算模型与熔断机制**
- [ ] **利润校准模块（历史利润学习）**
- [ ] **敏感词库与品牌侵权拦截（含 OCR 识别 Logo）**
- [ ] 类目错放检测
- [ ] **接入 OSS 对象存储，替换本地 data/images**
- [ ] 热销品获取与竞品监控
- [ ] 定价建议模块

### Phase 3 — 图片翻译 + 变体（第11-14周）

- [ ] OCR 图片文字提取 + 图片合成（文本覆盖）
- [ ] 变体（规格/SKU）处理与映射
- [ ] 图片去水印、白底抠图
- [ ] 图片质量评估（PSNR）

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

## 十九、技术依赖清单

### Python 依赖（`requirements.txt`）

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
langgraph>=0.0.30          # LangGraph 工作流编排
dashscope>=1.14.0           # 阿里通义千问
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
boto3>=1.34.0               # AWS S3
aiobotocore>=2.11.0         # MinIO 异步
playwright>=1.40.0          # 反爬
pytest>=7.4.3
pytest-cov>=4.1.0
pytest-asyncio>=0.21.1
locust>=2.20.0
```

> **V4.0 变更说明**：
> - 版本号改为 `>=` 而非精确锁定，方便安全补丁更新
> - 新增 `langgraph>=0.0.30` 依赖
> - Celery Worker 的 `requirements.txt` 应与 `api/` 分开，避免不必要的依赖

### Node.js 依赖（Dashboard）

```
next: 14.x
react: 18.x
tailwindcss: 3.x
shadcn/ui: 最新
react-query: 5.x
axios: 1.x
zustand: 4.x
next-auth: 4.x
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

## 二十、项目目录结构

```text
pipixia/
├── api/                          # FastAPI 后端
│   ├── main.py
│   ├── config.py
│   ├── models/                   # SQLAlchemy 模型
│   │   ├── user.py, shop.py, product.py, listing.py, ...
│   ├── schemas/                  # Pydantic 模型
│   ├── routers/                  # API 路由
│   │   ├── auth.py, shops.py, products.py, listings.py, audit.py,
│   │   ├── competitors.py, reports.py, settings.py, media.py
│   │   └── webhooks.py           # Webhook 接收端点
│   ├── services/                 # 业务逻辑
│   │   ├── crawler/              # 数据采集（含反爬代理池）
│   │   │   ├── base.py, shopee.py, alibaba.py, pdd.py, proxy_pool.py
│   │   ├── ai_engine/            # AI 翻译（LangGraph 编排）
│   │   │   ├── translator_graph.py  # LangGraph 工作流定义
│   │   │   ├── translator.py        # 翻译节点实现
│   │   │   ├── image_translate.py   # 图片翻译
│   │   │   ├── seo_optimizer.py     # SEO 优化
│   │   │   └── cache.py             # 翻译缓存
│   │   ├── finance/              # 财务核算与熔断
│   │   │   ├── profit_calculator.py
│   │   │   └── profit_calibration.py  # 利润校准
│   │   ├── risk/                 # 风控、违禁词、侵权检测
│   │   │   ├── word_filter.py, brand_detector.py, category_validator.py
│   │   ├── listing/              # 上架执行（含图片异步轮询）
│   │   │   ├── creator.py, updater.py, shopee_api.py
│   │   ├── monitor/              # 竞品/库存监控
│   │   ├── report/               # 日报生成
│   │   └── storage/              # OSS/S3/MinIO 统一接口
│   ├── middleware/               # 鉴权、限流、日志
│   ├── utils/                    # 工具（加密、JWT、图片处理）
│   └── requirements.txt
│
├── worker/                       # Celery 后台任务
│   ├── celery_app.py
│   ├── tasks.py                  # 所有任务定义
│   └── requirements.txt          # 精简依赖，不含 API 无关包
│
├── dashboard/                    # Next.js Dashboard
│   ├── src/
│   │   ├── app/                  # 页面路由
│   │   ├── components/           # UI 组件
│   │   ├── lib/                  # API 客户端、hooks
│   │   └── styles/
│   └── package.json
│
├── migrations/                   # Alembic 迁移
├── data/                         # 本地临时缓存（生产禁用，仅开发）
├── config/                       # 配置文件
│   ├── settings.yaml
│   ├── llm.yaml
│   ├── categories.yaml
│   ├── risk_words.json           # 违禁词/品牌词库
│   └── prompts.yaml
├── scripts/                      # 运维脚本（初始化、备份、恢复）
├── tests/                        # 单元/集成/E2E测试
├── docker-compose.yml
├── .env.example
├── Makefile
└── README.md
```

---

## 二十一、附录：用户快速启动指南

### 21.1 首次启动（Docker）

```bash
git clone https://github.com/yourteam/pipixia.git
cd pipixia
cp .env.example .env
# 编辑 .env，填入数据库密码、Shopee API Key、OSS 配置等
docker-compose up -d
docker-compose exec api python scripts/init_db.py
docker-compose exec api python scripts/create_admin.py --username admin --password xxx
# 访问 http://localhost:3000
```

### 21.2 配置店铺

1. 登录 Dashboard → 店铺管理 → 添加店铺
2. 选择平台（Shopee 泰国），填入店铺名称和 API Token
3. 验证连接，保存。

### 21.3 第一个商品上架

1. 商品管理 → 导入商品 → 粘贴 1688 链接
2. 系统自动执行：采集 → LangGraph AI 编排（缓存→风控→翻译→本地化→SEO） → 财务核算
3. 进入审核队列，查看结果（若利润不足或风控命中会显示）
4. 若通过，点击"通过"自动上架。
5. 查看上架记录确认成功。

### 21.4 日常运营建议

- 每日查看"财务日报"监控利润
- 关注"风控日志"及时处理拦截项
- 定期更新敏感词库
- 检查"竞品监控"调整定价
- 查看"利润校准"报告，了解预估 vs 实际的偏差

---

## 附：V4.0 修订记录

| 版本 | 日期 | 修订内容 |
|------|------|----------|
| V3.0 | 2026-07-02 | 初始合并版，整合财务风控、反爬、Webhook、对象存储等模块 |
| **V4.0** | **2026-07-04** | **1. 引入 LangChain + LangGraph 作为 AI 编排工具<br>2. 重构 AI 翻译模块为 LangGraph 有向图工作流<br>3. 开发优先级调整：财务风控提前到 Phase 2，图片翻译延后到 Phase 3<br>4. 数据库新增 profit_calibration 表和索引建议<br>5. 依赖版本改为 >= 而非精确锁定<br>6. 安全设计补充 HMAC-SHA256 nonce 存储和过期策略<br>7. 新增利润校准模块和历史利润学习功能<br>8. Celery Worker 依赖与 API 分离** |

---

**本文档为 V4.0 完整版**，整合了 LangChain + LangGraph AI 工作流编排、修订后的开发优先级、数据库索引优化、安全加固等所有改进。可作为正式立项及开发的参考。如需进一步细化某一模块（如具体 Prompt 模板、Shopee 完整字段映射表、LangGraph 节点实现细节），可继续补充。

祝 pipixia 项目顺利上线！🚀
