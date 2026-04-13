from pydantic import BaseModel, EmailStr

# Request model for verification code
class SendVerificationCodeRequest(BaseModel):
    email: EmailStr

# Request model for user registration
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    invitation_code: str
    verification_code: str

# Request model for new login
class NewLoginRequest(BaseModel):
    email: EmailStr
    password: str

# Request model for token verification
class TokenVerifyRequest(BaseModel):
    token: str
    user_id: str

# Request model for Google code verification
class GoogleCodeVerifyRequest(BaseModel):
    authorization_code: str
    redirect_uri: str  # 前端传递的 redirect_uri，例如: ${window.location.origin}/google-callback

# Request model for invitation code verification (Google OAuth)
class InvitationCodeVerifyRequest(BaseModel):
    invitation_code: str
    user_id: str
