from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from conf.system import SYS_CONFIG

Base = declarative_base()
engine = create_engine(f"sqlite:///database/database.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)