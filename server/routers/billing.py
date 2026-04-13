import os
import jwt
from typing import Optional
import json

from fastapi.responses import JSONResponse
from fastapi import APIRouter, Form, Cookie, Request
import stripe

from conf.system import SYS_CONFIG
from src.logger import logger
from server.database import SessionLocal
from server.models import UserInfo

router = APIRouter()

# Configure Stripe credentials once during startup
stripe_secret_key = SYS_CONFIG.stripe_config.get("secret_key")
if stripe_secret_key:
    stripe.api_key = stripe_secret_key
STRIPE_WEBHOOK_SECRET = SYS_CONFIG.stripe_config.get("webhook_secret")


@router.get("stripe-session-status")
async def stripe_session_status(
    session_id: str,
    token: Optional[str] = Cookie(None),
    user_id: Optional[str] = Cookie(None)
):
    """
    获取Stripe支付会话状态
    请求参数: session_id, token, user_id (cookie)
    返回: result, status, customer_email
    """
    if not token or not user_id:
        return {"result": False, "description": "缺少token或user_id"}

    try:
        # Verify JWT token
        try:
            payload = jwt.decode(token, SYS_CONFIG.secret_key, algorithms=["HS256"])
            token_user_id = payload.get("sub")

            if token_user_id != user_id:
                logger.warning(f"Token verification failed: user_id mismatch")
                return {"result": False, "description": "token验证失败"}

        except jwt.ExpiredSignatureError:
            logger.info(f"Token expired for user_id: {user_id}")
            return {"result": False, "description": "token已过期"}
        except jwt.InvalidTokenError:
            logger.warning(f"Invalid token for user_id: {user_id}")
            return {"result": False, "description": "无效的token"}

        # Retrieve session status
        session = stripe.checkout.Session.retrieve(session_id)

        logger.info(f"Stripe session status retrieved for user_id: {user_id}, session_id: {session_id}, status: {session.status}")

        return {
            "result": True,
            "status": session.status,
            "customer_email": session.customer_details.email if session.customer_details else None
        }

    except Exception as e:
        logger.error(f"Error retrieving session status: {e}")
        return {"result": False, "description": f"获取会话状态失败: {str(e)}"}


@router.post("/order_info_stripe")
async def create_order(
    subscription_info: str = Form(...),
    email: str = Form(...),
    token: Optional[str] = Cookie(None),
    user_id: Optional[str] = Cookie(None)
):
    if not token or not user_id:
        return {"result": False, "description": "缺少token或user_id"}

    db = SessionLocal()

    try:
        # Verify JWT token
        try:
            payload = jwt.decode(token, SYS_CONFIG.secret_key, algorithms=["HS256"])
            token_user_id = payload.get("sub")

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
            logger.warning(f"User not found for user_id: {user_id}")
            return {"result": False, "description": "用户不存在"}

        # Get the price_id for the subscription
        price_id = SYS_CONFIG.stripe_config.get("price_ids", {}).get(subscription_info)

        if not price_id:
            logger.error(f"Price ID not found for subscription: {subscription_info}")
            return {"result": False, "description": "套餐配置错误，请联系管理员"}

        domain = os.getenv("DOMAIN", "http://localhost")
        # Create Stripe Checkout Session with embedded UI
        try:
            checkout_session = stripe.checkout.Session.create(
                ui_mode='embedded',
                line_items=[
                    {
                        'price': price_id,
                        'quantity': 1,
                    },
                ],
                mode='subscription',
                return_url=f"{domain}/stripe-callback?session_id={{CHECKOUT_SESSION_ID}}",
                customer_email=email
            )

            logger.info(f"Stripe embedded checkout session created for user_id: {user_id}, subscription: {subscription_info}")

            return {
                "result": True,
                "clientSecret": checkout_session.client_secret
            }

        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return {"result": False, "description": f"创建订单失败: {str(e)}"}
        
    finally:
        db.close()

@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Stripe webhook endpoint to process asynchronous payment events."""
    payload_bytes = await request.body()
    payload_str = payload_bytes.decode("utf-8")
    try:
        event = json.loads(payload_str)
    except json.JSONDecodeError as exc:
        logger.warning(f"Stripe webhook payload parse error: {exc}")
        return JSONResponse(status_code=400, content={"success": False})

    if STRIPE_WEBHOOK_SECRET:
        sig_header = request.headers.get("stripe-signature")
        if not sig_header:
            logger.warning("Stripe webhook signature header missing")
            return JSONResponse(status_code=400, content={"success": False})
        try:
            event = stripe.Webhook.construct_event(
                payload=payload_str,
                sig_header=sig_header,
                secret=STRIPE_WEBHOOK_SECRET,
            )
        except stripe.error.SignatureVerificationError as exc:
            logger.warning(f"Stripe webhook signature verification failed: {exc}")
            return JSONResponse(status_code=400, content={"success": False})

    event_type = event.get("type")
    
    if event_type == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        amount = payment_intent.get("amount")
        logger.info(f"Payment for {amount} succeeded")
        # TODO: add business logic for successful payment intents if needed.
    elif event_type == "payment_method.attached":
        payment_method = event["data"]["object"]
        logger.info(f"Payment method attached: {payment_method.get('id')}")
        # TODO: add business logic for attached payment methods if needed.
    else:
        logger.info(f"Unhandled Stripe event type: {event_type}")

    logger.info(payment_intent)
    return JSONResponse(content={"success": True})


@router.get("/stripe-publishable-key")
async def get_stripe_publishable_key():
    """Retrieve the Stripe publishable key."""
    publishable_key = SYS_CONFIG.stripe_config.get("publishable_key")
    if not publishable_key:
        return JSONResponse(status_code=404, content={"error": "Stripe publishable key not found."})
    return {"publishable_key": publishable_key}