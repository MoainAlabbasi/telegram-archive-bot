#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram File Archive Bot v3.0
يستمع للمجموعة ويحفظ روابط الملفات في Supabase
مع دعم حفظ الوصف وتتبع الرافع والتزامن مع قاعدة البيانات
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from telegram import Update, PhotoSize, Document, Video, Audio, Message
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from supabase import create_client, Client

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# بيانات الاتصال من المتغيرات البيئية
BOT_TOKEN = os.getenv('BOT_TOKEN')
TARGET_GROUP_ID_STR = os.getenv('TARGET_GROUP_ID')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# التحقق من وجود جميع المتغيرات المطلوبة
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

# إنشاء عميل Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_file_type_from_mime(mime_type: str) -> str:
    """
    تحديد نوع الملف من MIME type
    
    Args:
        mime_type: نوع MIME للملف
        
    Returns:
        نوع الملف (image, video, audio, document)
    """
    if mime_type.startswith("image/"):
        return "image"
    elif mime_type.startswith("video/"):
        return "video"
    elif mime_type.startswith("audio/"):
        return "audio"
    return "document"

def create_file_data(
    file_name: str,
    file_size: int,
    file_type: str,
    mime_type: str,
    file_id: str,
    file_url: str,
    message_id: int,
    caption: Optional[str] = None,
    uploaded_by: Optional[int] = None
) -> Dict[str, Any]:
    """
    إنشاء بيانات الملف للحفظ في قاعدة البيانات
    
    Args:
        file_name: اسم الملف
        file_size: حجم الملف بالبايت
        file_type: نوع الملف
        mime_type: MIME type
        file_id: معرف الملف في تليجرام
        file_url: رابط الملف
        message_id: معرف الرسالة
        caption: الوصف المرافق للملف
        uploaded_by: معرف المستخدم الذي قام بالرفع
        
    Returns:
        قاموس يحتوي على بيانات الملف
    """
    return {
        "file_name": file_name,
        "file_size": file_size,
        "file_type": file_type,
        "mime_type": mime_type,
        "telegram_file_id": file_id,
        "file_url": file_url,
        "message_id": message_id,
        "caption": caption,
        "uploaded_by": uploaded_by,
        "created_at": datetime.utcnow().isoformat()
    }

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    معالج موحد لجميع أنواع الملفات (مستندات، صور، فيديوهات، صوتيات)
    يدعم الرسائل المحولة (Forwarded Messages)
    يحفظ الوصف (Caption) ويتتبع الرافع
    
    Args:
        update: كائن التحديث من تليجرام
        context: سياق التطبيق
    """
    
    # التحقق من أن الرسالة من المجموعة المستهدفة
    if update.effective_chat.id != TARGET_GROUP_ID:
        return
    
    try:
        # استخدام effective_message لدعم الرسائل المحولة
        message = update.effective_message
        if not message:
            return

        # متغيرات لتخزين معلومات الملف
        file_obj: Optional[Any] = None
        file_type: Optional[str] = None
        file_name: Optional[str] = None
        mime_type: Optional[str] = None
        caption: Optional[str] = message.caption  # حفظ الوصف
        
        # تحديد نوع الملف واستخراج معلوماته
        if message.document:
            file_obj = message.document
            mime_type = file_obj.mime_type or "application/octet-stream"
            file_type = get_file_type_from_mime(mime_type)
            file_name = file_obj.file_name or "unknown_file"
            
        elif message.photo:
            file_obj = message.photo[-1]  # أكبر حجم للصورة
            file_type = "image"
            mime_type = "image/jpeg"
            file_name = f"photo_{message.message_id}.jpg"
            
        elif message.video:
            file_obj = message.video
            file_type = "video"
            mime_type = file_obj.mime_type or "video/mp4"
            file_name = file_obj.file_name or f"video_{message.message_id}.mp4"
            
        elif message.audio:
            file_obj = message.audio
            file_type = "audio"
            mime_type = file_obj.mime_type or "audio/mpeg"
            file_name = file_obj.file_name or f"audio_{message.message_id}.mp3"
        
        else:
            # لا يوجد ملف في الرسالة
            return
        
        # استخراج معلومات الملف
        file_id = file_obj.file_id
        file_size = getattr(file_obj, 'file_size', 0) or 0
        
        # الحصول على رابط الملف من تليجرام
        file = await context.bot.get_file(file_id)
        file_url = file.file_path
        
        # إنشاء بيانات الملف
        data = create_file_data(
            file_name=file_name,
            file_size=file_size,
            file_type=file_type,
            mime_type=mime_type,
            file_id=file_id,
            file_url=file_url,
            message_id=message.message_id,
            caption=caption,
            uploaded_by=None  # سيتم تعيينه من الموقع عند الرفع
        )
        
        # حفظ البيانات في Supabase
        supabase.table('files').insert(data).execute()
        
        # تسجيل نجاح العملية
        caption_info = f" | الوصف: {caption[:30]}..." if caption else ""
        logger.info(f"✅ تم حفظ {file_type}: {file_name} ({file_size:,} bytes){caption_info}")
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة الملف: {str(e)}")

async def handle_deleted_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    معالج لحذف الملفات المحذوفة من تليجرام
    يتم تفعيله عند حذف رسالة من المجموعة
    
    Args:
        update: كائن التحديث من تليجرام
        context: سياق التطبيق
    """
    try:
        # التحقق من أن الحذف من المجموعة المستهدفة
        if update.effective_chat.id != TARGET_GROUP_ID:
            return
        
        # الحصول على معرف الرسالة المحذوفة
        if hasattr(update, 'message') and update.message:
            message_id = update.message.message_id
            
            # حذف الملف من قاعدة البيانات
            result = supabase.table('files').delete().eq('message_id', message_id).execute()
            
            if result.data:
                logger.info(f"🗑️ تم حذف الملف المرتبط بالرسالة: {message_id}")
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة الحذف: {str(e)}")

def main() -> None:
    """نقطة البداية الرئيسية للبوت"""
    
    logger.info("=" * 60)
    logger.info("🚀 بدء تشغيل بوت أرشفة ملفات تليجرام v3.0...")
    logger.info(f"📡 المجموعة المستهدفة: {TARGET_GROUP_ID}")
    logger.info(f"🔗 Supabase URL: {SUPABASE_URL}")
    logger.info("=" * 60)
    
    # إنشاء التطبيق
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة معالج موحد لجميع أنواع الملفات
    application.add_handler(MessageHandler(
        filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO,
        handle_file
    ))
    
    # إضافة معالج للرسائل المحذوفة
    application.add_handler(MessageHandler(
        filters.StatusUpdate.DELETED_MESSAGES,
        handle_deleted_message
    ))
    
    logger.info("✅ البوت جاهز ويستمع للرسائل...")
    logger.info("📝 أنواع الملفات المدعومة: مستندات، صور، فيديوهات، صوتيات")
    logger.info("🔄 دعم الرسائل المحولة (Forwarded): مفعّل")
    logger.info("💾 حفظ الوصف (Caption): مفعّل")
    logger.info("🔄 تزامن الحذف: مفعّل")
    logger.info("=" * 60)
    
    # تشغيل البوت
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
