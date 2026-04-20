"""
SaaS API Endpoints — Auth + Projects + Music
Layered on top of existing MoneyPrinterTurbo controllers.
"""

import secrets
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.middleware.auth import (
    create_access_token, get_current_user, get_admin_user,
    hash_password, verify_password,
)
from app.models.db import User, Project, RenderJob, CreditTransaction, CachedTrack
from app.models.database import get_db

router = APIRouter(prefix="/api/v1", tags=["SaaS"])


# ═══════════════════════════════════════════════
# REQUEST / RESPONSE SCHEMAS
# ═══════════════════════════════════════════════

class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    credits: int

class CreateProjectRequest(BaseModel):
    topic: str
    script: Optional[str] = None
    aspect_ratio: Optional[str] = "9:16"
    voice_name: Optional[str] = ""
    bgm_mood: Optional[str] = "random"
    caption_style: Optional[str] = "bottom"
    llm_provider: Optional[str] = "openai"
    video_source: Optional[str] = "pexels"

class ProjectResponse(BaseModel):
    id: str
    topic: str
    status: str
    video_url: Optional[str]
    duration: Optional[int]
    created_at: str

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════
# AUTH ENDPOINTS
# ═══════════════════════════════════════════════

@router.post("/auth/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user with email + password."""
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        email=req.email,
        hashed_password=hash_password(req.password),
        display_name=req.display_name or req.email.split("@")[0],
        credits=3,  # Free trial
        api_key=secrets.token_urlsafe(32),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    token = create_access_token(str(user.id), user.email, user.is_admin)
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        email=user.email,
        credits=user.credits,
    )


@router.post("/auth/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Login with email + password."""
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(str(user.id), user.email, user.is_admin)
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        email=user.email,
        credits=user.credits,
    )


@router.get("/auth/me")
def get_me(user: User = Depends(get_current_user)):
    """Get current user profile."""
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "credits": user.credits,
        "subscription_tier": user.subscription_tier,
        "api_key": user.api_key,
        "is_admin": user.is_admin,
    }


# ═══════════════════════════════════════════════
# PROJECT ENDPOINTS
# ═══════════════════════════════════════════════

@router.post("/projects", status_code=201)
def create_project(
    req: CreateProjectRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new video project and queue it for rendering."""
    # Check credits
    if not user.has_credits(1):
        raise HTTPException(status_code=402, detail="Insufficient credits. Please purchase more.")
    
    # Create project
    project = Project(
        user_id=user.id,
        topic=req.topic,
        script=req.script,
        status="queued",
        aspect_ratio=req.aspect_ratio,
        voice_name=req.voice_name,
        bgm_mood=req.bgm_mood,
        caption_style=req.caption_style,
        llm_provider=req.llm_provider,
        render_params={
            "video_subject": req.topic,
            "video_script": req.script or "",
            "video_aspect": req.aspect_ratio,
            "voice_name": req.voice_name or "",
            "bgm_type": req.bgm_mood or "random",
            "subtitle_position": req.caption_style or "bottom",
            "video_source": req.video_source or "pexels",
            "subtitle_enabled": True,
        },
    )
    db.add(project)
    db.flush()
    
    # Create render job
    job = RenderJob(project_id=project.id, status="pending")
    db.add(job)
    db.commit()
    db.refresh(project)
    
    # Dispatch Celery task
    from app.workers.video_task import generate_video
    generate_video.delay(str(project.id), str(user.id))
    
    return {
        "id": str(project.id),
        "status": "queued",
        "message": "Video generation started. Check /projects/{id} for status.",
    }


@router.get("/projects")
def list_projects(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
):
    """List all projects for the current user."""
    projects = (
        db.query(Project)
        .filter(Project.user_id == user.id)
        .order_by(Project.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    total = db.query(Project).filter(Project.user_id == user.id).count()
    
    return {
        "total": total,
        "projects": [
            {
                "id": str(p.id),
                "topic": p.topic,
                "status": p.status,
                "video_url": p.video_url,
                "duration": p.duration,
                "aspect_ratio": p.aspect_ratio,
                "credits_used": p.credits_used,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in projects
        ],
    }


@router.get("/projects/{project_id}")
def get_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get project details + render job status."""
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    job = db.query(RenderJob).filter(RenderJob.project_id == project.id).first()
    
    return {
        "id": str(project.id),
        "topic": project.topic,
        "script": project.script,
        "status": project.status,
        "video_url": project.video_url,
        "thumbnail_url": project.thumbnail_url,
        "duration": project.duration,
        "aspect_ratio": project.aspect_ratio,
        "voice_name": project.voice_name,
        "bgm_mood": project.bgm_mood,
        "credits_used": project.credits_used,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "render_job": {
            "status": job.status if job else None,
            "progress": job.progress if job else 0,
            "error": job.error if job else None,
            "started_at": job.started_at.isoformat() if job and job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job and job.finished_at else None,
        } if job else None,
    }


@router.delete("/projects/{project_id}")
def delete_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a project (user can only delete their own)."""
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(project)
    db.commit()
    return {"message": "Project deleted"}


# ═══════════════════════════════════════════════
# MUSIC LIBRARY ENDPOINT
# ═══════════════════════════════════════════════

@router.get("/music")
def get_music_library(
    mood: Optional[str] = Query(None, description="Filter by mood: lofi, cinematic, upbeat, chill"),
    limit: int = Query(30, le=100),
    db: Session = Depends(get_db),
):
    """Get cached music tracks by mood."""
    query = db.query(CachedTrack)
    if mood:
        query = query.filter(CachedTrack.mood == mood)
    
    tracks = query.order_by(CachedTrack.id.desc()).limit(limit).all()
    
    moods = db.query(CachedTrack.mood).distinct().all()
    available_moods = [m[0] for m in moods if m[0]]
    
    return {
        "available_moods": available_moods,
        "tracks": [
            {
                "id": t.id,
                "source": t.source,
                "name": t.name,
                "artist": t.artist,
                "mood": t.mood,
                "stream_url": t.stream_url,
                "duration": t.duration,
                "license": t.license,
            }
            for t in tracks
        ],
    }


# ═══════════════════════════════════════════════
# CREDITS ENDPOINT
# ═══════════════════════════════════════════════

@router.get("/credits/history")
def get_credit_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(20, le=100),
):
    """Get credit transaction history."""
    txns = (
        db.query(CreditTransaction)
        .filter(CreditTransaction.user_id == user.id)
        .order_by(CreditTransaction.created_at.desc())
        .limit(limit)
        .all()
    )
    
    return {
        "current_credits": user.credits,
        "transactions": [
            {
                "id": str(t.id),
                "amount": t.amount,
                "type": t.type,
                "project_id": str(t.project_id) if t.project_id else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in txns
        ],
    }
