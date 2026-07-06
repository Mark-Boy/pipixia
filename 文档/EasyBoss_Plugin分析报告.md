# EasyBoss ERP Chrome 插件分析报告

> **分析日期**：2026-07-06  
> **版本**：V1.3.4  
> **插件类型**：Chrome Extension (Manifest V3)  
> **用途**：跨境电商商品数据采集工具（从货源平台采集商品信息推送到 EasyBoss ERP）

---

## 一、插件架构概览

### 1.1 技术栈

| 技术 | 说明 |
|------|------|
| Manifest V3 | Chrome 扩展最新规范 |
| Service Worker | background.js 使用 SW 替代旧版 background page |
| Content Scripts | 注入到所有电商网站，执行采集逻辑 |
| jQuery 3.x | DOM 操作和 AJAX |
| Bootstrap 3.3.4 | Popup 弹窗样式 |
| Layer 3.0.1 | 轻量级弹窗组件 |
| Webpack 5 | 模块化打包（output chunk 命名：easyboss_chrome_extension） |
| Underscore 1.8.3 | 工具函数库 |
| MD5 | 加密工具 |
| i18n | 14 种语言国际化 |

### 1.2 核心通信架构

```
┌─────────────────────────────────────────────────────────┐
│                   Chrome Extension                       │
│                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────┐ │
│  │ Background    │    │ Content      │    │ Popup      │ │
│  │ Script (SW)   │◄──►│ Script       │    │ (UI)       │ │
│  │               │    │ (注入页面)    │    │            │ │
│  └──────┬───────┘    └──────┬───────┘    └────────────┘ │
│         │                   │                             │
│         ▼                   ▼                             │
│  ┌──────────────┐    ┌──────────────┐                     │
│  │ ERP Server   │    │ 电商网站      │                     │
│  │ plw.jiancent │    │ (1688等)     │                     │
│  │ .com          │    │              │                     │
│  └──────────────┘    └──────────────┘                     │
└─────────────────────────────────────────────────────────┘
```

### 1.3 文件结构

```
EasyBoss ERP - Plugin/
├── manifest.json                  # 扩展清单 (MV3, 117 个 content_script 匹配规则)
├── background.js                  # Service Worker (极简，转发消息)
├── popup.html                     # 插件弹出窗口
├── js/
│   ├── jquery.js                  # DOM/AJAX 库
│   ├── underscore-1.8.3.min.js    # 工具函数
│   ├── lib.js                     # 运行时库
│   ├── md5.js                     # 加密
│   ├── ric_plugin.js              # RIC 插件核心（i18n/存储/通信）
│   ├── popup.js                   # Popup 逻辑
│   ├── bootstrap/                 # Bootstrap JS
│   ├── layer-3.0.1/               # Layer 弹窗
│   ├── biz/
│   │   ├── common/
│   │   │   ├── common_tool.js     # 平台 URL 解析器（核心）
│   │   │   ├── common_util.js     # 通用工具
│   │   │   └── fetch_tool.js      # 采集工具（反爬/页面数据获取）
│   │   ├── platform/
│   │   │   ├── platform-base.js   # 基类 PlatBase（核心引擎）
│   │   │   ├── platform-hook-config.js  # 钩子配置
│   │   │   ├── platform-1688.js   # 1688 平台适配
│   │   │   ├── platform-shopee.js # Shopee 平台适配
│   │   │   ├── platform-amazon.js # Amazon
│   │   │   ├── platform-aliexpress.js
│   │   │   ├── platform-lazada.js
│   │   │   └── ... (50+ 平台适配文件)
│   │   └── platform/inject/       # 动态注入脚本
│   │       ├── platform-1688-inject.js
│   │       ├── platform-shopee.js
│   │       └── ...
├── css/
│   ├── niuniu.css                 # 插件样式
│   └── bootstrap.css              # Bootstrap 样式
├── _locales/                      # 14 种语言翻译
│   ├── en/messages.json
│   ├── zh_CN/messages.json
│   ├── th/messages.json
│   └── ...
└── images/                        # 图标资源
```

---

## 二、核心功能分析

### 2.1 数据采集流程

