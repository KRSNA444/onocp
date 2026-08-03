"""
ONOCP — One Nation, One Complaint Portal
Backend API (FastAPI + SQLite)

Run:
    pip install -r requirements.txt
    uvicorn main:app --reload

Docs at http://127.0.0.1:8000/docs
"""

import random
import string
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import shutil
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base

from routing import detect_category, get_department, get_sla_days, get_color, all_categories

# ---------------------------------------------------------------------------
# DB setup
# ---------------------------------------------------------------------------
DATABASE_URL = "sqlite:///./onocp.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

STATUS_FLOW = ["Pending", "Assigned", "In Progress", "Resolved"]


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    tracking_id = Column(String, unique=True, index=True)
    title = Column(String)
    description = Column(String)
    category = Column(String)
    department = Column(String)
    status = Column(String, default="Pending")
    location_text = Column(String, nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    citizen_contact = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    deadline = Column(DateTime)
    escalated = Column(Boolean, default=False)
    video_url = Column(String, nullable=True)


Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="ONOCP API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


def gen_tracking_id() -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"ONOCP-{suffix}"


def to_dict(c: Complaint) -> dict:
    now = datetime.utcnow()
    is_overdue = c.status != "Resolved" and now > c.deadline
    return {
        "id": c.id,
        "tracking_id": c.tracking_id,
        "title": c.title,
        "description": c.description,
        "category": c.category,
        "department": c.department,
        "status": c.status,
        "location_text": c.location_text,
        "lat": c.lat,
        "lng": c.lng,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
        "deadline": c.deadline.isoformat(),
        "overdue": is_overdue,
        "escalated": c.escalated or is_overdue,
        "color": get_color(c.category),
        "video_url": c.video_url,
    }


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ComplaintCreate(BaseModel):
    title: str = Field(..., min_length=3)
    description: str = Field(..., min_length=5)
    location_text: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    citizen_contact: Optional[str] = None
    category_override: Optional[str] = None  # let user correct auto-detection


class StatusUpdate(BaseModel):
    status: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.post("/api/complaints")
def create_complaint(payload: ComplaintCreate):
    db = SessionLocal()
    try:
        category = payload.category_override if payload.category_override in all_categories() \
            else detect_category(payload.title, payload.description)
        department = get_department(category)
        sla_days = get_sla_days(category)

        complaint = Complaint(
            tracking_id=gen_tracking_id(),
            title=payload.title,
            description=payload.description,
            category=category,
            department=department,
            status="Pending",
            location_text=payload.location_text,
            lat=payload.lat,
            lng=payload.lng,
            citizen_contact=payload.citizen_contact,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            deadline=datetime.utcnow() + timedelta(days=sla_days),
            escalated=False,
        )
        db.add(complaint)
        db.commit()
        db.refresh(complaint)
        return to_dict(complaint)
    finally:
        db.close()

@app.post("/api/complaints/{complaint_id}/video")
def upload_video(complaint_id: int, video: UploadFile = File(...)):
    db = SessionLocal()
    try:
        c = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not c:
            raise HTTPException(status_code=404, detail="Complaint not found")
        
        file_path = f"uploads/{c.tracking_id}_{video.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(video.file, buffer)
            
        c.video_url = f"/{file_path}"
        c.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(c)
        return to_dict(c)
    finally:
        db.close()


@app.get("/api/complaints/track/{tracking_id}")
def track_complaint(tracking_id: str):
    db = SessionLocal()
    try:
        c = db.query(Complaint).filter(Complaint.tracking_id == tracking_id).first()
        if not c:
            raise HTTPException(status_code=404, detail="Tracking ID not found")
        return to_dict(c)
    finally:
        db.close()


@app.get("/api/complaints")
def list_complaints(
    status: Optional[str] = None,
    department: Optional[str] = None,
    category: Optional[str] = None,
):
    db = SessionLocal()
    try:
        q = db.query(Complaint)
        if status:
            q = q.filter(Complaint.status == status)
        if department:
            q = q.filter(Complaint.department == department)
        if category:
            q = q.filter(Complaint.category == category)
        complaints = q.order_by(Complaint.created_at.desc()).all()
        return [to_dict(c) for c in complaints]
    finally:
        db.close()


@app.patch("/api/complaints/{complaint_id}")
def update_status(complaint_id: int, payload: StatusUpdate):
    if payload.status not in STATUS_FLOW:
        raise HTTPException(status_code=400, detail=f"Status must be one of {STATUS_FLOW}")
    db = SessionLocal()
    try:
        c = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not c:
            raise HTTPException(status_code=404, detail="Complaint not found")
        c.status = payload.status
        c.updated_at = datetime.utcnow()
        if payload.status == "Resolved":
            c.escalated = False
        db.commit()
        db.refresh(c)
        return to_dict(c)
    finally:
        db.close()


@app.get("/api/complaints/heatmap")
def heatmap_data():
    """Public endpoint — only non-personal fields for the public heatmap."""
    db = SessionLocal()
    try:
        complaints = db.query(Complaint).filter(
            Complaint.lat.isnot(None), Complaint.lng.isnot(None)
        ).all()
        return [
            {
                "lat": c.lat,
                "lng": c.lng,
                "category": c.category,
                "status": c.status,
                "color": get_color(c.category),
            }
            for c in complaints
        ]
    finally:
        db.close()


@app.get("/api/stats")
def stats():
    db = SessionLocal()
    try:
        complaints = db.query(Complaint).all()
        total = len(complaints)
        by_status = {s: 0 for s in STATUS_FLOW}
        by_department = {}
        overdue = 0
        now = datetime.utcnow()
        for c in complaints:
            by_status[c.status] = by_status.get(c.status, 0) + 1
            by_department[c.department] = by_department.get(c.department, 0) + 1
            if c.status != "Resolved" and now > c.deadline:
                overdue += 1
        return {
            "total": total,
            "by_status": by_status,
            "by_department": by_department,
            "overdue": overdue,
        }
    finally:
        db.close()


@app.get("/api/categories")
def categories():
    return all_categories()


@app.get("/")
def root():
    return {"message": "ONOCP API is running. See /docs for API reference."}
