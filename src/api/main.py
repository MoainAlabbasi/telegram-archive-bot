#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask Server v3.0 للأرشيف
يوفر API لرفع وعرض وحذف الملفات مع نظام مصادقة وصلاحيات
"""

import os
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context, render_template
from flask_cors import CORS
import requests
from supabase import create_client, Client
from ..core.auth import AuthManager
from ..core.permissions import PermissionManager
from ..core.config import config
from ..utils.email import email_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# تحديد المسار المطلق للمجلدات بشكل صارم
# __file__ = /app/src/api/main.py (في Railway)
# BASE_DIR = /app (المجلد الجذر للمشروع)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

# طباعة المسارات للتأكد (مهم للتصحيح)
logger.info(f"📁 BASE_DIR: {BASE_DIR}")
logger.info(f"📄 TEMPLATE_DIR: {TEMPLATE_DIR}")
logger.info(f"📄 Templates exist: {os.path.exists(TEMPLATE_DIR)}")
if os.path.exists(TEMPLATE_DIR):
    logger.info(f"📄 Template files: {os.listdir(TEMPLATE_DIR)}")

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
CORS(app)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24).hex())

# التحقق من الإعدادات
config.validate()

# إنشاء عميل Supabase
supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
TELEGRAM_API_URL = config.TELEGRAM_API_URL
TARGET_GROUP_ID = config.TARGET_GROUP_ID

# إنشاء مديري المصادقة والصلاحيات
auth_manager = AuthManager(supabase)
permission_manager = PermissionManager(supabase)

def get_file_type(mime_type: str) -> str:
    """تحديد نوع الملف من MIME type"""
    if mime_type.startswith('image/'):
        return 'image'
    elif mime_type.startswith('video/'):
        return 'video'
    elif mime_type.startswith('audio/'):
        return 'audio'
    return 'document'

def get_current_user() -> Optional[Dict[str, Any]]:
    """الحصول على المستخدم الحالي من الجلسة"""
    session_token = request.headers.get('Authorization')
    if not session_token:
        return None
    
    success, user_data = auth_manager.verify_session(session_token)
    if success:
        return user_data
    return None

# ========================================
# Authentication Routes
# ========================================

@app.route('/api/auth/register/verify', methods=['POST'])
def verify_registration():
    """التحقق من بيانات المستخدم (الخطوة 2)"""
    try:
        data = request.json
        user_id = data.get('user_id')
        full_name = data.get('full_name')
        
        if not user_id or not full_name:
            return jsonify({'error': 'البيانات غير مكتملة'}), 400
        
        success, db_user_id, message = auth_manager.verify_user_data(user_id, full_name)
        
        if success:
            return jsonify({'success': True, 'user_db_id': db_user_id, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/register/send-otp', methods=['POST'])
def send_otp():
    """إرسال رمز OTP (الخطوة 3)"""
    try:
        data = request.json
        user_db_id = data.get('user_db_id')
        email = data.get('email')
        
        if not user_db_id or not email:
            return jsonify({'error': 'البيانات غير مكتملة'}), 400
        
        success, message = auth_manager.send_activation_otp(user_db_id, email)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/register/activate', methods=['POST'])
def activate_account():
    """تفعيل الحساب بعد التحقق من OTP"""
    try:
        data = request.json
        user_db_id = data.get('user_db_id')
        email = data.get('email')
        otp_code = data.get('otp_code')
        password = data.get('password')
        
        if not all([user_db_id, email, otp_code, password]):
            return jsonify({'error': 'البيانات غير مكتملة'}), 400
        
        success, message = auth_manager.verify_otp_and_activate(user_db_id, email, otp_code, password)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """تسجيل الدخول"""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'البيانات غير مكتملة'}), 400
        
        success, user_data, message = auth_manager.login(email, password)
        
        if success:
            return jsonify({'success': True, 'user': user_data, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """تسجيل الخروج"""
    try:
        session_token = request.headers.get('Authorization')
        if not session_token:
            return jsonify({'error': 'غير مصرح'}), 401
        
        auth_manager.logout(session_token)
        return jsonify({'success': True, 'message': 'تم تسجيل الخروج بنجاح'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/me', methods=['GET'])
def get_current_user_info():
    """الحصول على معلومات المستخدم الحالي"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'غير مصرح'}), 401
    
    # إضافة الصلاحيات
    permissions = permission_manager.get_user_permissions(user['user_id'])
    user['permissions'] = permissions
    
    return jsonify({'success': True, 'user': user})