```
用户在电商网站浏览商品
        │
        ▼
插件检测当前 URL → 匹配平台类型
        │
        ▼
注入采集按钮到页面（底部工具栏 / 侧边栏）
        │
        ├─ 单商品采集 → 提取标题/图片/价格/SKU → 推送至 ERP
        ├─ 列表页采集 → 遍历所有商品链接 → 批量提取
        ├─ 翻页采集 → 自动滚动/点击下一页 → 持续采集
        └─ 选中采集 → 用户勾选商品 → 批量采集
        │
        ▼
反爬检测（登录态/验证码/数据完整性）
        │
        ▼
通过 API 推送到 EasyBoss ERP Server
        │
        ▼
ERP 服务器处理并存储
```

### 2.2 支持的货源平台（50+ 个）

| 类别 | 平台 | 说明 |
|------|------|------|
| **核心货源** | 1688, 拼多多(17qcc/17zwd), 义乌购, 搜款网, 包牛牛, 杭州南油 | 服装/批发 |
| **跨境货源** | Alibaba, DHgate, Gigab2b, SaleYee, 五三外贸 | B2B 批发 |
| **跨境销售** | Shopee, Lazada, AliExpress, Amazon, eBay, TikTok Shop, Temu, Shein | 销售平台 |
| **其他国内** | 苏宁, 当当, 唯品会, 京东, 天猫, 考拉, 小红书 | 多平台比价 |
| **东南亚** | Daraz, Jumia, Coupang, Ozon | 区域市场 |
| **小众/垂直** | Etsy, Allegro, Walmart, Joom,  Kongfz(孔夫子) | 特色平台 |

### 2.3 核心引擎 — PlatBase（platform-base.js）

**这是整个插件的心脏**，负责：

#### 2.3.1 链接类型检测

```javascript
// 判断当前页面是列表页还是详情页
getLinkTypeByRule(n) {
    // linkTypeRuleList: [{type: "detail", indexOfList: [...]}, {type: "list", ...}]
    // 匹配 URL 模式 → 确定采集模式
}
```

#### 2.3.2 工具栏 UI 构建

```javascript
buildDetailFetchToolBox()   // 详情页：单个商品采集按钮
buildListFetchToolBox()     // 列表页：全选/本页/选中/翻页采集
buildSidebarToolBox()       // 侧边栏模式（可切换底部/侧边栏）
```

#### 2.3.3 列表页商品链接提取

```javascript
buildListFetchBtn() {
    // 遍历页面所有 <a> 标签
    // 匹配商品链接规则 → 叠加采集浮层
    // 鼠标悬停显示"采集此商品"按钮
    // 支持点击圆形选择器多选
}
```

#### 2.3.4 登录态检查

```javascript
checkLogin() {
    // 检查所有已绑定 ERP 店铺是否已登录
    // 未登录 → 弹出授权引导
}
```

#### 2.3.5 数据采集推送

```javascript
processFetchItem(selectedItemsMap) {
    // 1. 检查 ERP 登录状态
    // 2. 选择采集模式：collectBox（推送到ERP）/ copy（复制链接）
    // 3. 批量推送商品数据到 ERP Server
    // 4. 显示采集结果弹窗
}
```

### 2.4 URL 解析器（common_tool.js）

**这是最核心的数据结构之一** — 定义了所有平台的 URL 正则表达式：

```javascript
getSourceInfoByItemUrl(itemUrl, sources) {
    // sources: ["1688"] 或 ["shopee"] 等
    // 返回: { itemId: "12345", source: "1688", site: "th" }
    
    // 每个平台一个正则，例如：
    // 1688: "(.*.1688.com/offer/|caigou.1688.com/detail/)(\\d+).htm"
    // shopee: "(?:https://|http://)(?:(?:(?:mall|my).)*)(shopee..*|.*.xiapibuy.com)/[^\\?]*[(?:-i.)|(?:product/)](\\d+[\\.|\\/]\\d+)"
    // lazada: "(www).lazada.(.*?)/products/.*-?i(\\d+(?:(-s\\d+)?)).html"
    // temu: "(www)(.)temu.com/?.*?(?:g-(\\d+).html|goods.html?.*goods_id=(\\d+))"
}
```

**关键洞察**：URL 解析器支持 **site 识别**（如 shopee.th, shopee.vn, lazada.my 等），这对于多站点 ERP 至关重要。

### 2.5 反爬机制（fetch_tool.js）

#### 2.5.1 反爬检测

