# 拼多多商品采集器

## 功能说明

拼多多商品采集器是 pipixia 管理平台的一个独立页面，用于搜索、浏览并采集拼多多商品到管理平台。

## 使用方式

### 方式一：页面内搜索采集

1. 进入"商品管理" → 点击"导入商品"下拉菜单 → 选择"拼多多商品采集器"
2. 选择目标店铺
3. 输入搜索关键词，点击"搜索"
4. 在搜索结果中选择要采集的商品
5. 点击"采集选中"按钮
6. 采集成功后，点击"批量导入到店铺"导入到数据库

### 方式二：打开拼多多浏览器

1. 点击右上角"打开拼多多浏览器"按钮
2. 在新窗口中浏览拼多多网站
3. 复制商品链接回到采集器页面粘贴导入

## 技术架构

### 前端
- Next.js App Router
- 拼多多 API 直接请求（CORS）
- 选择/批量操作 UI

### 后端
- `api/routers/products.py` — 商品导入 API
- `api/crawlers/pinduoduo.py` — 拼多多爬虫

## API 端端点

### 搜索商品
```
GET https://mobile.yangkeduo.com/proxy/apis/v5/search/search
参数: keyword, page, page_size
```

### 获取商品详情
```
GET https://mobile.yangkeduo.com/proxy/apis/v5/item/detail
参数: item_id
```

### 导入商品
```
POST /api/v1/products/import
Body: { url: string, shop_id: number }
```

## 注意事项

- 拼多多 API 需要 CORS 支持，前端请求时可能需要代理
- 商品标题中的特殊字符会被自动处理
- 价格信息统一转换为人民币（CNY）
- 采集频率限制：每秒最多 5 个请求
- 导入失败的商品会在导入结果中显示错误原因

## 后续优化

- [ ] 添加采集历史记录
- [ ] 支持从剪贴板粘贴商品链接
- [ ] 添加商品对比功能
- [ ] 支持批量导出采集结果
- [ ] 添加价格监控和降价提醒
- [ ] 支持多店铺采集
