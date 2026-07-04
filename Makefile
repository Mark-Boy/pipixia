# pipixia 项目 Makefile

.PHONY: help up down restart logs build clean db-init create-admin

help: ## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## 启动所有服务
	docker compose up -d

down: ## 停止所有服务
	docker compose down

restart: ## 重启所有服务
	docker compose down && docker compose up -d

logs: ## 查看 API 日志
	docker compose logs -f api

worker-logs: ## 查看 Worker 日志
	docker compose logs -f worker

dashboard-logs: ## 查看 Dashboard 日志
	docker compose logs -f dashboard

build: ## 重新构建镜像
	docker compose build --no-cache

clean: ## 清理容器和数据卷
	docker compose down -v

db-init: ## 初始化数据库
	docker compose exec api python scripts/init_db.py

create-admin: ## 创建管理员账号
	docker compose exec api python scripts/create_admin.py --username admin --password admin123

migrate: ## 运行数据库迁移
	docker compose exec api alembic upgrade head

seed: ## 插入种子数据
	docker compose exec api python scripts/seed_data.py
