from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# For GitHub Codespaces, use a path in the workspace
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sensegrid.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    name = Column(String(255))
    password = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    rooms = relationship("Room", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")

class Room(Base):
    __tablename__ = "rooms"
    
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String(255), index=True)  # Not globally unique, unique per user
    room_name = Column(String(255))
    device_id = Column(String(255))
    sensors = Column(Text)  # JSON string
    actions = Column(Text)  # JSON string
    last_seen = Column(Integer)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    user = relationship("User", back_populates="rooms")

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(String(255), index=True)
    home_id = Column(String(255), index=True)
    snapshot_url = Column(String(512), nullable=True)
    timestamp = Column(Integer)  # Unix timestamp in milliseconds
    resolved = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    user = relationship("User", back_populates="alerts")


# Create all tables
def init_db():
    Base.metadata.create_all(bind=engine)


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()