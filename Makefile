# pipixia 项目 Makefile

.PHONY: help up down restart logs build clean db-init create-admin migrate seed pg-migrate

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

db-init: ## 初始化数据库（创建表）
	docker compose exec api python scripts/init_db.py

create-admin: ## 创建管理员账号
	docker compose exec api python scripts/create_admin.py --username admin --password admin123

migrate: ## 运行 Alembic 迁移到最新
	docker compose exec api alembic upgrade head

migrate-down: ## 回退一次迁移
	docker compose exec api alembic downgrade -1

seed: ## 插入种子数据
	docker compose exec api python scripts/seed_data.py

pg-migrate: ## SQLite → PostgreSQL 数据迁移
	python3 scripts/migrate_sqlite_to_pg.py

pg-shell: ## 进入 PostgreSQL shell
	docker compose exec postgres psql -U pipixia -d pipixia