# ========================================
# Admin Routes
# ========================================

@app.route('/api/admin/users/create', methods=['POST'])
def admin_create_user():
    """إنشاء مستخدم جديد بواسطة الأدمن"""
    user = get_current_user()
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'غير مصرح'}), 403
    
    try:
        data = request.json
        user_id = data.get('user_id')
        full_name = data.get('full_name')
        
        if not user_id or not full_name:
            return jsonify({'error': 'البيانات غير مكتملة'}), 400
        
        success, message = auth_manager.create_user_by_admin(user_id, full_name)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/users', methods=['GET'])
def admin_get_users():
    """الحصول على جميع المستخدمين"""
    user = get_current_user()
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'غير مصرح'}), 403
    
    try:
        users = permission_manager.get_all_users_with_permissions()
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/roles', methods=['GET'])
def admin_get_roles():
    """الحصول على جميع الصلاحيات"""
    user = get_current_user()
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'غير مصرح'}), 403
    
    try:
        roles = permission_manager.get_all_roles()
        return jsonify({'success': True, 'roles': roles})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/roles/create', methods=['POST'])
def admin_create_role():
    """إنشاء صلاحية جديدة"""
    user = get_current_user()
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'غير مصرح'}), 403
    
    try:
        data = request.json
        name = data.get('name')
        description = data.get('description')
        permissions = data.get('permissions', {})
        
        if not name:
            return jsonify({'error': 'اسم الصلاحية مطلوب'}), 400
        
        success, message = permission_manager.create_role(name, description, permissions)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/users/<int:user_id>/roles', methods=['POST'])
def admin_assign_role(user_id):
    """إسناد صلاحية لمستخدم"""
    user = get_current_user()
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'غير مصرح'}), 403
    
    try:
        data = request.json
        role_id = data.get('role_id')
        
        if not role_id:
            return jsonify({'error': 'معرف الصلاحية مطلوب'}), 400
        
        success, message = permission_manager.assign_role_to_user(user_id, role_id)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========================================
# File Routes
# ========================================

@app.route('/')
def index() -> Any:
    """صفحة الموقع الرئيسية"""
    try:
        logger.info("🏠 طلب الصفحة الرئيسية")
        return render_template('index.html')
    except Exception as e:
        logger.error(f"❌ خطأ في عرض الصفحة الرئيسية: {e}")
        # حل احتياطي: إرجاع HTML مباشر
        index_path = os.path.join(TEMPLATE_DIR, 'index.html')
        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8') as f:
                return f.read()
        return f"<h1>Error</h1><p>{str(e)}</p><p>TEMPLATE_DIR: {TEMPLATE_DIR}</p>", 500

