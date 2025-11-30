#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram File Archive Bot v3.0
نقطة بدء البوت الرئيسية
"""

import logging
from telegram.ext import Application, MessageHandler, filters

from supabase import create_client
from ..core.config import config
from .handlers import FileHandler, DeletionHandler

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def create_bot_application() -> Application:
    """إنشاء وإعداد تطبيق البوت"""
    
    # التحقق من الإعدادات
    try:
        config.validate()
    except ValueError as e:
        logger.error(str(e))
        raise
    
    # إنشاء عميل Supabase
    supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    
    # إنشاء المعالجات
    file_handler = FileHandler(supabase, config.TARGET_GROUP_ID)
    deletion_handler = DeletionHandler(supabase, config.TARGET_GROUP_ID)
    
    # إنشاء التطبيق
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # تسجيل معالجات الرسائل
    application.add_handler(
        MessageHandler(
            filters.Document.ALL | filters.PHOTO | filters.VIDEO | 
            filters.AUDIO | filters.VOICE,
            file_handler.handle_file
        )
    )
    
    # معالج الرسائل المحذوفة (إذا كان مدعوماً)
    application.add_handler(
        MessageHandler(
            filters.StatusUpdate.DELETED_MESSAGES,
            deletion_handler.handle_deletion
        )
    )
    
    logger.info("✅ تم إعداد البوت بنجاح")
    return application


def run_bot():
    """تشغيل البوت"""
    logger.info("🚀 بدء تشغيل البوت...")
    
    try:
        application = create_bot_application()
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل البوت: {e}")
        raise


if __name__ == '__main__':
    run_bot()
