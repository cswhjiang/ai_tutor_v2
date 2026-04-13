
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
from concurrent.futures import ThreadPoolExecutor


from conf.system import SYS_CONFIG
from src.logger import logger


# Thread pool executor for async email sending
email_executor = ThreadPoolExecutor(max_workers=3)

# Function to send email using smtplib (synchronous)
def send_email_smtp_sync(recipient_email: str, subject: str, body: str):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = SYS_CONFIG.email_config['sender_email']
    sender_password = SYS_CONFIG.email_config['sender_password']

    # Create the email message
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = subject

    # Attach the email body
    message.attach(MIMEText(body, "plain"))

    # Connect to the SMTP server and send the email
    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            server.starttls()  # Upgrade the connection to secure
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, message.as_string())
            logger.info(f"Verification email sent successfully to {recipient_email}")
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Authentication failed: {e}")
        # 不抛出异常，只记录日志
    except TimeoutError as e:
        logger.error(f"SMTP connection timeout for {recipient_email}: {e}")
        # 不抛出异常，只记录日志
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {e}")
        # 不抛出异常，只记录日志


# Async wrapper for email sending
async def send_email_smtp(recipient_email: str, subject: str, body: str):
    """异步发送邮件，不阻塞API响应"""
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(email_executor, send_email_smtp_sync, recipient_email, subject, body)
    except Exception as e:
        logger.error(f"Async email sending failed for {recipient_email}: {e}")
        # 不再抛出异常，避免未捕获的 task exception