import os
from datetime import datetime
from typing import Generator
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# Using a zero-setup local SQLite database file instead of PostgreSQL
DATABASE_URL = "sqlite:///./test.db"

# connect_args={"check_same_thread": False} is required for SQLite to work with FastAPI
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class HCPProfile(Base):
    __tablename__ = "hcp_profiles"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    specialty = Column(String(100), index=True)
    hospital = Column(String(200))
    email = Column(String(100), unique=True, index=True)
    phone = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    interactions = relationship("Interaction", back_populates="hcp")

class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    hcp_id = Column(Integer, ForeignKey("hcp_profiles.id"), nullable=False)
    summary = Column(Text, nullable=False)
    extracted_entities = Column(Text, nullable=True)  # Stored as JSON string
    follow_up_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hcp = relationship("HCPProfile", back_populates="interactions")

# Initialize DB Tables
def init_db():
    Base.metadata.create_all(bind=engine)

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()