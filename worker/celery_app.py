"""
Celery Worker 配置
"""

import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.config_from_object({
    "broker_connection_retry_on_startup": True,
    "task_serializer": "json",
    "result_serializer": "json",
    "accept_content": ["json"],
    "timezone": "Asia/Shanghai",
    "enable_utc": False,
    "task_routes": {
        "worker.tasks.*": {"queue": "tasks"},
    },
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
    },
})

# 自动发现所有 tasks 模块
celery_app.autodiscover_tasks(["worker"])
