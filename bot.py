#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram File Archive Bot
يستمع للمجموعة ويحفظ روابط الملفات في Supabase
النسخة المحسنة: تدعم الرسائل المحولة (Forwarded) وتتجنب الأخطاء
"""

import os
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from supabase import create_client, Client

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# بيانات الاتصال من المتغيرات البيئية
BOT_TOKEN = os.getenv('BOT_TOKEN', '8526337520:AAEIWegHcbKfnIt3f9UtPCVMGrGrpma4DV8')
TARGET_GROUP_ID = int(os.getenv('TARGET_GROUP_ID', '-1002469448517'))
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://gmtcbemfxirorrsznlcr.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdtdGNiZW1meGlyb3Jyc3pubGNyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQ0Njg0OTYsImV4cCI6MjA4MDA0NDQ5Nn0.oc0YeWFgWOx1AyaH3yfsyBWJ3wAQ0jlMHuF6CYPeokA')

# إنشاء عميل Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج استلام الملفات من المجموعة"""
    
    # التحقق من أن الرسالة من المجموعة المستهدفة
    if update.effective_chat.id != TARGET_GROUP_ID:
        # logger.info(f"تجاهل رسالة من مجموعة غير مستهدفة: {update.effective_chat.id}")
        return
    
    try:
        # استخدام effective_message بدلاً من message لتجنب الأخطاء في الرسائل المحولة
        message = update.effective_message
        if not message:
            return

        document = message.document
        if not document:
            return
        
        # استخراج معلومات الملف
        file_id = document.file_id
        file_name = document.file_name or "unknown_file"
        file_size = document.file_size or 0
        mime_type = document.mime_type or "application/octet-stream"
        
        # تحديد نوع الملف
        file_type = "document"
        if mime_type.startswith("image/"):
            file_type = "image"
        elif mime_type.startswith("video/"):
            file_type = "video"
        elif mime_type.startswith("audio/"):
            file_type = "audio"
        
        # الحصول على رابط الملف
        file = await context.bot.get_file(file_id)
        file_url = file.file_path
        
        # حفظ البيانات في Supabase
        data = {
            "file_name": file_name,
            "file_size": file_size,
            "file_type": file_type,
            "mime_type": mime_type,
            "telegram_file_id": file_id,
            "file_url": file_url,
            "message_id": message.message_id,
            "created_at": datetime.utcnow().isoformat()
        }
        
        supabase.table('files').insert(data).execute()
        logger.info(f"✅ تم حفظ الملف: {file_name} ({file_size} bytes)")
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة الملف: {str(e)}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج استلام الصور من المجموعة"""
    
    if update.effective_chat.id != TARGET_GROUP_ID:
        return
    
    try:
        message = update.effective_message
        if not message or not message.photo:
            return

        photo = message.photo[-1]  # أكبر حجم للصورة
        
        # استخراج معلومات الصورة
        file_id = photo.file_id
        file_size = photo.file_size or 0
        # تسمية الصورة بناءً على ID الرسالة لأن الصور في تليجرام ليس لها اسم أصلي
        file_name = f"photo_{message.message_id}.jpg"
        
        # الحصول على رابط الصورة
        file = await context.bot.get_file(file_id)
        file_url = file.file_path
        
        # حفظ البيانات في Supabase
        data = {
            "file_name": file_name,
            "file_size": file_size,
            "file_type": "image",
            "mime_type": "image/jpeg",
            "telegram_file_id": file_id,
            "file_url": file_url,
            "message_id": message.message_id,
            "created_at": datetime.utcnow().isoformat()
        }
        
        supabase.table('files').insert(data).execute()
        logger.info(f"✅ تم حفظ الصورة: {file_name} ({file_size} bytes)")
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة الصورة: {str(e)}")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج استلام الفيديوهات من المجموعة"""
    
    if update.effective_chat.id != TARGET_GROUP_ID:
        return
    
    try:
        message = update.effective_message
        if not message:
            return

        video = message.video
        if not video:
            return
        
        # استخراج معلومات الفيديو
        file_id = video.file_id
        file_name = video.file_name or f"video_{message.message_id}.mp4"
        file_size = video.file_size or 0
        mime_type = video.mime_type or "video/mp4"
        
        # الحصول على رابط الفيديو
        file = await context.bot.get_file(file_id)
        file_url = file.file_path
        
        # حفظ البيانات في Supabase
        data = {
            "file_name": file_name,
            "file_size": file_size,
            "file_type": "video",
            "mime_type": mime_type,
            "telegram_file_id": file_id,
            "file_url": file_url,
            "message_id": message.message_id,
            "created_at": datetime.utcnow().isoformat()
        }
        
        supabase.table('files').insert(data).execute()
        logger.info(f"✅ تم حفظ الفيديو: {file_name} ({file_size} bytes)")
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة الفيديو: {str(e)}")

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج استلام الملفات الصوتية من المجموعة"""
    
    if update.effective_chat.id != TARGET_GROUP_ID:
        return
    
    try:
        message = update.effective_message
        if not message:
            return

        audio = message.audio
        if not audio:
            return
        
        # استخراج معلومات الملف الصوتي
        file_id = audio.file_id
        file_name = audio.file_name or f"audio_{message.message_id}.mp3"
        file_size = audio.file_size or 0
        mime_type = audio.mime_type or "audio/mpeg"
        
        # الحصول على رابط الملف الصوتي
        file = await context.bot.get_file(file_id)
        file_url = file.file_path
        
        # حفظ البيانات في Supabase
        data = {
            "file_name": file_name,
            "file_size": file_size,
            "file_type": "audio",
            "mime_type": mime_type,
            "telegram_file_id": file_id,
            "file_url": file_url,
            "message_id": message.message_id,
            "created_at": datetime.utcnow().isoformat()
        }
        
        supabase.table('files').insert(data).execute()
        logger.info(f"✅ تم حفظ الملف الصوتي: {file_name} ({file_size} bytes)")
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة الملف الصوتي: {str(e)}")

def main():
    """نقطة البداية الرئيسية للبوت"""
    
    logger.info("🚀 بدء تشغيل بوت أرشفة ملفات تليجرام...")
    logger.info(f"📡 المجموعة المستهدفة: {TARGET_GROUP_ID}")
    
    # إنشاء التطبيق
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة معالجات الرسائل
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    
    logger.info("✅ البوت جاهز ويستمع للرسائل...")
    
    # تشغيل البوت
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