@app.route('/stream/<file_id>')
def stream_file(file_id: str) -> Tuple[Any, int]:
    """بث الملف مع دعم المعاينة في المتصفح"""
    try:
        # جلب معلومات الملف من تليجرام
        r = requests.get(f"{TELEGRAM_API_URL}/getFile?file_id={file_id}")
        
        if r.status_code != 200 or not r.json().get('ok'):
            logger.warning(f"⚠️ الملف {file_id} غير موجود في تليجرام. جاري الحذف...")
            supabase.table('files').delete().eq('telegram_file_id', file_id).execute()
            return "File deleted", 404
            
        file_path = r.json()['result']['file_path']
        download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        
        # طلب البث من تليجرام
        req = requests.get(download_url, stream=True)
        content_type = req.headers.get('content-type')
        
        # تحديد طريقة العرض (inline للمعاينة، attachment للتحميل)
        # PDF يجب أن يعرض inline للمعاينة
        disposition = "inline" if content_type and (
            content_type.startswith('image/') or 
            content_type.startswith('video/') or 
            content_type == 'application/pdf'
        ) else "attachment"
        
        return Response(
            stream_with_context(req.iter_content(chunk_size=1024 * 1024)),
            mimetype=content_type,
            headers={
                "Content-Disposition": disposition,
                "Cache-Control": "public, max-age=3600"
            }
        )
    except Exception as e:
        logger.error(f"❌ خطأ في البث: {e}")
        return str(e), 500

