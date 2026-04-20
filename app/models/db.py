"""
SQLAlchemy Database Models for MoneyPrinterTurbo SaaS.
Maps directly to the schema defined in the refactor plan.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, 
    String, Text, JSON, UniqueConstraint, create_engine
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


# ─────────────────────────────────────────────
# USERS
# ─────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # NULL for OAuth users
    oauth_provider = Column(String(50), nullable=True)     # 'google', 'github'
    oauth_id = Column(String(255), nullable=True)
    display_name = Column(String(100), nullable=True)
    
    # Billing
    credits = Column(Integer, default=3)                   # Free trial credits
    subscription_tier = Column(String(20), default="free") # free, pro, enterprise
    stripe_customer_id = Column(String(255), nullable=True)
    
    # API access
    api_key = Column(String(64), unique=True, nullable=True)
    
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    credit_transactions = relationship("CreditTransaction", back_populates="user")

    def has_credits(self, amount: int = 1) -> bool:
        return self.credits >= amount

    def deduct_credits(self, amount: int = 1):
        if not self.has_credits(amount):
            raise ValueError(f"Insufficient credits: {self.credits} < {amount}")
        self.credits -= amount

    def add_credits(self, amount: int):
        self.credits += amount


# ─────────────────────────────────────────────
# PROJECTS (video generation requests)
# ─────────────────────────────────────────────
class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    topic = Column(String(500), nullable=False)
    script = Column(Text, nullable=True)
    status = Column(String(20), default="draft", index=True)  # draft, queued, processing, complete, failed
    
    # Output
    video_url = Column(String(1000), nullable=True)            # S3 signed URL
    thumbnail_url = Column(String(1000), nullable=True)
    
    # Params
    aspect_ratio = Column(String(10), default="9:16")
    duration = Column(Integer, nullable=True)                  # seconds
    voice_name = Column(String(100), nullable=True)
    bgm_mood = Column(String(50), nullable=True)
    caption_style = Column(String(50), nullable=True)
    llm_provider = Column(String(50), nullable=True)
    credits_used = Column(Integer, default=1)
    render_params = Column(JSON, nullable=True)                # Full VideoParams snapshot
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="projects")
    render_job = relationship("RenderJob", back_populates="project", uselist=False, cascade="all, delete-orphan")


# ─────────────────────────────────────────────
# RENDER JOBS (Celery task tracking)
# ─────────────────────────────────────────────
class RenderJob(Base):
    __tablename__ = "render_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    celery_task_id = Column(String(255), nullable=True)
    status = Column(String(20), default="pending", index=True)  # pending, started, progress, success, failure
    progress = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    project = relationship("Project", back_populates="render_job")


# ─────────────────────────────────────────────
# CACHED MUSIC TRACKS (Jamendo + Pixabay)
# ─────────────────────────────────────────────
class CachedTrack(Base):
    __tablename__ = "cached_tracks"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_track_source_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(20), nullable=False)             # 'jamendo', 'pixabay'
    external_id = Column(String(100), nullable=False)
    name = Column(String(255), nullable=True)
    artist = Column(String(255), nullable=True)
    mood = Column(String(50), nullable=True, index=True)    # 'lofi', 'cinematic', 'upbeat'
    stream_url = Column(String(1000), nullable=True)
    duration = Column(Integer, nullable=True)
    license = Column(String(50), nullable=True)             # 'CC-BY', 'CC0'
    last_refreshed = Column(DateTime(timezone=True), server_default=func.now())


# ─────────────────────────────────────────────
# CREDIT TRANSACTIONS
# ─────────────────────────────────────────────
class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Integer, nullable=False)                 # positive = purchase, negative = usage
    type = Column(String(20), nullable=False)                # 'purchase', 'render', 'refund', 'bonus'
    stripe_payment_id = Column(String(255), nullable=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="credit_transactions")


# ─────────────────────────────────────────────
# DATABASE SESSION FACTORY
# ─────────────────────────────────────────────
def get_engine(database_url: str):
    return create_engine(database_url, pool_pre_ping=True, pool_size=10, max_overflow=20)

def get_session_factory(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
