"""
Celery Task: Video Generation Pipeline
Wraps MoneyPrinterTurbo's task.py:start() into an async Celery task.
Handles: credit deduction, S3 upload, DB state updates, error recovery.
"""

import os
import uuid
from datetime import datetime, timezone

from celery import shared_task
from celery.utils.log import get_task_logger

from app.models.db import Project, RenderJob, CreditTransaction, User
from app.models.database import get_db_context
from app.models.schema import VideoParams

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    name="app.workers.video_task.generate_video",
    max_retries=2,
    time_limit=900,
    soft_time_limit=600,
    acks_late=True,
)
def generate_video(self, project_id: str, user_id: str):
    """
    Main video generation Celery task.
    
    Flow:
    1. Update render_job status → 'started'
    2. Deduct user credits
    3. Call MoneyPrinterTurbo pipeline (task.py:start)
    4. Upload result to S3
    5. Update project status → 'complete'
    
    On failure: refund credits, mark as 'failed'.
    """
    logger.info(f"🎬 Starting video generation: project={project_id}, user={user_id}")
    
    with get_db_context() as db:
        # ── Update render job ──
        job = db.query(RenderJob).filter(RenderJob.project_id == project_id).first()
        if not job:
            logger.error(f"No render_job found for project {project_id}")
            return {"error": "Job not found"}
        
        job.status = "started"
        job.celery_task_id = self.request.id
        job.started_at = datetime.now(timezone.utc)
        db.flush()
        
        # ── Get project & user ──
        project = db.query(Project).get(project_id)
        user = db.query(User).get(user_id)
        
        if not project or not user:
            job.status = "failure"
            job.error = "Project or user not found"
            return {"error": job.error}
        
        # ── Deduct credits ──
        credits_needed = project.credits_used or 1
        if not user.has_credits(credits_needed):
            job.status = "failure"
            job.error = "Insufficient credits"
            project.status = "failed"
            return {"error": "Insufficient credits"}
        
        user.deduct_credits(credits_needed)
        db.add(CreditTransaction(
            user_id=uuid.UUID(user_id),
            amount=-credits_needed,
            type="render",
            project_id=uuid.UUID(project_id),
        ))
        db.flush()
    
    # ── Run the pipeline (outside DB session — long-running) ──
    try:
        from app.services.task import start as run_pipeline
        
        # Build VideoParams from stored render_params
        render_params = project.render_params or {}
        render_params.setdefault("video_subject", project.topic)
        render_params.setdefault("video_aspect", project.aspect_ratio or "9:16")
        
        if project.script:
            render_params["video_script"] = project.script
        if project.voice_name:
            render_params["voice_name"] = project.voice_name
        
        params = VideoParams(**render_params)
        
        # Progress callback
        def on_progress(pct):
            with get_db_context() as db2:
                j = db2.query(RenderJob).filter(RenderJob.project_id == project_id).first()
                if j:
                    j.progress = pct
        
        # ── Execute MoneyPrinterTurbo pipeline ──
        result = run_pipeline(task_id=str(project_id), params=params)
        
        if result and result.get("videos"):
            video_path = result["videos"][0]
            
            # ── Upload to S3 (if configured) ──
            video_url = _upload_to_storage(video_path, project_id, user_id)
            
            with get_db_context() as db:
                proj = db.query(Project).get(project_id)
                job = db.query(RenderJob).filter(RenderJob.project_id == project_id).first()
                
                proj.status = "complete"
                proj.video_url = video_url
                if result.get("audio_duration"):
                    proj.duration = int(result["audio_duration"])
                
                job.status = "success"
                job.progress = 100
                job.finished_at = datetime.now(timezone.utc)
            
            logger.info(f"✅ Video generation complete: {project_id}")
            return {"video_url": video_url, "project_id": project_id}
        else:
            raise Exception("Pipeline returned no videos")
    
    except Exception as exc:
        logger.error(f"❌ Video generation failed: {project_id} — {exc}")
        
        with get_db_context() as db:
            proj = db.query(Project).get(project_id)
            job = db.query(RenderJob).filter(RenderJob.project_id == project_id).first()
            user = db.query(User).get(user_id)
            
            if proj:
                proj.status = "failed"
            if job:
                job.status = "failure"
                job.error = str(exc)
                job.finished_at = datetime.now(timezone.utc)
            
            # Refund credits on failure
            if user:
                user.add_credits(credits_needed)
                db.add(CreditTransaction(
                    user_id=uuid.UUID(user_id),
                    amount=credits_needed,
                    type="refund",
                    project_id=uuid.UUID(project_id),
                ))
        
        # Celery retry (exponential backoff)
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))


def _upload_to_storage(local_path: str, project_id: str, user_id: str) -> str:
    """Upload video to S3/R2 if configured, otherwise return local path."""
    s3_endpoint = os.environ.get("S3_ENDPOINT")
    
    if not s3_endpoint:
        # Local mode: serve from filesystem
        logger.info("S3 not configured, using local file path")
        return f"/tasks/{project_id}/final-1.mp4"
    
    try:
        import boto3
        
        s3 = boto3.client(
            "s3",
            endpoint_url=s3_endpoint,
            aws_access_key_id=os.environ.get("S3_ACCESS_KEY"),
            aws_secret_access_key=os.environ.get("S3_SECRET_KEY"),
        )
        
        bucket = os.environ.get("S3_BUCKET", "moneyprinter-videos")
        key = f"{user_id}/{project_id}.mp4"
        
        s3.upload_file(local_path, bucket, key, ExtraArgs={"ContentType": "video/mp4"})
        
        public_url = os.environ.get("S3_PUBLIC_URL", s3_endpoint)
        return f"{public_url}/{key}"
    
    except Exception as e:
        logger.error(f"S3 upload failed: {e}, falling back to local")
        return f"/tasks/{project_id}/final-1.mp4"
