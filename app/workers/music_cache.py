"""
Celery Task: Music Cache Refresh
Fetches tracks from Jamendo and Pixabay Music APIs,
caches metadata (not MP3s) in PostgreSQL for fast retrieval.
"""

import os
from datetime import datetime, timezone

from celery import shared_task
from celery.utils.log import get_task_logger

import requests

from app.models.db import CachedTrack
from app.models.database import get_db_context

logger = get_task_logger(__name__)

# ─────────────────────────────────────────────
# JAMENDO API
# ─────────────────────────────────────────────
JAMENDO_MOODS = ["lofi", "chill", "cinematic", "epic", "happy", "romantic", "dark", "upbeat"]

def _fetch_jamendo_tracks(client_id: str, mood: str, limit: int = 30):
    """Fetch tracks from Jamendo API filtered by mood tag."""
    try:
        url = "https://api.jamendo.com/v3.0/tracks/"
        params = {
            "client_id": client_id,
            "format": "json",
            "limit": limit,
            "tags": mood,
            "include": "musicinfo",
            "audioformat": "mp32",
            "order": "popularity_total",
        }
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        tracks = []
        for t in data.get("results", []):
            tracks.append({
                "source": "jamendo",
                "external_id": str(t["id"]),
                "name": t.get("name", "Unknown"),
                "artist": t.get("artist_name", "Unknown"),
                "mood": mood,
                "stream_url": t.get("audio", ""),        # Direct CDN stream
                "duration": int(t.get("duration", 0)),
                "license": t.get("license_ccurl", "CC-BY"),
            })
        return tracks
    except Exception as e:
        logger.error(f"Jamendo fetch failed for mood '{mood}': {e}")
        return []


# ─────────────────────────────────────────────
# PIXABAY MUSIC API
# ─────────────────────────────────────────────
PIXABAY_CATEGORIES = ["background", "beats", "acoustic", "cinematic", "electronic"]

def _fetch_pixabay_music(api_key: str, category: str, limit: int = 30):
    """Fetch music from Pixabay API."""
    try:
        url = "https://pixabay.com/api/music/"
        params = {
            "key": api_key,
            "category": category,
            "per_page": limit,
            "order": "popular",
        }
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        tracks = []
        for t in data.get("hits", []):
            tracks.append({
                "source": "pixabay",
                "external_id": str(t["id"]),
                "name": t.get("title", "Unknown"),
                "artist": t.get("user", "Unknown"),
                "mood": category,
                "stream_url": t.get("audio", "") or t.get("url", ""),
                "duration": int(t.get("duration", 0)),
                "license": "Pixabay License",
            })
        return tracks
    except Exception as e:
        logger.error(f"Pixabay fetch failed for category '{category}': {e}")
        return []


# ─────────────────────────────────────────────
# CELERY TASKS
# ─────────────────────────────────────────────
@shared_task(name="app.workers.music_cache.refresh_all_tracks")
def refresh_all_tracks():
    """
    Weekly scheduled task: fetches fresh track metadata from 
    Jamendo + Pixabay and upserts into cached_tracks table.
    """
    logger.info("🎵 Starting music cache refresh...")
    
    total_upserted = 0
    
    # ── Jamendo ──
    jamendo_id = os.environ.get("JAMENDO_CLIENT_ID")
    if jamendo_id:
        for mood in JAMENDO_MOODS:
            tracks = _fetch_jamendo_tracks(jamendo_id, mood)
            count = _upsert_tracks(tracks)
            total_upserted += count
            logger.info(f"  Jamendo [{mood}]: {count} tracks")
    else:
        logger.warning("JAMENDO_CLIENT_ID not set, skipping Jamendo")
    
    # ── Pixabay ──
    pixabay_key = os.environ.get("PIXABAY_API_KEY")
    if pixabay_key:
        for cat in PIXABAY_CATEGORIES:
            tracks = _fetch_pixabay_music(pixabay_key, cat)
            count = _upsert_tracks(tracks)
            total_upserted += count
            logger.info(f"  Pixabay [{cat}]: {count} tracks")
    else:
        logger.warning("PIXABAY_API_KEY not set, skipping Pixabay")
    
    logger.info(f"✅ Music cache refresh complete: {total_upserted} tracks upserted")
    return {"total_upserted": total_upserted}


@shared_task(name="app.workers.music_cache.get_tracks_by_mood")
def get_tracks_by_mood(mood: str, limit: int = 20):
    """Retrieve cached tracks by mood from DB."""
    with get_db_context() as db:
        tracks = (
            db.query(CachedTrack)
            .filter(CachedTrack.mood == mood)
            .order_by(CachedTrack.id.desc())
            .limit(limit)
            .all()
        )
        return [
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
        ]


def _upsert_tracks(tracks: list) -> int:
    """Insert or update tracks in the DB. Returns count of upserted rows."""
    if not tracks:
        return 0
    
    count = 0
    with get_db_context() as db:
        for t in tracks:
            existing = (
                db.query(CachedTrack)
                .filter(
                    CachedTrack.source == t["source"],
                    CachedTrack.external_id == t["external_id"],
                )
                .first()
            )
            
            if existing:
                # Update
                existing.name = t["name"]
                existing.artist = t["artist"]
                existing.mood = t["mood"]
                existing.stream_url = t["stream_url"]
                existing.duration = t["duration"]
                existing.license = t["license"]
                existing.last_refreshed = datetime.now(timezone.utc)
            else:
                # Insert
                db.add(CachedTrack(**t))
            
            count += 1
    
    return count
