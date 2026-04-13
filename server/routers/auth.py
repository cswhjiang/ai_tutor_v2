import uuid
import jwt
import random
import string
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Cookie
from fastapi.responses import JSONResponse

from conf.system import SYS_CONFIG
from server.database import SessionLocal
from server.models import UserInfo, VerificationCode, InvitationCode
from server.schemas import (
    RegisterRequest, NewLoginRequest, SendVerificationCodeRequest, 
    GoogleCodeVerifyRequest, InvitationCodeVerifyRequest
)
from server.utils.auth import (
    hash_password, verify_password, verify_google_authorization_code
)
from server.utils.email import send_email_smtp
from src.logger import logger



router = APIRouter()


@router.post("/send-verification-code")
async def send_verification_code(request: SendVerificationCodeRequest):

    # Generate a 6-character random verification code
    verification_code = "".join(random.choices(string.ascii_letters + string.digits, k=6))

    # Save the verification code to the database
    db = SessionLocal()
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    db_verification_code = VerificationCode(email=request.email, code=verification_code, expires_at=expires_at)
    db.merge(db_verification_code)  # Upsert operation
    db.commit()
    db.close()

    # Send the email asynchronously (non-blocking)
    subject = "创意智能体验证码"
    body = f"你的验证码是: {verification_code}. 它将在 10 分钟后过期，请尽快使用。"
    
    # 立即返回响应，邮件在后台发送
    asyncio.create_task(send_email_smtp(request.email, subject, body))
    
    return {"result": True, "description": "验证码已生成，邮件正在发送中"}

@router.post("/register")
async def register(request: RegisterRequest):
    db = SessionLocal()
    
    try:
        # Check invitation code from database
        invitation_code_entry = db.query(InvitationCode).filter_by(code=request.invitation_code).first()
        if not invitation_code_entry:
            return {"result": False, "description": "邀请码不存在"}
        
        remaining_uses = int(invitation_code_entry.remaining_uses)
        if remaining_uses <= 0:
            return {"result": False, "description": "邀请码已用完"}
        
        # Check if email already exists
        existing_user = db.query(UserInfo).filter_by(email=request.email).first()
        if existing_user:
            return {"result": False, "description": "该邮箱已被注册"}
        
        # Check verification code
        db_verification_code = db.query(VerificationCode).filter_by(email=request.email).first()
        if not db_verification_code or db_verification_code.code != request.verification_code:
            return {"result": False, "description": "验证码无效或已过期"}
        
        if datetime.utcnow() > db_verification_code.expires_at:
            return {"result": False, "description": "验证码已过期"}

        # Create new user
        user_id = f"user_{uuid.uuid4()}"
        hashed_password = hash_password(request.password)  # 加密密码
        new_user = UserInfo(
            user_id=user_id,
            email=request.email,
            user_name=request.email,
            password=hashed_password,  # 存储加密后的密码
            points_total="10",
            points_balance="10",
            is_activated="1",  # Email registration users are activated immediately
            login_method="email"
        )
        
        db.add(new_user)
        
        # Remove the used verification code
        db.delete(db_verification_code)
        
        # Decrement invitation code remaining uses
        invitation_code_entry.remaining_uses = str(remaining_uses - 1)
        
        db.commit()
        
        logger.info(f"New user registered: {request.email}, invitation code {request.invitation_code} remaining uses: {remaining_uses - 1}")
        return {"result": True, "user_id": user_id}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Registration failed: {e}")
        return {"result": False, "description": f"注册失败: {str(e)}"}
    finally:
        db.close()