```javascript
checkAndGetItemPageDataAntiCode(source, pageData) {
    // 根据平台类型检测反爬状态
    switch(source) {
        case "temu":
            // 检查是否登录、rawData 是否有效
        case "lazada":
        case "aliexpress":
            // 检查 x5secdata=（验证码）
        case "walmart":
            // 检查 Robot or human
        case "kwaixiaodian":
            // 检查需要验证
        case "shein":
            // 检查 needVerify
    }
}
```

#### 2.5.2 反爬处理

```javascript
processFetchItemAnti(source, antiCode, pageData) {
    // 根据不同平台和反爬类型显示不同提示
    // 例如：1688 未登录 → 跳转登录页
    // aliexpress 验证码 → 弹出 iframe 让用户手动验证
    // temu 账号异常 → 提示降低采集频率
}
```

#### 2.5.3 页面数据获取

```javascript
getPlatformPageDataFromCurrentPage(source) {
    // 根据不同平台获取页面数据的策略：
    // - 1688: 从 DOM 提取
    // - Shopee: 从 <script text/mfe-initial-data> 提取 JSON
    // - Lazada: 从 __moduleData__ 变量提取
    // - AliExpress: 从 API 获取 + 滚动加载详情
    // - Temu: 从 window.rawData 提取
    // - Amazon: 从页面脚本提取 SKU 信息
}
```

### 2.6 1688 平台特殊处理（platform-1688.js）

1688 是最复杂的平台，因为：

1. **API 签名**：实现了完整的 RSA/MD5 签名算法（模拟 1688 的 mtop API）
2. **列表页**：通过 AJAX 调用 `h5api.m.1688.com` 获取商品列表
3. **详情页**：从 DOM 直接提取
4. **动态注入**：使用 `chrome.runtime.getURL()` 注入 content script

```javascript
getAlibabaCategoryParameter(page, href, i) {
    // 构造 1688 mtop API 请求参数
    // 签名算法：MD5(token + t + appKey + dataStr)
    // 返回: { dataStr, pageUrl }
}

fetchItemListFromApi(callback) {
    // 调用 1688 mtop API 获取商品列表
    // 处理 cookie (_m_h5_tk) 中的 token
}

getSign(token, t, dataStr) {
    // 实现 1688 的签名算法（MD5 变种）
}
```

### 2.7 Shopee 平台特殊处理（platform-shopee.js）

1. **页面数据提取**：从 `<script text="mfe-initial-data">` 标签提取 JSON
2. **动态注入**：注入 `platform-shopee.js` 到页面获取完整数据
3. **SKU 处理**：自动处理变体数据
4. **采集限制**：Shopee 详情页不支持采集库存（提示用户）

### 2.8 ERP 服务端通信

**服务端地址**：`https://plw.jiancent.com`（即 EasyBoss ERP）

| API 端点 | 方法 | 用途 |
|----------|------|------|
| `/open/niu/check_login` | POST | 检查 ERP 登录状态 |
| `/open/niu/push_collect_box` | POST | 推送商品到 ERP |
| `/open/niu/check_item_has_fetch` | POST | 检查商品是否已采集 |
| `/open/niu/get_auth_url` | GET | 获取授权 URL |
| `/open/fetch/pfti` | POST | 推送采集页面数据 |
| `/open/common/download_item_urls` | POST | 下载采集的商品链接 |
| `/open/common/format_item_urls` | POST | 格式化商品链接 |
| `/open/fetch/push_fil` | POST | 推送采集日志 |

**推送数据格式**：
```json
{
    "isAutoPublish": 0,
    "itemSimpleDetails": [
        {
            "source": "1688",
            "site": "th",
            "itemId": "12345",
            "itemUrl": "https://detail.1688.com/offer/12345.html",
            "title": "商品标题",
            "itemImg": "图片URL",
            "price": 39.9
        }
    ]
}
```

---

## 三、与 pipixia 项目的对比分析

### 3.1 功能重叠与差异

| 功能 | EasyBoss 插件 | pipixia | 差异分析 |
|------|-------------|---------|----------|
| **商品采集** | ✅ 50+ 平台 | ⬜ 待实现 | pipixia 需实现爬虫 |
| **URL 解析** | ✅ 正则表达式 | 🟡 部分 | pipixia 仅 1688/PDD |
| **翻译** | ❌ 无 | ✅ DashScope | pipixia 独有 |
| **审核** | ❌ 无 | ✅ 审核队列 | pipixia 独有 |
| **上架** | ❌ 无 | ✅ Shopee API | pipixia 独有 |
| **利润核算** | ❌ 无 | ✅ 含佣金/物流 | pipixia 独有 |
| **风控** | ❌ 无 | ✅ 敏感词库 | pipixia 独有 |
| **图片翻译** | ❌ 无 | ⬜ 待实现 | 都未实现 |
| **ERP 服务端** | ✅ jiancent.com | ⬜ 自建 | pipixia 需自建 |

