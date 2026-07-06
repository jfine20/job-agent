import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import init_db, get_db, Job, Application, ChatMessage
from scraper import scrape_all_jobs
from agent import score_job, tailor_application, chat

scheduler = AsyncIOScheduler()


async def run_daily_scrape():
    from database import SessionLocal
    print(f"[{datetime.now()}] Starting scrape...")
    db = SessionLocal()
    try:
        jobs = await scrape_all_jobs()
        new_count = 0
        for job_data in jobs:
            if db.query(Job).filter(Job.external_id == job_data["external_id"]).first():
                continue
            scored = score_job(job_data["title"], job_data.get("description", ""), job_data["company"])
            job = Job(
                external_id=job_data["external_id"],
                title=job_data["title"],
                company=job_data["company"],
                location=job_data.get("location", ""),
                description=job_data.get("description", ""),
                apply_url=job_data.get("apply_url", ""),
                source=job_data.get("source", ""),
                salary_range=job_data.get("salary_range"),
                fit_score=scored["fit_score"],
                fit_summary=scored["fit_summary"],
                seniority=scored["seniority"],
                company_type=scored["company_type"],
                is_new=True,
            )
            db.add(job)
            new_count += 1
        db.commit()
        print(f"[{datetime.now()}] Done. Added {new_count} new jobs.")
    except Exception as e:
        print(f"Scrape error: {e}")
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler.add_job(run_daily_scrape, "cron", hour=9, minute=0)
    scheduler.start()
    print("Scheduler ready — daily scrape at 9:00 AM")
    yield
    scheduler.shutdown()


app = FastAPI(title="Sam's Job Agent", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)


# ── Jobs ──────────────────────────────────────────────────────────────────────

@app.get("/api/jobs")
def get_jobs(
    min_score: float = 0,
    source: Optional[str] = None,
    company_type: Optional[str] = None,
    seniority: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Job).filter(Job.fit_score >= min_score)
    if source:
        q = q.filter(Job.source == source)
    if company_type:
        q = q.filter(Job.company_type == company_type)
    if seniority:
        q = q.filter(Job.seniority == seniority)
    return q.order_by(Job.fit_score.desc(), Job.scraped_at.desc()).all()


@app.post("/api/jobs/scrape")
async def trigger_scrape(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_daily_scrape)
    return {"message": "Scrape started"}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Not found")
    return job


@app.post("/api/jobs/{job_id}/tailor")
def tailor_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Not found")
    return tailor_application(job.title, job.description or "", job.company)


@app.patch("/api/jobs/{job_id}/seen")
def mark_seen(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if job:
        job.is_new = False
        db.commit()
    return {"ok": True}


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Not found")
    db.delete(job)
    db.commit()
    return {"ok": True}


@app.get("/api/jobs/stats/summary")
def stats(db: Session = Depends(get_db)):
    total = db.query(Job).count()
    new = db.query(Job).filter(Job.is_new == True).count()
    by_source = {}
    for job in db.query(Job).all():
        by_source[job.source] = by_source.get(job.source, 0) + 1
    by_type = {}
    for job in db.query(Job).all():
        k = job.company_type or "other"
        by_type[k] = by_type.get(k, 0) + 1
    return {"total": total, "new": new, "by_source": by_source, "by_type": by_type}


# ── Applications ──────────────────────────────────────────────────────────────

class ApplicationCreate(BaseModel):
    job_id: Optional[int] = None
    company: str
    title: str
    apply_url: Optional[str] = None
    status: str = "applied"
    notes: Optional[str] = None


class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


@app.get("/api/applications")
def get_applications(db: Session = Depends(get_db)):
    return db.query(Application).order_by(Application.applied_date.desc()).all()


@app.post("/api/applications")
def create_application(data: ApplicationCreate, db: Session = Depends(get_db)):
    obj = Application(**data.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@app.patch("/api/applications/{app_id}")
def update_application(app_id: int, data: ApplicationUpdate, db: Session = Depends(get_db)):
    obj = db.query(Application).filter(Application.id == app_id).first()
    if not obj:
        raise HTTPException(404, "Not found")
    if data.status is not None:
        obj.status = data.status
    if data.notes is not None:
        obj.notes = data.notes
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


@app.delete("/api/applications/{app_id}")
def delete_application(app_id: int, db: Session = Depends(get_db)):
    obj = db.query(Application).filter(Application.id == app_id).first()
    if not obj:
        raise HTTPException(404, "Not found")
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str


@app.post("/api/chat")
def chat_endpoint(req: ChatRequest, db: Session = Depends(get_db)):
    db.add(ChatMessage(role="user", content=req.message))
    db.commit()
    history = db.query(ChatMessage).order_by(ChatMessage.created_at).all()
    messages = [{"role": m.role, "content": m.content} for m in history]
    reply = chat(messages)
    db.add(ChatMessage(role="assistant", content=reply))
    db.commit()
    return {"reply": reply}


@app.delete("/api/chat")
def clear_chat(db: Session = Depends(get_db)):
    db.query(ChatMessage).delete()
    db.commit()
    return {"ok": True}


@app.get("/api/chat/history")
def get_chat_history(db: Session = Depends(get_db)):
    msgs = db.query(ChatMessage).order_by(ChatMessage.created_at).all()
    return [{"role": m.role, "content": m.content, "id": m.id} for m in msgs]


@app.get("/health")
def health():
    return {"status": "ok"}
