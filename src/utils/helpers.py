#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helper Functions Module
دوال مساعدة عامة
"""

import secrets
import string
from datetime import datetime, timedelta
from typing import Optional


def generate_otp(length: int = 6) -> str:
    """توليد كود OTP عشوائي"""
    digits = string.digits
    return ''.join(secrets.choice(digits) for _ in range(length))


def generate_session_token(length: int = 32) -> str:
    """توليد Session Token عشوائي"""
    return secrets.token_urlsafe(length)


def is_expired(created_at: str, expiry_minutes: int) -> bool:
    """التحقق من انتهاء صلاحية شيء ما"""
    try:
        created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        expiry_time = created_time + timedelta(minutes=expiry_minutes)
        return datetime.utcnow() > expiry_time
    except:
        return True


def format_file_size(size_bytes: int) -> str:
    """تنسيق حجم الملف بشكل قابل للقراءة"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def sanitize_filename(filename: str) -> str:
    """تنظيف اسم الملف من الأحرف غير المسموح بها"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename


def get_file_extension(filename: str) -> Optional[str]:
    """الحصول على امتداد الملف"""
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return None


def is_image_file(filename: str) -> bool:
    """التحقق من أن الملف صورة"""
    image_extensions = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'}
    ext = get_file_extension(filename)
    return ext in image_extensions if ext else False


def is_video_file(filename: str) -> bool:
    """التحقق من أن الملف فيديو"""
    video_extensions = {'mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm'}
    ext = get_file_extension(filename)
    return ext in video_extensions if ext else False


def is_document_file(filename: str) -> bool:
    """التحقق من أن الملف مستند"""
    document_extensions = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt'}
    ext = get_file_extension(filename)
    return ext in document_extensions if ext else False