# New login endpoint
@router.post("/login")
async def login(request: NewLoginRequest):
    """
    新的登录接口
    请求参数: email, password
    返回: result(布尔), token, user_id, email, user_name
    """
    db = SessionLocal()
    
    try:
        # Query user by email
        user = db.query(UserInfo).filter_by(email=request.email).first()
        
        if not user:
            logger.info(f"Login failed: email not found - {request.email}")
            return {"result": False, "description": "邮箱或密码错误"}
        
        # Verify password
        if not verify_password(request.password, user.password):
            logger.info(f"Login failed: incorrect password - {request.email}")
            return {"result": False, "description": "邮箱或密码错误"}
        
        # Generate new JWT token with 7 days expiration
        current_time = datetime.utcnow()
        expiration_time = current_time + timedelta(days=7)  # Token valid for 7 days
        
        payload = {
            "sub": user.user_id,
            "email": user.email,
            "iat": current_time,  # Issued at time
            "exp": expiration_time  # Expiration time
        }
        token = jwt.encode(payload, SYS_CONFIG.secret_key, algorithm="HS256")
        
        logger.info(f"User logged in successfully: {user.email} (user_id: {user.user_id}), token expires at: {expiration_time}")
        
        return {
            "result": True,
            "token": token,
            "user_id": user.user_id,
            "email": user.email,
            "user_name": user.user_name
        }
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return {"result": False, "description": f"登录失败: {str(e)}"}
    finally:
        db.close()


# Token verification endpoint
@router.get("/verify-token")
async def verify_token(
    token: Optional[str] = Cookie(None),
    user_id: Optional[str] = Cookie(None)
):
    """
    验证登录信息
    请求参数: token(请求头cookie里), user_id(请求头cookie里)
    返回: result(布尔), email, user_name
    """
    if not token or not user_id:
        return {"result": False, "description": "缺少token或user_id"}
    
    db = SessionLocal()
    
    try:
        # Verify JWT token
        try:
            payload = jwt.decode(token, SYS_CONFIG.secret_key, algorithms=["HS256"])
            token_user_id = payload.get("sub")
            
            # Check if token's user_id matches the provided user_id
            if token_user_id != user_id:
                logger.warning(f"Token verification failed: user_id mismatch")
                return {"result": False, "description": "token验证失败"}
                
        except jwt.ExpiredSignatureError:
            logger.info(f"Token expired for user_id: {user_id}")
            return {"result": False, "description": "token已过期"}
        except jwt.InvalidTokenError:
            logger.warning(f"Invalid token for user_id: {user_id}")
            return {"result": False, "description": "无效的token"}
        
        # Query user information
        user = db.query(UserInfo).filter_by(user_id=user_id).first()
        
        if not user:
            logger.warning(f"Token verification: user not found - {user_id}")
            return {"result": False, "description": "用户不存在"}
        
        logger.info(f"Token verified successfully for email: {user.email}")
        
        return {
            "result": True,
            "email": user.email,
            "user_name": user.user_name,
            "user_id": user.user_id
        }
        
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return {"result": False, "description": f"验证失败: {str(e)}"}
    finally:
        db.close()


@router.post("/verify-google-code")
async def verify_google_code(request: GoogleCodeVerifyRequest):
    """
    验证Google授权码进行登录或注册
    请求参数: authorization_code, redirect_uri
    返回: result, requires_invitation_code, token (如果不需要邀请码), user_id, email, user_name
    """
    # Verify Google authorization code and get user info
    user_info = verify_google_authorization_code(request.authorization_code, request.redirect_uri)
    
    if not user_info:
        logger.warning("Google authorization code verification failed")
        return {"result": False, "description": "Google授权码验证失败"}
    
    email = user_info["email"]
    name = user_info["name"]
    
    db = SessionLocal()
    
    try:
        # Check if user exists in database
        user = db.query(UserInfo).filter_by(email=email).first()
        
        if user:
            # User exists - check activation status
            if user.is_activated == "0":
                # User registered via Google but hasn't activated with invitation code
                logger.info(f"Google user exists but not activated: {email}")
                return {
                    "result": True,
                    "requires_invitation_code": True,
                    "user_id": user.user_id,
                    "email": user.email,
                    "user_name": user.user_name
                }
            else:
                # User is already activated - generate token and log in
                current_time = datetime.utcnow()
                expiration_time = current_time + timedelta(days=7)
                
                payload = {
                    "sub": user.user_id,
                    "email": user.email,
                    "iat": current_time,
                    "exp": expiration_time
                }
                token = jwt.encode(payload, SYS_CONFIG.secret_key, algorithm="HS256")
                
                logger.info(f"Google user logged in successfully: {email} (user_id: {user.user_id})")
                
                return {
                    "result": True,
                    "requires_invitation_code": False,
                    "token": token,
                    "user_id": user.user_id,
                    "email": user.email,
                    "user_name": user.user_name
                }
        else:
            # First time login - create inactive user
            user_id = f"user_{uuid.uuid4()}"
            
            # Generate random 10-character password
            random_password = "".join(random.choices(string.ascii_letters + string.digits, k=10))
            hashed_password = hash_password(random_password)  # 加密密码
            new_user = UserInfo(
                user_id=user_id,
                email=email,
                user_name=name,
                password=hashed_password,
                points_total="10",
                points_balance="10",
                is_activated="0",  # Not activated yet
                login_method="google"
            )
            
            db.add(new_user)
            db.commit()
            
            logger.info(f"New Google user created (not activated): {email} (user_id: {user_id})")
            
            return {
                "result": True,
                "requires_invitation_code": True,
                "user_id": user_id,
                "email": email,
                "user_name": name
            }
            
    except Exception as e:
        db.rollback()
        logger.error(f"Google code verification error: {e}")
        return {"result": False, "description": f"处理失败: {str(e)}"}
    finally:
        db.close()


