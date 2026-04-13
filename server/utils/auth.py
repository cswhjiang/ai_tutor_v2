
from typing import Optional, Dict

import requests
import bcrypt

from conf.system import SYS_CONFIG
from src.logger import logger


# 在注册时加密密码
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')

# 在登录时验证密码
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


# Google OAuth verification function
def verify_google_authorization_code(authorization_code: str, redirect_uri: str) -> Optional[Dict[str, str]]:
    """
    验证Google授权码并获取用户信息
    
    参数:
        authorization_code: Google OAuth授权码
        redirect_uri: 前端使用的重定向URI
    
    返回:
        成功时返回包含email和name的字典，失败时返回None
    """
    try:
        # Step 1: Exchange authorization code for access token
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": authorization_code,
            "client_id": SYS_CONFIG.google_oauth_config.get("client_id"),
            "client_secret": SYS_CONFIG.google_oauth_config.get("client_secret"),
            "redirect_uri": redirect_uri,  # 使用前端传递的 redirect_uri
            "grant_type": "authorization_code"
        }
        
        token_response = requests.post(token_url, data=token_data, timeout=10)
        
        if token_response.status_code != 200:
            logger.error(f"Failed to exchange authorization code: {token_response.text}")
            return None
        
        token_info = token_response.json()
        access_token = token_info.get("access_token")
        
        if not access_token:
            logger.error("No access token in response")
            return None
        
        # Step 2: Use access token to get user info
        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        userinfo_response = requests.get(userinfo_url, headers=headers, timeout=10)
        
        if userinfo_response.status_code != 200:
            logger.error(f"Failed to get user info: {userinfo_response.text}")
            return None
        
        user_info = userinfo_response.json()
        
        email = user_info.get("email")
        name = user_info.get("name", email)  # Use email as name if name not provided
        
        if not email:
            logger.error("No email in user info")
            return None
        
        logger.info(f"Successfully retrieved Google user info for email: {email}")
        return {"email": email, "name": name}
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error during Google OAuth verification: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during Google OAuth verification: {e}")
        return None