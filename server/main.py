import sys
from pathlib import Path
import aiosqlite
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from conf.system import SYS_CONFIG
from server.database import Base, engine
from server.routers import chat, auth, billing, user, home_page
from src.logger import logger

# 初始化数据库
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = Path(SYS_CONFIG.session_database_dir) / "session_database.db"
    async with aiosqlite.connect(db_path, timeout=30) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA synchronous=NORMAL;")
        await db.execute("PRAGMA busy_timeout=5000;")   # ms
        await db.commit()
    yield


# --- FastAPI 应用和服务设置 ---
app = FastAPI(title=f"{SYS_CONFIG.app_name} API (Streaming Workflow Engine)", lifespan=lifespan)

# --- 配置 CORS 中间件 ---
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:7860",
    "http://127.0.0.1:7860",
    "http://localhost:80",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 2. 路由挂载
app.include_router(chat.router, tags=["Workflow"])
app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(billing.router, prefix="/api", tags=["Billing"])
app.include_router(user.router, prefix="/api", tags=["User"])
app.include_router(home_page.router, prefix="/api", tags=["Home Page"])


if __name__ == "__main__":
    import uvicorn

    logger.info(
        f"Starting API server, port {SYS_CONFIG.api_port}, application name '{SYS_CONFIG.app_name}"
    )
    uvicorn.run("server.api:app", host="0.0.0.0", port=SYS_CONFIG.api_port, reload=False, workers=1)