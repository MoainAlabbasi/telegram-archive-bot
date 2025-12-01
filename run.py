#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نقطة التشغيل الرئيسية للمشروع
تشغيل Flask في خيط خلفي وبوت Telegram في الخيط الرئيسي
"""

import os
import sys
import asyncio
import threading
import logging

# إضافة مسار المشروع إلى PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def run_flask_app():
    """
    تشغيل Flask في خيط خلفي (Daemon Thread)
    """
    try:
        from src.api.main import app
        
        # جلب المنفذ من متغيرات البيئة
        port = int(os.environ.get("PORT", 8080))
        host = os.environ.get("HOST", "0.0.0.0")
        
        logger.info(f"🌐 بدء تشغيل Flask على {host}:{port}")
        
        # تشغيل Flask بدون Reloader لمنع تضارب الإشارات
        app.run(
            host=host,
            port=port,
            debug=False,
            use_reloader=False,
            threaded=True
        )
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل Flask: {e}", exc_info=True)


async def run_telegram_bot():
    """
    تشغيل بوت Telegram بشكل غير متزامن (Async)
    """
    try:
        from src.bot.main import main as bot_main
        
        logger.info("🤖 بدء تشغيل بوت Telegram في الخيط الرئيسي...")
        
        # تشغيل البوت
        await bot_main()
        
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل بوت Telegram: {e}", exc_info=True)
        raise


def main():
    """
    نقطة الدخول الرئيسية
    - Flask يعمل في خيط خلفي (Daemon)
    - Telegram Bot يعمل في الخيط الرئيسي (Main Thread)
    """
    try:
        logger.info("=" * 60)
        logger.info("🚀 بدء تشغيل telegram-archive-bot")
        logger.info("=" * 60)
        
        # التحقق من متغيرات البيئة الضرورية
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            logger.error("❌ متغير البيئة TELEGRAM_BOT_TOKEN غير موجود!")
            sys.exit(1)
        
        # 1. تشغيل Flask في خيط خلفي (Daemon Thread)
        flask_thread = threading.Thread(
            target=run_flask_app,
            daemon=True,  # سيتوقف تلقائياً عند إيقاف البرنامج
            name="FlaskThread"
        )
        flask_thread.start()
        logger.info("✅ تم تشغيل Flask في خيط خلفي")
        
        # 2. تشغيل بوت Telegram في الخيط الرئيسي (Main Thread)
        # هذا ضروري لأن python-telegram-bot v20+ يتطلب Main Thread
        logger.info("✅ بدء تشغيل Telegram Bot في الخيط الرئيسي...")
        asyncio.run(run_telegram_bot())
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ تم إيقاف البرنامج بواسطة المستخدم (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ خطأ حرج في البرنامج: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
