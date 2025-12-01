#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask Server v3.0 (Monolithic - Railway Fixed)
تم دمج منطق الرفع والمصادقة مع إصلاحات المسارات لبيئة Railway
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
from src.core.auth import AuthManager
from src.core.permissions import PermissionManager
from src.core.config import config
from src.utils.email import email_service

# إعداد السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================================================
# 1. إصلاح المسارات لـ Railway (Absolute Paths)
# =========================================================
# نحدد المجلد الجذري للمشروع بدقة
current_dir = os.path.dirname(os.path.abspath(__file__)) # /app/src/api
project_root = os.path.dirname(os.path.dirname(current_dir)) # /app
TEMPLATE_DIR = os.path.join(project_root, 'templates')
STATIC_DIR = os.path.join(project_root, 'static')

logger.info(f"📂 Project Root: {project_root}")
logger.info(f"📄 TEMPLATE_DIR: {TEMPLATE_DIR}")

# =========================================================
# 2. إعداد التطبيق والخدمات
# =========================================================
app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
CORS(app)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24).hex())

# التحقق من الإعدادات
config.validate()

# خدمات Supabase و Telegram
supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
TELEGRAM_API_URL = config.TELEGRAM_API_URL
TARGET_GROUP_ID = config.TARGET_GROUP_ID
BOT_TOKEN = config.BOT_TOKEN # تأكدنا من إضافته للتحميل

auth_manager = AuthManager(supabase)
permission_manager = PermissionManager(supabase)

# =========================================================
# 3. دوال مساعدة (Helpers)
# =========================================================
def get_file_type(mime_type: str) -> str:
    if mime_type.startswith('image/'): return 'image'
    elif mime_type.startswith('video/'): return 'video'
    elif mime_type.startswith('audio/'): return 'audio'
    return 'document'

def get_current_user() -> Optional[Dict[str, Any]]:
    session_token = request.headers.get('Authorization')
    if not session_token: return None
    success, user_data = auth_manager.verify_session(session_token)
    return user_data if success else None

# =========================================================
# 4. مسارات الصفحات (HTML Pages) - تم الإصلاح هنا
# =========================================================

