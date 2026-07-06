import os
import asyncio
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
from agent import score_job_fit, tailor_application, chat

scheduler = AsyncIOScheduler()


async def run_daily_scrape():
    from database import SessionLocal
    print(f"[{datetime.now()}] Starting daily job scrape...")
    jobs = await scrape_all_jobs()
    db = SessionLocal()
    try:
        new_count = 0
        for job_data in jobs:
            existing = db.query(Job).filter(Job.external_id == job_data["external_id"]).first()
            if existing:
                continue
            score, summary = score_job_fit(
                job_data["title"], job_data["description"], job_data["company"]
            )
            job = Job(
                **job_data,
                fit_score=score,
                fit_summary=summary,
            )
            db.add(job)
            new_count += 1
        db.commit()
        print(f"[{datetime.now()}] Scrape complete. Added {new_count} new jobs.")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler.add_job(run_daily_scrape, "cron", hour=9, minute=0)
    scheduler.start()
    print("Scheduler started — daily scrape at 9:00 AM")
    yield
    scheduler.shutdown()


app = FastAPI(title="Sam's Job Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Job endpoints ---

@app.get("/api/jobs")
def get_jobs(min_score: float = 0, db: Session = Depends(get_db)):
    jobs = (
        db.query(Job)
        .filter(Job.fit_score >= min_score)
        .order_by(Job.fit_score.desc(), Job.scraped_at.desc())
        .all()
    )
    return jobs


@app.post("/api/jobs/scrape")
async def trigger_scrape(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_daily_scrape)
    return {"message": "Scrape started in background"}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/api/jobs/{job_id}/tailor")
def tailor_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    result = tailor_application(job.title, job.description, job.company)
    return result


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()
    return {"message": "Job deleted"}


# --- Application tracker endpoints ---

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
    app_obj = Application(**data.dict())
    db.add(app_obj)
    db.commit()
    db.refresh(app_obj)
    return app_obj


@app.patch("/api/applications/{app_id}")
def update_application(app_id: int, data: ApplicationUpdate, db: Session = Depends(get_db)):
    app_obj = db.query(Application).filter(Application.id == app_id).first()
    if not app_obj:
        raise HTTPException(status_code=404, detail="Application not found")
    if data.status is not None:
        app_obj.status = data.status
    if data.notes is not None:
        app_obj.notes = data.notes
    app_obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(app_obj)
    return app_obj


@app.delete("/api/applications/{app_id}")
def delete_application(app_id: int, db: Session = Depends(get_db)):
    app_obj = db.query(Application).filter(Application.id == app_id).first()
    if not app_obj:
        raise HTTPException(status_code=404, detail="Application not found")
    db.delete(app_obj)
    db.commit()
    return {"message": "Deleted"}


# --- Chat endpoint ---

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
    return {"message": "Chat cleared"}


@app.get("/api/chat/history")
def get_chat_history(db: Session = Depends(get_db)):
    messages = db.query(ChatMessage).order_by(ChatMessage.created_at).all()
    return [{"role": m.role, "content": m.content, "id": m.id} for m in messages]


@app.get("/health")
def health():
    return {"status": "ok"}
