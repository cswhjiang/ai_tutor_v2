from typing import Optional

from fastapi import APIRouter, Cookie, HTTPException, Depends
from sqlalchemy.orm import Session

from server.database import SessionLocal
from server.models import UserInfo

router = APIRouter()

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@router.post("/user_info")
async def get_user_info(token: Optional[str] = Cookie(None), user_id: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    # 验证逻辑同 auth 模块
    user = db.query(UserInfo).filter_by(user_id=user_id).first()
    if not user: return {"result": False, "description": "用户不存在"}
    return {
        "result": True, "email": user.email, "user_name": user.user_name,
        "points_total": user.points_total, "points_balance": user.points_balance,
        "subscription_info": user.subscription_info
    }


@router.post("/check-and-decrement-points")
async def check_and_decrement_points(token: Optional[str] = Cookie(None), user_id: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    user = db.query(UserInfo).filter(UserInfo.user_id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")

    points_balance = int(user.points_balance)
    if points_balance >= 1:
        user.points_balance = str(points_balance - 1)
        db.commit()
        return {"result": True}
    return {"result": False}