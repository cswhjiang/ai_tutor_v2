import os

from conf.system import SYS_CONFIG
from google.adk.sessions import DatabaseSessionService
from google.adk.artifacts import InMemoryArtifactService

db_path = os.path.join(SYS_CONFIG.session_database_dir, "session_database.db")
db_url = "sqlite+aiosqlite:///{}?timeout=30".format(db_path)    # 设置超时时间为30秒，避免数据库锁定问题

session_service = DatabaseSessionService(db_url)
artifact_service = InMemoryArtifactService()
