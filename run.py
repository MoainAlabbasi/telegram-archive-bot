#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Archive Bot v3.0
نقطة البدء الرئيسية للمشروع
"""

import sys
import os
import logging
import threading

# إضافة مجلد src إلى المسار
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def run_bot():
    """تشغيل البوت"""
    try:
        from src.bot.main import run_bot as start_bot
        logger.info("🤖 بدء تشغيل البوت...")
        start_bot()
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل البوت: {e}")


def run_server():
    """تشغيل الخادم"""
    try:
        from src.api.main import app
        from src.core.config import config
        
        logger.info(f"🌐 بدء تشغيل الخادم على المنفذ {config.PORT}...")
        app.run(
            host=config.HOST,
            port=config.PORT,
            debug=False,
            threaded=True
        )
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل الخادم: {e}")


def main():
    """نقطة البدء الرئيسية"""
    logger.info("=" * 60)
    logger.info("🚀 Telegram Archive Bot v3.0")
    logger.info("=" * 60)
    
    # تشغيل البوت في thread منفصل
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # تشغيل الخادم في الـ thread الرئيسي
    run_server()


if __name__ == '__main__':
    main()