### 3.2 pipixia 可借鉴的关键设计

#### 1. URL 解析器模式（最核心价值）

EasyBoss 的 `common_tool.js` 中定义了 **50+ 平台的 URL 正则**，这是 pipixia 最急需补齐的能力：

```javascript
// 可参考的正则模式（1688）
"1688": "(.*.1688.com/offer/|caigou.1688.com/detail/)(\\d+).htm"

// 可参考的正则模式（拼多多）
"yangkeduo": "//(.*?)weidian.com/item.html.*?itemID=([^&]*)"

// 可参考的正则模式（Shopee）
"shopee": "(?:https://|http://)(?:(?:(?:mall|my).)*)(shopee..*|.*.xiapibuy.com)/[^\\?]*[(?:-i.)|(?:product/)](\\d+[\\.|\\/]\\d+)"
```

#### 2. 平台适配模式

每个平台的适配文件遵循统一模式：
- `platformConfig` 对象定义平台特定的采集规则
- `init()` 方法初始化
- 注入按钮到页面
- 监听按钮事件执行采集

#### 3. 反爬处理模式

- 检测登录态
- 检测验证码
- 分级处理（提示用户 / 自动跳过 / 暂停采集）

#### 4. 多站点识别

Shopee/Lazada/Daraz 等平台的多站点识别逻辑非常成熟：
```javascript
// Shopee 站点映射
var s = {xiapi:"tw", "co.id":"id", "co.th":"th", "com.my":"my", ...}
```

### 3.3 pipixia 的差异化优势

| 维度 | EasyBoss | pipixia |
|------|----------|---------|
| **定位** | 纯数据采集工具 | 全链路 ERP 系统 |
| **翻译** | ❌ | ✅ LLM 翻译（DashScope） |
| **审核** | ❌ | ✅ 人工审核队列 |
| **上架** | ❌ | ✅ Shopee API 上架 |
| **财务** | ❌ | ✅ 利润核算 + 熔断 |
| **风控** | ❌ | ✅ 敏感词库 + 品牌词检测 |
| **部署** | SaaS（云端） | 私有化部署 |
| **技术栈** | jQuery + Content Script | FastAPI + Next.js |

---

## 四、pipixia 可落地的改进方案

### 4.1 立即实施：URL 解析器

将 EasyBoss 的 URL 正则提取到 pipixia：

```python
# api/services/url_parser.py
PLATFORM_URL_PATTERNS = {
    "1688": r"(.*\.1688\.com/offer/|caigou\.1688\.com/detail/)(\d+)\.htm",
    "pinduoduo": r"(.*\.pinduoduo\.com/.*?|.*\.yangkeduo\.com/.*?)(?:id=|/)(\d+)",
    "shopee": r"(?:shopee\..*|.*\.xiapibuy\.com)/[^\\?]*[(?:-i\.)|(?:product/)](\d+[\.\/]\d+)",
    "lazada": r"(www)\.lazada\.(.*?)/products/.*-?i(\d+)",
    "amazon": r"(?:www\.)?amazon\.([\w\.]+)/(?:dp|gp/product|gp/aw/d)/(\w+)",
    "aliexpress": r"(?:https?://)?(.*)aliexpress\.(.*)/item/(?:id/)?(\d+)\.html",
    # ... 更多平台
}

SITE_MAP = {
    "shopee": {
        "shopee.co.th": "th",
        "shopee.co.id": "id",
        "shopee.ph": "ph",
        "shopee.com.my": "my",
        "shopee.sg": "sg",
    },
    "lazada": {
        "lazada.co.th": "th",
        "lazada.co.id": "id",
        "lazada.co.ph": "ph",
        "lazada.com.my": "my",
    },
}

def parse_platform_url(url: str) -> dict:
    """解析商品 URL，返回 {platform, site, item_id}"""
    for platform, pattern in PLATFORM_URL_PATTERNS.items():
        match = re.search(pattern, url)
        if match:
            item_id = match.group(match.lastindex)
            site = detect_site(url, platform)
            return {"platform": platform, "site": site, "item_id": item_id}
    return None
```

