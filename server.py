#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask Server لرفع الملفات إلى تليجرام وحفظها في Supabase
"""

import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from supabase import create_client, Client

# إعداد السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# إنشاء التطبيق
app = Flask(__name__, static_folder='.')
CORS(app)

# بيانات الاتصال
BOT_TOKEN = os.getenv('BOT_TOKEN', '8526337520:AAEIWegHcbKfnIt3f9UtPCVMGrGrpma4DV8')
TARGET_GROUP_ID = os.getenv('TARGET_GROUP_ID', '-1002469448517')
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://gmtcbemfxirorrsznlcr.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdtdGNiZW1meGlyb3Jyc3pubGNyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQ0Njg0OTYsImV4cCI6MjA4MDA0NDQ5Nn0.oc0YeWFgWOx1AyaH3yfsyBWJ3wAQ0jlMHuF6CYPeokA')

# إنشاء عميل Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# رابط Telegram API
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def get_file_type(mime_type):
    """تحديد نوع الملف بناءً على MIME type"""
    if mime_type.startswith('image/'):
        return 'image'
    elif mime_type.startswith('video/'):
        return 'video'
    elif mime_type.startswith('audio/'):
        return 'audio'
    else:
        return 'document'

def upload_to_telegram(file_data, file_name, mime_type):
    """رفع الملف إلى تليجرام"""
    try:
        # تحديد نوع الملف
        file_type = get_file_type(mime_type)
        
        # اختيار endpoint المناسب
        if file_type == 'image':
            endpoint = 'sendPhoto'
            file_key = 'photo'
        elif file_type == 'video':
            endpoint = 'sendVideo'
            file_key = 'video'
        elif file_type == 'audio':
            endpoint = 'sendAudio'
            file_key = 'audio'
        else:
            endpoint = 'sendDocument'
            file_key = 'document'
        
        # رفع الملف
        url = f"{TELEGRAM_API_URL}/{endpoint}"
        files = {file_key: (file_name, file_data, mime_type)}
        data = {'chat_id': TARGET_GROUP_ID}
        
        response = requests.post(url, files=files, data=data)
        result = response.json()
        
        if not result.get('ok'):
            raise Exception(f"Telegram API Error: {result.get('description')}")
        
        # استخراج معلومات الملف
        message = result['result']
        
        if file_type == 'image':
            file_info = message['photo'][-1]  # أكبر حجم
        elif file_type == 'video':
            file_info = message['video']
        elif file_type == 'audio':
            file_info = message['audio']
        else:
            file_info = message['document']
        
        file_id = file_info['file_id']
        file_size = file_info.get('file_size', 0)
        
        # الحصول على رابط الملف
        file_url_response = requests.get(f"{TELEGRAM_API_URL}/getFile?file_id={file_id}")
        file_url_result = file_url_response.json()
        
        if file_url_result.get('ok'):
            file_path = file_url_result['result']['file_path']
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        else:
            file_url = ""
        
        return {
            'file_id': file_id,
            'file_size': file_size,
            'file_url': file_url,
            'message_id': message['message_id']
        }
        
    except Exception as e:
        logger.error(f"خطأ في رفع الملف إلى تليجرام: {str(e)}")
        raise

@app.route('/')
def index():
    """عرض الصفحة الرئيسية"""
    return send_from_directory('.', 'index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """رفع ملف جديد"""
    try:
        # التحقق من وجود ملف
        if 'file' not in request.files:
            return jsonify({'error': 'لم يتم إرسال ملف'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'اسم الملف فارغ'}), 400
        
        # قراءة الملف
        file_data = file.read()
        file_name = file.filename
        mime_type = file.content_type or 'application/octet-stream'
        file_size = len(file_data)
        
        logger.info(f"📤 رفع ملف: {file_name} ({file_size} bytes)")
        
        # رفع إلى تليجرام
        telegram_result = upload_to_telegram(file_data, file_name, mime_type)
        
        # حفظ في Supabase
        data = {
            'file_name': file_name,
            'file_size': file_size,
            'file_type': get_file_type(mime_type),
            'mime_type': mime_type,
            'telegram_file_id': telegram_result['file_id'],
            'file_url': telegram_result['file_url'],
            'message_id': telegram_result['message_id'],
            'created_at': datetime.utcnow().isoformat()
        }
        
        result = supabase.table('files').insert(data).execute()
        
        logger.info(f"✅ تم حفظ الملف بنجاح: {file_name}")
        
        return jsonify({
            'success': True,
            'message': 'تم رفع الملف بنجاح',
            'data': data
        })
        
    except Exception as e:
        logger.error(f"❌ خطأ في رفع الملف: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/files', methods=['GET'])
def get_files():
    """الحصول على قائمة الملفات"""
    try:
        result = supabase.table('files').select('*').order('created_at', desc=True).execute()
        return jsonify({
            'success': True,
            'data': result.data
        })
    except Exception as e:
        logger.error(f"خطأ في جلب الملفات: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """الحصول على إحصائيات الملفات"""
    try:
        result = supabase.table('files').select('file_size, file_type').execute()
        files = result.data
        
        total_files = len(files)
        total_size = sum(f.get('file_size', 0) for f in files)
        file_types = len(set(f.get('file_type') for f in files))
        
        return jsonify({
            'success': True,
            'data': {
                'total_files': total_files,
                'total_size': total_size,
                'file_types': file_types
            }
        })
    except Exception as e:
        logger.error(f"خطأ في جلب الإحصائيات: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """فحص صحة الخادم"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    logger.info(f"🚀 بدء تشغيل الخادم على المنفذ {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
