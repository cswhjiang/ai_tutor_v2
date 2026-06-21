from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from conf.path import DATABASE_ROOT

Base = declarative_base()
db_path = Path(DATABASE_ROOT) / "database.db"
db_path.parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(f"sqlite:///{db_path}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
