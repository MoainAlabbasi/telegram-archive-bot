#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration Module
إعدادات المشروع المركزية
"""

import os
from typing import Optional


class Config:
    """إعدادات المشروع"""
    
    # Telegram Bot Configuration
    BOT_TOKEN: str = os.getenv('BOT_TOKEN', '')
    TARGET_GROUP_ID: int = int(os.getenv('TARGET_GROUP_ID', '0'))
    
    # Supabase Configuration
    SUPABASE_URL: str = os.getenv('SUPABASE_URL', '')
    SUPABASE_KEY: str = os.getenv('SUPABASE_KEY', '')
    
    # Email Configuration
    SMTP_SERVER: str = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT: int = int(os.getenv('SMTP_PORT', '587'))
    SMTP_EMAIL: str = os.getenv('SMTP_EMAIL', '')
    SMTP_PASSWORD: str = os.getenv('SMTP_PASSWORD', '')
    
    # Server Configuration
    SECRET_KEY: str = os.getenv('SECRET_KEY', os.urandom(24).hex())
    PORT: int = int(os.getenv('PORT', '8080'))
    HOST: str = os.getenv('HOST', '0.0.0.0')
    
    # Telegram API
    TELEGRAM_API_URL: str = f"https://api.telegram.org/bot{BOT_TOKEN}"
    
    # OTP Configuration
    OTP_EXPIRY_MINUTES: int = 10
    
    # Session Configuration
    SESSION_EXPIRY_HOURS: int = 24 * 7  # أسبوع
    
    @classmethod
    def validate(cls) -> bool:
        """التحقق من صحة الإعدادات المطلوبة"""
        required_vars = [
            'BOT_TOKEN',
            'TARGET_GROUP_ID',
            'SUPABASE_URL',
            'SUPABASE_KEY',
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(
                f"❌ المتغيرات البيئية التالية مفقودة: {', '.join(missing_vars)}"
            )
        
        return True
    
    @classmethod
    def get_telegram_file_url(cls, file_path: str) -> str:
        """الحصول على رابط ملف من تليجرام"""
        return f"https://api.telegram.org/file/bot{cls.BOT_TOKEN}/{file_path}"


# إنشاء نسخة واحدة من الإعدادات
config = Config()
