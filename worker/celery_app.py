"""
Celery Worker 配置
"""

import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
# 如果Redis不可用，使用sqlite作为broker
celery_app = Celery("worker")

celery_app.config_from_object({
    "broker_url": REDIS_URL,
    "result_backend": REDIS_URL,
    "broker_connection_retry_on_startup": True,
    "task_serializer": "json",
    "result_serializer": "json",
    "accept_content": ["json"],
    "timezone": "Asia/Shanghai",
    "enable_utc": False,
    "task_always_eager": True,  # 开发模式：直接执行任务
    "task_store_eager_result": True,  # 保存任务结果
    "task_routes": {
        "tasks.*": {"queue": "tasks"},
    },
    "include": ["tasks"],  # 容器内 worker/ 目录即 /app，直接导入 tasks 模块
    "beat_schedule": {
        "daily-profit-report": {
            "task": "worker.tasks.generate_daily_report",
            "schedule": 86400,  # 每天
            "options": {"queue": "scheduled"},
        },
        "exchange-rate-update": {
            "task": "worker.tasks.update_exchange_rate",
            "schedule": 86400,  # 每天
            "options": {"queue": "scheduled"},
        },
        "stock-sync": {
            "task": "worker.tasks.sync_inventory",
            "schedule": 86400,  # 每天
            "options": {"queue": "scheduled"},
        },
        "profit-circuit-breaker": {
            "task": "worker.tasks.profit_circuit_breaker",
            "schedule": 86400,  # 每天
            "options": {"queue": "scheduled"},
        },
    },
})

# 确保 tasks 模块被导入（容器内 /app/ 下有 tasks.py）
import sys
sys.path.insert(0, ".")
try:
    import tasks  # noqa: F401
except ImportError:
    pass
