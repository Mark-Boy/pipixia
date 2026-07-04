# pipixia

跨境电商自动上架工具：1688/拼多多 → Shopee 泰国站

## 快速启动

```bash
# 1. 复制环境变量
cp .env.example .env

# 2. 启动基础设施
docker compose up -d postgres redis minio minio-init

# 3. 启动后端
docker compose up -d api

# 4. 初始化数据库
docker compose exec api python scripts/init_db.py

# 5. 启动 Worker
docker compose up -d worker

# 6. 启动 Dashboard
cd dashboard && npm install && npm run dev
```

## 访问地址

- Dashboard: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- MinIO Console: http://localhost:9001

## 项目结构

```
pipixia/
├── api/              # FastAPI 后端
├── worker/           # Celery Worker
├── dashboard/        # Next.js 前端
├── config/           # 配置文件
├── scripts/          # 运维脚本
├── tests/            # 测试
├── migrations/       # Alembic 迁移
├── docker-compose.yml
└── .env.example
```
# pipixia