@app.route('/')
def index():
    """الصفحة الرئيسية"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"❌ Error rendering home: {e}")
        return f"Error loading template. Path: {TEMPLATE_DIR}", 500

@app.route('/login')
@app.route('/login.html')
def login_page():
    """صفحة تسجيل الدخول (حل مشكلة 404)"""
    try:
        return render_template('login.html')
    except Exception as e:
        logger.error(f"❌ Error rendering login: {e}")
        return "Error loading login page.", 500

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'version': '3.0', 'service': 'Telegram Archive Bot'})

# =========================================================
# 5. مسارات المصادقة (Auth API)
# =========================================================

@app.route('/api/auth/login', methods=['POST'])
def login_api():
    try:
        data = request.json
        success, user_data, message = auth_manager.login(data.get('email'), data.get('password'))
        if success: return jsonify({'success': True, 'user': user_data, 'message': message})
        return jsonify({'success': False, 'error': message}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/register/verify', methods=['POST'])
def verify_registration():
    try:
        data = request.json
        success, db_user_id, message = auth_manager.verify_user_data(data.get('user_id'), data.get('full_name'))
        if success: return jsonify({'success': True, 'user_db_id': db_user_id, 'message': message})
        return jsonify({'success': False, 'error': message}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/register/send-otp', methods=['POST'])
def send_otp():
    try:
        data = request.json
        success, message = auth_manager.send_activation_otp(data.get('user_db_id'), data.get('email'))
        if success: return jsonify({'success': True, 'message': message})
        return jsonify({'success': False, 'error': message}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/register/activate', methods=['POST'])
def activate_account():
    try:
        data = request.json
        success, message = auth_manager.verify_otp_and_activate(
            data.get('user_db_id'), data.get('email'), data.get('otp_code'), data.get('password')
        )
        if success: return jsonify({'success': True, 'message': message})
        return jsonify({'success': False, 'error': message}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/me', methods=['GET'])
def get_current_user_info():
    user = get_current_user()
    if not user: return jsonify({'error': 'غير مصرح'}), 401
    permissions = permission_manager.get_user_permissions(user['user_id'])
    user['permissions'] = permissions
    return jsonify({'success': True, 'user': user})

# =========================================================
# 6. مسارات الملفات (File API)
# =========================================================

@app.route('/api/files', methods=['GET'])
def get_files():
    user = get_current_user()
    if not user: return jsonify({'error': 'غير مصرح'}), 401
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 30))
        search = request.args.get('search', '')
        start = (page - 1) * per_page
        end = start + per_page - 1
        
        query = supabase.table('files').select('*', count='exact')
        if search: query = query.ilike('file_name', f'%{search}%')
        result = query.order('created_at', desc=True).range(start, end).execute()
        
        return jsonify({
            'success': True, 'files': result.data, 'total': result.count,
            'page': page, 'per_page': per_page
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stream/<file_id>')
def stream_file(file_id: str):
    try:
        # جلب مسار الملف من تليجرام
        r = requests.get(f"{TELEGRAM_API_URL}/getFile?file_id={file_id}")
        if r.status_code != 200 or not r.json().get('ok'):
            # إذا حذف من تليجرام نحذفه من القاعدة
            supabase.table('files').delete().eq('telegram_file_id', file_id).execute()
            return "File deleted/Not found", 404
            
        file_path = r.json()['result']['file_path']
        download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        
        # بث الملف كـ Stream
        req = requests.get(download_url, stream=True)
        content_type = req.headers.get('content-type')
        disposition = "inline" if content_type and (
            content_type.startswith(('image/', 'video/', 'audio/')) or content_type == 'application/pdf'
        ) else "attachment"
        
        return Response(
            stream_with_context(req.iter_content(chunk_size=1024 * 1024)),
            mimetype=content_type,
            headers={"Content-Disposition": disposition}
        )
    except Exception as e:
        logger.error(f"❌ Stream Error: {e}")
        return str(e), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    user = get_current_user()
    if not user: return jsonify({'error': 'غير مصرح'}), 401
    if not permission_manager.check_permission(user['user_id'], 'upload'):
        return jsonify({'error': 'No upload permission'}), 403

    try:
        if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
        file = request.files['file']
        caption = request.form.get('caption', '')
        
        file_data = file.read()
        filename = file.filename
        mime_type = file.content_type or 'application/octet-stream'
        ftype = get_file_type(mime_type)
        
        endpoint = 'sendDocument'
        if ftype == 'image': endpoint = 'sendPhoto'
        elif ftype == 'video': endpoint = 'sendVideo'
        elif ftype == 'audio': endpoint = 'sendAudio'
        
        files_payload = {endpoint.replace('send', '').lower(): (filename, file_data, mime_type)}
        full_caption = f"{caption}\n\n📤 By: {user['full_name']}" if caption else f"📤 By: {user['full_name']}"
        
        resp = requests.post(
            f"{TELEGRAM_API_URL}/{endpoint}", 
            files=files_payload, 
            data={'chat_id': TARGET_GROUP_ID, 'caption': full_caption}
        )
        
        if not resp.ok: raise Exception(f"Telegram Error: {resp.text}")
        result = resp.json()['result']
        
        # استخراج file_id
        if 'document' in result: fid = result['document']['file_id']
        elif 'photo' in result: fid = result['photo'][-1]['file_id']
        elif 'video' in result: fid = result['video']['file_id']
        elif 'audio' in result: fid = result['audio']['file_id']
        else: fid = None

        if not fid: raise Exception("No file_id found")

        db_data = {
            'file_name': filename, 'file_size': len(file_data), 'file_type': ftype,
            'mime_type': mime_type, 'telegram_file_id': fid, 'message_id': result['message_id'],
            'caption': caption, 'uploaded_by': user['user_id'], 'created_at': datetime.utcnow().isoformat()
        }
        
        supabase.table('files').insert(db_data).execute()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"❌ Upload Failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/delete_file', methods=['POST'])
def delete_file():
    user = get_current_user()
    if not user: return jsonify({'error': 'غير مصرح'}), 401
    if not permission_manager.check_permission(user['user_id'], 'delete'):
        return jsonify({'error': 'No delete permission'}), 403
    
    try:
        data = request.json
        if data.get('message_id'):
            requests.post(f"{TELEGRAM_API_URL}/deleteMessage", json={
                'chat_id': TARGET_GROUP_ID, 'message_id': data.get('message_id')
            })
        if data.get('id'):
            supabase.table('files').delete().eq('id', data.get('id')).execute()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# =========================================================
# 7. التنظيف التلقائي (Background)
# =========================================================
def cleanup_deleted_files():
    while True:
        time.sleep(60 * 60) # كل ساعة
        try:
            # يمكن تفعيل المنطق هنا لاحقاً لتجنب الضغط على السيرفر
            pass 
        except Exception:
            pass

# تشغيل خيط التنظيف فقط عند التشغيل المباشر أو عبر Gunicorn
# ملاحظة: في Gunicorn قد يتكرر هذا الخيط لكل Worker، لذا يفضل تعطيله أو استخدامه بحذر
# سنبقيه بسيطاً هنا
if os.environ.get('ENABLE_CLEANUP') == 'true':
    cleanup_thread = threading.Thread(target=cleanup_deleted_files, daemon=True)
    cleanup_thread.start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
