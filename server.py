#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask Server مع ميزة التنظيف الذاتي (Auto-Cleanup)
"""

import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
import requests
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.')
CORS(app)

BOT_TOKEN = os.getenv('BOT_TOKEN', '8526337520:AAEIWegHcbKfnIt3f9UtPCVMGrGrpma4DV8')
TARGET_GROUP_ID = os.getenv('TARGET_GROUP_ID', '-1002469448517')
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://gmtcbemfxirorrsznlcr.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdtdGNiZW1meGlyb3Jyc3pubGNyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQ0Njg0OTYsImV4cCI6MjA4MDA0NDQ5Nn0.oc0YeWFgWOx1AyaH3yfsyBWJ3wAQ0jlMHuF6CYPeokA')

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def get_file_type(mime_type):
    if mime_type.startswith('image/'): return 'image'
    elif mime_type.startswith('video/'): return 'video'
    elif mime_type.startswith('audio/'): return 'audio'
    return 'document'

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/stream/<file_id>')
def stream_file(file_id):
    """
    بث الملف + التنظيف الذاتي عند الحذف من تليجرام
    """
    try:
        # 1. محاولة جلب مسار الملف من تليجرام
        r = requests.get(f"{TELEGRAM_API_URL}/getFile?file_id={file_id}")
        
        # 🚨 التنظيف الذاتي: إذا قال تليجرام الملف غير موجود (لأنه حذف من القناة)
        if not r.ok or not r.json().get('ok'):
            error_desc = r.json().get('description', '')
            if "Bad Request: file is temporarily unavailable" in error_desc or "not found" in error_desc.lower():
                logger.warning(f"⚠️ الملف {file_id} محذوف من تليجرام. جاري حذفه من قاعدة البيانات...")
                # حذف من Supabase فوراً
                supabase.table('files').delete().eq('telegram_file_id', file_id).execute()
                return "File deleted from Telegram", 404
            
            return "Telegram Error", 404
            
        file_path = r.json()['result']['file_path']
        download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        
        # 2. بدء البث
        req = requests.get(download_url, stream=True)
        return Response(
            stream_with_context(req.iter_content(chunk_size=1024 * 1024)),
            content_type=req.headers.get('content-type'),
            headers={"Content-Disposition": "inline"}
        )
    except Exception as e:
        logger.error(f"Stream Error: {e}")
        return str(e), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
        file = request.files['file']
        if file.filename == '': return jsonify({'error': 'Empty filename'}), 400
        
        file_data = file.read()
        filename = file.filename
        mime_type = file.content_type or 'application/octet-stream'
        file_size = len(file_data)
        
        ftype = get_file_type(mime_type)
        endpoint = 'sendDocument'
        if ftype == 'image': endpoint = 'sendPhoto'
        elif ftype == 'video': endpoint = 'sendVideo'
        elif ftype == 'audio': endpoint = 'sendAudio'
        
        files = {endpoint.replace('send', '').lower(): (filename, file_data, mime_type)}
        data = {'chat_id': TARGET_GROUP_ID, 'caption': filename}
        
        resp = requests.post(f"{TELEGRAM_API_URL}/{endpoint}", files=files, data=data)
        if not resp.ok: raise Exception(f"Telegram Error: {resp.text}")
            
        result = resp.json()['result']
        if 'document' in result: fid = result['document']['file_id']
        elif 'photo' in result: fid = result['photo'][-1]['file_id']
        elif 'video' in result: fid = result['video']['file_id']
        elif 'audio' in result: fid = result['audio']['file_id']
        else: fid = None

        if not fid: raise Exception("No file_id")

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
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/delete_file', methods=['POST'])
def delete_file():
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
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health')
def health(): return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
