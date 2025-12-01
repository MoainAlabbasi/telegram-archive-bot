#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Archive Bot v3.0
نقطة البدء الرئيسية للمشروع
"""

import sys
import os
import logging
import asyncio
from threading import Thread

# إضافة مجلد src إلى المسار
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def run_bot_async():
    """تشغيل البوت في event loop منفصل"""
    try:
        from src.bot.main import create_bot_application
        
        logger.info("🤖 بدء تشغيل البوت...")
        
        # إنشاء event loop جديد للـ thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # إنشاء وتشغيل التطبيق
        application = create_bot_application()
        
        # تشغيل البوت
        loop.run_until_complete(application.initialize())
        loop.run_until_complete(application.start())
        loop.run_until_complete(application.updater.start_polling())
        
        logger.info("✅ البوت يعمل الآن")
        
        # الإبقاء على البوت يعمل
        loop.run_forever()
        
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل البوت: {e}")
        import traceback
        traceback.print_exc()


def run_server():
    """تشغيل الخادم"""
    try:
        from src.api.main import app
        from src.core.config import config
        
        logger.info(f"🌐 بدء تشغيل الخادم على المنفذ {config.PORT}...")
        
        # استخدام Gunicorn في الإنتاج إذا كان متاحاً
        try:
            import gunicorn.app.base
            
            class StandaloneApplication(gunicorn.app.base.BaseApplication):
                def __init__(self, app, options=None):
                    self.options = options or {}
                    self.application = app
                    super().__init__()

                def load_config(self):
                    for key, value in self.options.items():
                        if key in self.cfg.settings and value is not None:
                            self.cfg.set(key.lower(), value)

                def load(self):
                    return self.application

            options = {
                'bind': f'{config.HOST}:{config.PORT}',
                'workers': 2,
                'worker_class': 'sync',
                'timeout': 120,
                'accesslog': '-',
                'errorlog': '-',
                'loglevel': 'info',
            }
            
            logger.info("🚀 استخدام Gunicorn للإنتاج")
            StandaloneApplication(app, options).run()
            
        except ImportError:
            logger.warning("⚠️ Gunicorn غير متاح، استخدام Flask development server")
            app.run(
                host=config.HOST,
                port=config.PORT,
                debug=False,
                threaded=True
            )
            
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل الخادم: {e}")
        import traceback
        traceback.print_exc()


def main():
    """نقطة البدء الرئيسية"""
    logger.info("=" * 60)
    logger.info("🚀 Telegram Archive Bot v3.0")
    logger.info("=" * 60)
    
    # تشغيل البوت في thread منفصل
    bot_thread = Thread(target=run_bot_async, daemon=True)
    bot_thread.start()
    
    # تشغيل الخادم في الـ thread الرئيسي
    run_server()


if __name__ == '__main__':
    main()