@router.post("/verify-invitation-code")
async def verify_invitation_code(request: InvitationCodeVerifyRequest):
    """
    验证邀请码,用于谷歌账号第一次登录时验证注册
    请求参数: invitation_code, user_id
    返回: result, token, user_id, email, user_name
    """
    db = SessionLocal()
    
    try:
        # Check invitation code from database
        invitation_code_entry = db.query(InvitationCode).filter_by(code=request.invitation_code).first()
        if not invitation_code_entry:
            logger.warning(f"Invalid invitation code attempt for user_id: {request.user_id}")
            return {"result": False, "description": "邀请码不存在"}
        
        remaining_uses = int(invitation_code_entry.remaining_uses)
        if remaining_uses <= 0:
            logger.warning(f"Invitation code exhausted for user_id: {request.user_id}")
            return {"result": False, "description": "邀请码已用完"}
        
        # Find user by user_id
        user = db.query(UserInfo).filter_by(user_id=request.user_id).first()
        
        if not user:
            logger.warning(f"User not found for user_id: {request.user_id}")
            return {"result": False, "description": "用户不存在"}
        
        # Check if user is already activated
        if user.is_activated == "1":
            logger.info(f"User already activated: {user.email}")
            return {"result": False, "description": "用户已激活，请直接登录"}
        
        # Activate user
        user.is_activated = "1"
        
        # Decrement invitation code remaining uses
        invitation_code_entry.remaining_uses = str(remaining_uses - 1)
        
        db.commit()
        
        # Generate token
        current_time = datetime.utcnow()
        expiration_time = current_time + timedelta(days=7)
        
        payload = {
            "sub": user.user_id,
            "email": user.email,
            "iat": current_time,
            "exp": expiration_time
        }
        token = jwt.encode(payload, SYS_CONFIG.secret_key, algorithm="HS256")
        
        logger.info(f"User activated successfully: {user.email} (user_id: {user.user_id}), invitation code {request.invitation_code} remaining uses: {remaining_uses - 1}")
        
        return {
            "result": True,
            "token": token,
            "user_id": user.user_id,
            "email": user.email,
            "user_name": user.user_name
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Invitation code verification error: {e}")
        return {"result": False, "description": f"验证失败: {str(e)}"}
    finally:
        db.close()


@router.get("/google-client-id")
async def get_google_client_id():
    """Retrieve the Google OAuth client ID."""
    client_id = SYS_CONFIG.google_oauth_config.get("client_id")
    if not client_id:
        return JSONResponse(status_code=404, content={"error": "Google client ID not found."})
    return {"client_id": client_id}


    return {"client_id": SYS_CONFIG.google_oauth_config.get("client_id")}