from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./job_agent.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, index=True)
    title = Column(String)
    company = Column(String)
    location = Column(String)
    description = Column(Text)
    apply_url = Column(String)
    source = Column(String)
    fit_score = Column(Float, nullable=True)
    fit_summary = Column(Text, nullable=True)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    is_new = Column(Boolean, default=True)


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, nullable=True)
    company = Column(String)
    title = Column(String)
    apply_url = Column(String, nullable=True)
    status = Column(String, default="applied")  # applied, phone_screen, interviewing, offer, rejected, withdrawn
    applied_date = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String)  # user or assistant
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
