"""
Celery Application Configuration.
Connects to Redis as broker and result backend.
"""

import os
from celery import Celery
from celery.schedules import crontab

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "moneyprinter",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "app.workers.video_task",
        "app.workers.music_cache",
    ],
)

# Celery Configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timezone
    timezone="UTC",
    enable_utc=True,
    
    # Task behavior
    task_track_started=True,
    task_time_limit=900,           # Hard kill after 15 min
    task_soft_time_limit=600,      # Graceful timeout at 10 min
    task_acks_late=True,           # Ack after task completes (crash-safe)
    worker_prefetch_multiplier=1,  # One task at a time per worker
    
    # Result expiry
    result_expires=86400,          # 24 hours
    
    # Retry
    task_default_retry_delay=30,
    task_max_retries=2,
    
    # Beat schedule (periodic tasks)
    beat_schedule={
        "refresh-music-cache-weekly": {
            "task": "app.workers.music_cache.refresh_all_tracks",
            "schedule": crontab(hour=3, minute=0, day_of_week="monday"),  # Every Monday 3 AM
        },
    },
)
