#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Email Utility Module
وحدة إرسال البريد الإلكتروني
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from ..core.config import config

logger = logging.getLogger(__name__)


class EmailService:
    """خدمة إرسال البريد الإلكتروني"""
    
    def __init__(self):
        self.smtp_server = config.SMTP_SERVER
        self.smtp_port = config.SMTP_PORT
        self.smtp_email = config.SMTP_EMAIL
        self.smtp_password = config.SMTP_PASSWORD
    
    def send_otp_email(self, to_email: str, otp_code: str) -> bool:
        """إرسال كود OTP إلى البريد الإلكتروني"""
        
        subject = "🔐 كود التحقق - Telegram Archive Bot"
        
        html_body = f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Cairo', 'Segoe UI', Tahoma, sans-serif;
                    background-color: #0f172a;
                    color: #e2e8f0;
                    padding: 20px;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
                    border-radius: 16px;
                    padding: 40px;
                    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
                }}
                .logo {{
                    text-align: center;
                    font-size: 48px;
                    margin-bottom: 20px;
                }}
                h1 {{
                    color: #818cf8;
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .otp-box {{
                    background: rgba(129, 140, 248, 0.1);
                    border: 2px solid #818cf8;
                    border-radius: 12px;
                    padding: 30px;
                    text-align: center;
                    margin: 30px 0;
                }}
                .otp-code {{
                    font-size: 42px;
                    font-weight: 800;
                    color: #818cf8;
                    letter-spacing: 8px;
                    font-family: 'Courier New', monospace;
                }}
                .info {{
                    background: rgba(248, 113, 113, 0.1);
                    border-right: 4px solid #f87171;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    color: #64748b;
                    font-size: 14px;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #334155;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">🔐</div>
                <h1>كود التحقق</h1>
                
                <p style="text-align: center; font-size: 18px; color: #cbd5e1;">
                    مرحباً! تم طلب كود تحقق لتفعيل حسابك في نظام أرشيف تليجرام.
                </p>
                
                <div class="otp-box">
                    <p style="margin: 0 0 10px 0; color: #94a3b8;">كود التحقق الخاص بك:</p>
                    <div class="otp-code">{otp_code}</div>
                </div>
                
                <div class="info">
                    <p style="margin: 5px 0;"><strong>⏰ صلاحية الكود:</strong> 10 دقائق</p>
                    <p style="margin: 5px 0;"><strong>⚠️ تحذير:</strong> لا تشارك هذا الكود مع أي شخص</p>
                </div>
                
                <p style="text-align: center; color: #94a3b8; margin-top: 30px;">
                    إذا لم تطلب هذا الكود، يمكنك تجاهل هذه الرسالة بأمان.
                </p>
                
                <div class="footer">
                    <p>Telegram Archive Bot v3.0</p>
                    <p>نظام إدارة الملفات الاحترافي</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(to_email, subject, html_body)
    
    def _send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str
    ) -> bool:
        """إرسال بريد إلكتروني"""
        
        if not all([self.smtp_email, self.smtp_password]):
            logger.error("❌ بيانات SMTP غير مكتملة")
            return False
        
        try:
            # إنشاء الرسالة
            message = MIMEMultipart('alternative')
            message['From'] = self.smtp_email
            message['To'] = to_email
            message['Subject'] = subject
            
            # إضافة المحتوى HTML
            html_part = MIMEText(html_body, 'html', 'utf-8')
            message.attach(html_part)
            
            # الاتصال بخادم SMTP وإرسال الرسالة
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_email, self.smtp_password)
                server.send_message(message)
            
            logger.info(f"✅ تم إرسال البريد الإلكتروني إلى: {to_email}")
            return True
        
        except Exception as e:
            logger.error(f"❌ خطأ في إرسال البريد الإلكتروني: {e}")
            return False


# إنشاء نسخة واحدة من الخدمة
email_service = EmailService()