@app.route('/api/files', methods=['GET'])
def get_files():
    """الحصول على قائمة الملفات مع Pagination"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'غير مصرح'}), 401
    
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 30))
        search = request.args.get('search', '')
        
        start = (page - 1) * per_page
        end = start + per_page - 1
        
        query = supabase.table('files').select('*', count='exact')
        
        # البحث
        if search:
            query = query.ilike('file_name', f'%{search}%')
        
        # الترتيب والتقسيم
        result = query.order('created_at', desc=True).range(start, end).execute()
        
        return jsonify({
            'success': True,
            'files': result.data,
            'total': result.count,
            'page': page,
            'per_page': per_page
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file() -> Tuple[Any, int]:
    """رفع ملف جديد"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'غير مصرح'}), 401
    
    # التحقق من صلاحية الرفع
    if not permission_manager.check_permission(user['user_id'], 'upload'):
        return jsonify({'error': 'ليس لديك صلاحية رفع الملفات'}), 403
    
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file'}), 400
        
        file = request.files['file']
        caption = request.form.get('caption', '')
        
        if file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400
        
        file_data = file.read()
        filename = file.filename
        mime_type = file.content_type or 'application/octet-stream'
        file_size = len(file_data)
        
        ftype = get_file_type(mime_type)
        endpoint = 'sendDocument'
        if ftype == 'image':
            endpoint = 'sendPhoto'
        elif ftype == 'video':
            endpoint = 'sendVideo'
        elif ftype == 'audio':
            endpoint = 'sendAudio'
        
        files = {endpoint.replace('send', '').lower(): (filename, file_data, mime_type)}
        
        # إضافة توقيع الرافع في Caption
        uploader_tag = f"\n\n📤 رفع بواسطة: {user['full_name']}"
        full_caption = (caption + uploader_tag) if caption else uploader_tag.strip()
        
        data = {'chat_id': TARGET_GROUP_ID, 'caption': full_caption}
        
        resp = requests.post(f"{TELEGRAM_API_URL}/{endpoint}", files=files, data=data)
        if not resp.ok:
            raise Exception(f"Telegram Error: {resp.text}")
            
        result = resp.json()['result']
        
        # استخراج file_id
        if 'document' in result:
            fid = result['document']['file_id']
        elif 'photo' in result:
            fid = result['photo'][-1]['file_id']
        elif 'video' in result:
            fid = result['video']['file_id']
        elif 'audio' in result:
            fid = result['audio']['file_id']
        else:
            fid = None

        if not fid:
            raise Exception("No file_id")

        db_data = {
            'file_name': filename,
            'file_size': file_size,
            'file_type': ftype,
            'mime_type': mime_type,
            'telegram_file_id': fid,
            'message_id': result['message_id'],
            'caption': caption,
            'uploaded_by': user['user_id'],
            'created_at': datetime.utcnow().isoformat()
        }
        
        supabase.table('files').insert(db_data).execute()
        logger.info(f"✅ تم رفع الملف: {filename} بواسطة {user['full_name']}")
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"❌ فشل الرفع: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/delete_file', methods=['POST'])
def delete_file() -> Tuple[Any, int]:
    """حذف ملف"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'غير مصرح'}), 401
    
    # التحقق من صلاحية الحذف
    if not permission_manager.check_permission(user['user_id'], 'delete'):
        return jsonify({'error': 'ليس لديك صلاحية حذف الملفات'}), 403
    
    try:
        data = request.json
        msg_id = data.get('message_id')
        db_id = data.get('id')
        
        if msg_id:
            # حذف من تليجرام
            requests.post(f"{TELEGRAM_API_URL}/deleteMessage", json={
                'chat_id': TARGET_GROUP_ID, 'message_id': msg_id
            })

        if db_id:
            # حذف من قاعدة البيانات
            supabase.table('files').delete().eq('id', db_id).execute()
            logger.info(f"🗑️ تم حذف الملف: ID={db_id} بواسطة {user['full_name']}")
            
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"❌ فشل الحذف: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/cleanup', methods=['POST'])
def cleanup() -> Tuple[Any, int]:
    """تنظيف الملفات المحذوفة"""
    user = get_current_user()
    if not user or not user.get('is_admin'):
        return jsonify({'error': 'غير مصرح'}), 403
    
    try:
        logger.info("🧹 بدء عملية التنظيف اليدوي...")
        result = supabase.table('files').select('id, telegram_file_id').execute()
        files = result.data
        
        deleted_count = 0
        for file in files:
            file_id = file['telegram_file_id']
            r = requests.get(f"{TELEGRAM_API_URL}/getFile?file_id={file_id}")
            
            if r.status_code != 200 or not r.json().get('ok'):
                supabase.table('files').delete().eq('id', file['id']).execute()
                deleted_count += 1
            
            time.sleep(0.3)
        
        logger.info(f"✅ انتهت عملية التنظيف. تم حذف {deleted_count} ملف")
        return jsonify({'success': True, 'deleted_count': deleted_count})
    except Exception as e:
        logger.error(f"❌ فشل التنظيف: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health')
def health() -> Any:
    """فحص صحة الخادم"""
    return jsonify({'status': 'ok', 'version': '3.0'})

def cleanup_deleted_files() -> None:
    """تنظيف دوري تلقائي للملفات المحذوفة"""
    time.sleep(5 * 60)
    
    while True:
        try:
            logger.info("🧹 بدء عملية التنظيف التلقائي...")
            
            result = supabase.table('files').select('id, telegram_file_id, file_name').execute()
            files = result.data
            
            deleted_count = 0
            for file in files:
                file_id = file['telegram_file_id']
                r = requests.get(f"{TELEGRAM_API_URL}/getFile?file_id={file_id}")
                
                if r.status_code != 200 or not r.json().get('ok'):
                    supabase.table('files').delete().eq('id', file['id']).execute()
                    deleted_count += 1
                    logger.info(f"🗑️ تم حذف: {file.get('file_name', 'unknown')}")
                
                time.sleep(0.5)
            
            logger.info(f"✅ انتهت عملية التنظيف التلقائي. تم حذف {deleted_count} ملف")
            
        except Exception as e:
            logger.error(f"❌ خطأ في التنظيف التلقائي: {e}")
        
        time.sleep(6 * 60 * 60)

if __name__ == '__main__':
    # بدء خيط التنظيف التلقائي
    cleanup_thread = threading.Thread(target=cleanup_deleted_files, daemon=True)
    cleanup_thread.start()
    
    logger.info("=" * 60)
    logger.info("🚀 بدء تشغيل خادم الأرشيف v3.0...")
    logger.info("🔐 نظام المصادقة: مفعّل")
    logger.info("🛡️ نظام الصلاحيات RBAC: مفعّل")
    logger.info("🧹 التنظيف التلقائي: مفعّل")
    logger.info("=" * 60)
    
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
