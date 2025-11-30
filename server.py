#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask Server للأرشيف
يوفر API لرفع وعرض وحذف الملفات
النسخة المحسنة: تنظيف تلقائي، Type Hints، أمان محسّن
"""

import os
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any, Tuple
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
import requests
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.')
CORS(app)

# المتغيرات البيئية (بدون قيم افتراضية للأمان)
BOT_TOKEN = os.getenv('BOT_TOKEN')
TARGET_GROUP_ID_STR = os.getenv('TARGET_GROUP_ID')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

def validate_environment_variables() -> None:
    """التحقق من وجود جميع المتغيرات البيئية المطلوبة"""
    missing_vars = []
    
    if not BOT_TOKEN:
        missing_vars.append('BOT_TOKEN')
    if not TARGET_GROUP_ID_STR:
        missing_vars.append('TARGET_GROUP_ID')
    if not SUPABASE_URL:
        missing_vars.append('SUPABASE_URL')
    if not SUPABASE_KEY:
        missing_vars.append('SUPABASE_KEY')
    
    if missing_vars:
        error_msg = f"❌ خطأ: المتغيرات البيئية التالية مفقودة: {', '.join(missing_vars)}\n"
        error_msg += "يرجى تعيينها في ملف .env أو في متغيرات البيئة."
        logger.error(error_msg)
        raise ValueError(error_msg)

# التحقق من المتغيرات
validate_environment_variables()

# تحويل TARGET_GROUP_ID إلى رقم صحيح
try:
    TARGET_GROUP_ID = int(TARGET_GROUP_ID_STR)
except ValueError:
    raise ValueError(f"❌ خطأ: TARGET_GROUP_ID يجب أن يكون رقماً صحيحاً، القيمة الحالية: {TARGET_GROUP_ID_STR}")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def get_file_type(mime_type: str) -> str:
    """
    تحديد نوع الملف من MIME type
    
    Args:
        mime_type: نوع MIME للملف
        
    Returns:
        نوع الملف (image, video, audio, document)
    """
    if mime_type.startswith('image/'):
        return 'image'
    elif mime_type.startswith('video/'):
        return 'video'
    elif mime_type.startswith('audio/'):
        return 'audio'
    return 'document'

@app.route('/')
def index() -> Any:
    """صفحة الموقع الرئيسية"""
    return send_from_directory('.', 'index.html')

@app.route('/stream/<file_id>')
def stream_file(file_id: str) -> Tuple[Any, int]:
    """
    بث الملف مع إجبار المتصفح على العرض (Inline) والتنظيف التلقائي
    
    Args:
        file_id: معرف الملف في تليجرام
        
    Returns:
        استجابة بث الملف أو رسالة خطأ
    """
    try:
        # 1. جلب معلومات الملف من تليجرام
        r = requests.get(f"{TELEGRAM_API_URL}/getFile?file_id={file_id}")
        
        # 🚨 التنظيف الذاتي الصارم: أي خطأ من تليجرام يعني الملف غير موجود
        if r.status_code != 200 or not r.json().get('ok'):
            logger.warning(f"⚠️ الملف {file_id} غير موجود في تليجرام. جاري الحذف...")
            # حذف فوري من Supabase
            supabase.table('files').delete().eq('telegram_file_id', file_id).execute()
            return "File deleted", 404
            
        file_path = r.json()['result']['file_path']
        download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        
        # 2. طلب البث من تليجرام
        req = requests.get(download_url, stream=True)
        
        # الحصول على نوع الملف الحقيقي (MIME Type)
        content_type = req.headers.get('content-type')
        
        # 3. إرسال الاستجابة مع إجبار العرض (inline)
        return Response(
            stream_with_context(req.iter_content(chunk_size=1024 * 1024)),
            mimetype=content_type,
            headers={
                "Content-Disposition": "inline",
                "Cache-Control": "public, max-age=3600"
            }
        )
    except Exception as e:
        logger.error(f"❌ خطأ في البث: {e}")
        return str(e), 500

@app.route('/upload', methods=['POST'])
def upload_file() -> Tuple[Any, int]:
    """
    رفع ملف جديد إلى تليجرام وحفظه في قاعدة البيانات
    
    Returns:
        استجابة JSON بنجاح أو فشل العملية
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file'}), 400
        
        file = request.files['file']
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
        data = {'chat_id': TARGET_GROUP_ID, 'caption': filename}
        
        resp = requests.post(f"{TELEGRAM_API_URL}/{endpoint}", files=files, data=data)
        if not resp.ok:
            raise Exception(f"Telegram Error: {resp.text}")
            
        result = resp.json()['result']
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
            'created_at': datetime.utcnow().isoformat()
        }
        
        supabase.table('files').insert(db_data).execute()
        logger.info(f"✅ تم رفع الملف: {filename} ({file_size:,} bytes)")
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"❌ فشل الرفع: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/delete_file', methods=['POST'])
def delete_file() -> Tuple[Any, int]:
    """
    حذف ملف من تليجرام وقاعدة البيانات
    
    Returns:
        استجابة JSON بنجاح أو فشل العملية
    """
    try:
        data = request.json
        msg_id = data.get('message_id')
        db_id = data.get('id')
        
        if msg_id:
            requests.post(f"{TELEGRAM_API_URL}/deleteMessage", json={
                'chat_id': TARGET_GROUP_ID, 'message_id': msg_id
            })

        if db_id:
            supabase.table('files').delete().eq('id', db_id).execute()
            logger.info(f"🗑️ تم حذف الملف: ID={db_id}")
            
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"❌ فشل الحذف: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/cleanup', methods=['POST'])
def cleanup() -> Tuple[Any, int]:
    """
    تنظيف الملفات المحذوفة من تليجرام (يدوي)
    
    Returns:
        استجابة JSON بعدد الملفات المحذوفة
    """
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
                logger.info(f"🗑️ تم حذف ملف محذوف: {file_id}")
            
            # انتظار قصير لتجنب Rate Limiting
            time.sleep(0.3)
        
        logger.info(f"✅ انتهت عملية التنظيف. تم حذف {deleted_count} ملف")
        return jsonify({'success': True, 'deleted_count': deleted_count})
    except Exception as e:
        logger.error(f"❌ فشل التنظيف: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health')
def health() -> Any:
    """فحص صحة الخادم"""
    return jsonify({'status': 'ok'})

def cleanup_deleted_files() -> None:
    """
    تنظيف دوري تلقائي للملفات المحذوفة من تليجرام
    يعمل في الخلفية كل 6 ساعات
    """
    # انتظار 5 دقائق قبل البدء (لإعطاء الخادم وقت للتشغيل)
    time.sleep(5 * 60)
    
    while True:
        try:
            logger.info("=" * 60)
            logger.info("🧹 بدء عملية التنظيف التلقائي...")
            
            result = supabase.table('files').select('id, telegram_file_id, file_name').execute()
            files = result.data
            
            deleted_count = 0
            for file in files:
                file_id = file['telegram_file_id']
                
                # التحقق من وجود الملف في تليجرام
                r = requests.get(f"{TELEGRAM_API_URL}/getFile?file_id={file_id}")
                
                # إذا كان الملف غير موجود، احذفه من قاعدة البيانات
                if r.status_code != 200 or not r.json().get('ok'):
                    supabase.table('files').delete().eq('id', file['id']).execute()
                    deleted_count += 1
                    logger.info(f"🗑️ تم حذف: {file.get('file_name', 'unknown')}")
                
                # انتظار قصير لتجنب Rate Limiting
                time.sleep(0.5)
            
            logger.info(f"✅ انتهت عملية التنظيف التلقائي. تم حذف {deleted_count} ملف")
            logger.info("⏰ التنظيف القادم بعد 6 ساعات")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"❌ خطأ في التنظيف التلقائي: {e}")
        
        # تكرار كل 6 ساعات
        time.sleep(6 * 60 * 60)

if __name__ == '__main__':
    # بدء خيط التنظيف التلقائي في الخلفية
    cleanup_thread = threading.Thread(target=cleanup_deleted_files, daemon=True)
    cleanup_thread.start()
    logger.info("=" * 60)
    logger.info("🚀 بدء تشغيل خادم الأرشيف...")
    logger.info("🧹 تم تفعيل التنظيف التلقائي (كل 6 ساعات)")
    logger.info(f"🔗 Supabase URL: {SUPABASE_URL}")
    logger.info("=" * 60)
    
    # تشغيل الخادم
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
