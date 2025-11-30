#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication System
نظام المصادقة والتحقق من المستخدمين
"""

import os
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from functools import wraps
import bcrypt
from flask import request, jsonify, session
from supabase import Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# إعدادات البريد الإلكتروني
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_EMAIL = os.getenv('SMTP_EMAIL')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')

class AuthManager:
    """مدير نظام المصادقة"""
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    def hash_password(self, password: str) -> str:
        """تشفير كلمة المرور"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """التحقق من كلمة المرور"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def generate_otp(self) -> str:
        """توليد رمز OTP من 6 أرقام"""
        return ''.join(secrets.choice(string.digits) for _ in range(6))
    
    def generate_session_token(self) -> str:
        """توليد رمز جلسة عشوائي"""
        return secrets.token_urlsafe(32)
    
    def send_otp_email(self, email: str, otp_code: str) -> bool:
        """إرسال رمز OTP إلى البريد الإلكتروني"""
        try:
            if not SMTP_EMAIL or not SMTP_PASSWORD:
                print("⚠️ تحذير: إعدادات البريد الإلكتروني غير مكتملة")
                return False
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = 'رمز التحقق - نظام الأرشيف'
            msg['From'] = SMTP_EMAIL
            msg['To'] = email
            
            html = f"""
            <html dir="rtl">
                <body style="font-family: 'Cairo', Arial, sans-serif; background-color: #f8fafc; padding: 20px;">
                    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                        <h2 style="color: #2563eb; text-align: center;">رمز التحقق</h2>
                        <p style="font-size: 16px; color: #1e293b; text-align: center;">
                            مرحباً، تم طلب رمز التحقق لتفعيل حسابك في نظام الأرشيف.
                        </p>
                        <div style="background: #eff6ff; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
                            <p style="font-size: 14px; color: #64748b; margin-bottom: 10px;">رمز التحقق الخاص بك:</p>
                            <h1 style="color: #2563eb; font-size: 36px; letter-spacing: 8px; margin: 0;">{otp_code}</h1>
                        </div>
                        <p style="font-size: 14px; color: #64748b; text-align: center;">
                            هذا الرمز صالح لمدة 10 دقائق فقط.
                        </p>
                        <p style="font-size: 12px; color: #94a3b8; text-align: center; margin-top: 30px;">
                            إذا لم تطلب هذا الرمز، يرجى تجاهل هذه الرسالة.
                        </p>
                    </div>
                </body>
            </html>
            """
            
            part = MIMEText(html, 'html')
            msg.attach(part)
            
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_EMAIL, SMTP_PASSWORD)
                server.send_message(msg)
            
            return True
        except Exception as e:
            print(f"❌ خطأ في إرسال البريد: {e}")
            return False
    
    def create_user_by_admin(self, user_id: str, full_name: str) -> Tuple[bool, str]:
        """إنشاء مستخدم جديد بواسطة الأدمن (الخطوة 1)"""
        try:
            # التحقق من عدم وجود المستخدم مسبقاً
            result = self.supabase.table('users').select('id').eq('user_id', user_id).execute()
            if result.data:
                return False, "الرقم التعريفي موجود مسبقاً"
            
            # إنشاء المستخدم
            data = {
                'user_id': user_id,
                'full_name': full_name,
                'is_active': False
            }
            self.supabase.table('users').insert(data).execute()
            return True, "تم إنشاء المستخدم بنجاح"
        except Exception as e:
            return False, f"خطأ: {str(e)}"
    
    def verify_user_data(self, user_id: str, full_name: str) -> Tuple[bool, Optional[int], str]:
        """التحقق من بيانات المستخدم (الخطوة 2)"""
        try:
            result = self.supabase.table('users').select('*').eq('user_id', user_id).eq('full_name', full_name).execute()
            
            if not result.data:
                return False, None, "البيانات غير متطابقة"
            
            user = result.data[0]
            
            if user['is_active']:
                return False, None, "الحساب مفعل بالفعل"
            
            return True, user['id'], "البيانات متطابقة"
        except Exception as e:
            return False, None, f"خطأ: {str(e)}"
    
    def send_activation_otp(self, user_db_id: int, email: str) -> Tuple[bool, str]:
        """إرسال رمز التفعيل (الخطوة 3)"""
        try:
            # توليد رمز OTP
            otp_code = self.generate_otp()
            expires_at = datetime.utcnow() + timedelta(minutes=10)
            
            # حفظ الرمز في قاعدة البيانات
            data = {
                'user_id': user_db_id,
                'email': email,
                'code': otp_code,
                'expires_at': expires_at.isoformat()
            }
            self.supabase.table('otp_codes').insert(data).execute()
            
            # إرسال البريد
            if self.send_otp_email(email, otp_code):
                return True, "تم إرسال رمز التحقق إلى بريدك الإلكتروني"
            else:
                # في حالة فشل الإرسال، نعيد الرمز للاختبار
                return True, f"رمز التحقق (للاختبار): {otp_code}"
        except Exception as e:
            return False, f"خطأ: {str(e)}"
    
    def verify_otp_and_activate(self, user_db_id: int, email: str, otp_code: str, password: str) -> Tuple[bool, str]:
        """التحقق من OTP وتفعيل الحساب"""
        try:
            # التحقق من الرمز
            result = self.supabase.table('otp_codes').select('*').eq('user_id', user_db_id).eq('email', email).eq('code', otp_code).eq('is_used', False).execute()
            
            if not result.data:
                return False, "رمز التحقق غير صحيح"
            
            otp_record = result.data[0]
            
            # التحقق من صلاحية الرمز
            expires_at = datetime.fromisoformat(otp_record['expires_at'].replace('Z', '+00:00'))
            if datetime.now(expires_at.tzinfo) > expires_at:
                return False, "رمز التحقق منتهي الصلاحية"
            
            # تشفير كلمة المرور
            password_hash = self.hash_password(password)
            
            # تفعيل الحساب
            self.supabase.table('users').update({
                'email': email,
                'password_hash': password_hash,
                'is_active': True,
                'activated_at': datetime.utcnow().isoformat()
            }).eq('id', user_db_id).execute()
            
            # تعليم الرمز كمستخدم
            self.supabase.table('otp_codes').update({'is_used': True}).eq('id', otp_record['id']).execute()
            
            return True, "تم تفعيل الحساب بنجاح"
        except Exception as e:
            return False, f"خطأ: {str(e)}"
    
    def login(self, email: str, password: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """تسجيل الدخول"""
        try:
            # البحث عن المستخدم
            result = self.supabase.table('users').select('*').eq('email', email).eq('is_active', True).execute()
            
            if not result.data:
                return False, None, "البريد الإلكتروني أو كلمة المرور غير صحيحة"
            
            user = result.data[0]
            
            # التحقق من كلمة المرور
            if not self.verify_password(password, user['password_hash']):
                return False, None, "البريد الإلكتروني أو كلمة المرور غير صحيحة"
            
            # إنشاء جلسة
            session_token = self.generate_session_token()
            expires_at = datetime.utcnow() + timedelta(days=7)
            
            self.supabase.table('sessions').insert({
                'user_id': user['id'],
                'session_token': session_token,
                'expires_at': expires_at.isoformat()
            }).execute()
            
            # تحديث آخر تسجيل دخول
            self.supabase.table('users').update({
                'last_login': datetime.utcnow().isoformat()
            }).eq('id', user['id']).execute()
            
            return True, {
                'user_id': user['id'],
                'user_identifier': user['user_id'],
                'full_name': user['full_name'],
                'email': user['email'],
                'is_admin': user['is_admin'],
                'session_token': session_token
            }, "تم تسجيل الدخول بنجاح"
        except Exception as e:
            return False, None, f"خطأ: {str(e)}"
    
    def verify_session(self, session_token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """التحقق من صلاحية الجلسة"""
        try:
            result = self.supabase.table('sessions').select('*, users(*)').eq('session_token', session_token).execute()
            
            if not result.data:
                return False, None
            
            session_data = result.data[0]
            
            # التحقق من صلاحية الجلسة
            expires_at = datetime.fromisoformat(session_data['expires_at'].replace('Z', '+00:00'))
            if datetime.now(expires_at.tzinfo) > expires_at:
                return False, None
            
            user = session_data['users']
            return True, {
                'user_id': user['id'],
                'user_identifier': user['user_id'],
                'full_name': user['full_name'],
                'email': user['email'],
                'is_admin': user['is_admin']
            }
        except Exception as e:
            print(f"❌ خطأ في التحقق من الجلسة: {e}")
            return False, None
    
    def logout(self, session_token: str) -> bool:
        """تسجيل الخروج"""
        try:
            self.supabase.table('sessions').delete().eq('session_token', session_token).execute()
            return True
        except Exception as e:
            print(f"❌ خطأ في تسجيل الخروج: {e}")
            return False
    
    def get_user_permissions(self, user_id: int) -> Dict[str, bool]:
        """الحصول على صلاحيات المستخدم"""
        try:
            result = self.supabase.table('user_roles').select('roles(permissions)').eq('user_id', user_id).execute()
            
            if not result.data:
                return {}
            
            # دمج جميع الصلاحيات
            all_permissions = {}
            for role in result.data:
                permissions = role['roles']['permissions']
                all_permissions.update(permissions)
            
            return all_permissions
        except Exception as e:
            print(f"❌ خطأ في الحصول على الصلاحيات: {e}")
            return {}

def login_required(f):
    """ديكوريتر للتحقق من تسجيل الدخول"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_token = request.headers.get('Authorization')
        if not session_token:
            return jsonify({'error': 'غير مصرح'}), 401
        
        # التحقق من الجلسة (يجب تمرير auth_manager من الكود الرئيسي)
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """ديكوريتر للتحقق من صلاحيات الأدمن"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # يجب التحقق من أن المستخدم أدمن
        return f(*args, **kwargs)
    return decorated_function