### 4.2 中期实施：Playwright 爬虫复用

EasyBoss 通过 Content Script 注入页面获取数据，pipixia 可以用 Playwright 实现类似效果：

```python
# worker/tasks.py 中的 import_product 任务
async def crawl_product(url: str, platform: str) -> dict:
    """使用 Playwright 抓取商品详情"""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")
        
        # 注入类似 EasyBoss 的数据提取逻辑
        if platform == "1688":
            # 从 DOM 提取标题/价格/图片/SKU
            data = await page.evaluate("""() => {
                return {
                    title: $('#mod-detail-title').text(),
                    price: $('.price-new-price').text(),
                    images: $('.vertical-img img').map((i, el) => $(el).attr('src')).get(),
                };
            }""")
        elif platform == "shopee":
            # 从 mfe-initial-data 脚本标签提取
            data = await page.evaluate("""() => {
                const script = document.querySelector('script[text="mfe-initial-data"]');
                return JSON.parse(script?.textContent || '{}');
            }""")
        
        await browser.close()
        return data
```

### 4.3 长期规划：ERP 服务端集成

如果 pipixia 需要对接 EasyBoss ERP 服务端：

```python
# api/services/easyboss_client.py
class EasyBossClient:
    BASE_URL = "https://plw.jiancent.com"
    
    def check_login(self) -> bool:
        """检查 ERP 登录状态"""
        resp = requests.post(f"{self.BASE_URL}/open/niu/check_login")
        return resp.json().get("result") == "success"
    
    def push_collect_box(self, items: list) -> dict:
        """推送商品到 ERP"""
        payload = {
            "isAutoPublish": 0,
            "itemSimpleDetails": items,
        }
        resp = requests.post(
            f"{self.BASE_URL}/open/niu/push_collect_box",
            json=payload,
        )
        return resp.json()
    
    def get_auth_url(self, platform: str) -> str:
        """获取授权 URL"""
        resp = requests.get(
            f"{self.BASE_URL}/open/niu/get_auth_url",
            params={"platform": platform},
        )
        return resp.json().get("authUrl")
```

---

## 五、安全风险分析

### 5.1 已发现的问题

| 风险 | 级别 | 说明 |
|------|------|------|
| **硬编码 API Key** | 🔴 高 | `SECRET_KEY` 写死在代码中 |
| **CORS 过于宽松** | 🟡 中 | `allow_origins=["http://localhost:3000"]` |
| **1688 API 签名泄露** | 🟡 中 | 前端暴露签名算法 |
| **Cookie 传输** | 🟡 中 | 1688 请求携带完整 Cookie |
| **未使用 HTTPS** | 🟢 低 | 部分资源通过 HTTP 加载 |

### 5.2 pipixia 的安全建议

1. **API Key 管理** — 使用环境变量 + 密钥管理服务（Vault）
2. **爬虫合规** — 遵守 robots.txt，控制请求频率
3. **数据脱敏** — 不存储用户密码，使用 bcrypt
4. **Token 轮换** — 已实现（access + refresh + 黑名单）
5. **资源隔离** — 已实现（shop_id + user_id 双重过滤）

---

## 六、总结

### 核心价值

1. **URL 解析器** 是最大资产 — 50+ 平台的正则表达式可直接复用
2. **平台适配模式** 提供了清晰的扩展框架
3. **反爬处理** 展示了成熟的电商数据采集经验

### pipixia 的差距

1. **爬虫能力** — EasyBoss 有 50+ 平台，pipixia 目前只有 URL 解析
2. **ERP 服务端** — EasyBoss 有云端 ERP，pipixia 需自建
3. **数据采集深度** — EasyBoss 提取完整 SKU/价格/图片，pipixia 仅存基础字段

### 下一步行动

1. ✅ 提取 EasyBoss 的 URL 解析正则到 pipixia
2. 🔄 用 Playwright 实现 1688/拼多多商品详情抓取
3. 🔄 对接 Shopee 真实 API（EasyBoss 已证明可行性）
4. ⬜ 考虑集成 EasyBoss ERP 服务端（如果用户有账号）

---

*本报告基于 EasyBoss ERP Chrome 插件 V1.3.4 源码分析*
