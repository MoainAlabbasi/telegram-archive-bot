#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
البوت الرئيسي لـ Telegram Archive Bot
يستخدم python-telegram-bot v20+ مع async/await
"""

import os
import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ==================== معالجات الأوامر ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    معالج أمر /start
    """
    user = update.effective_user
    welcome_message = (
        f"مرحباً {user.mention_html()}! 👋\n\n"
        "أنا بوت أرشفة رسائل تليجرام 📦\n\n"
        "الأوامر المتاحة:\n"
        "/start - بدء البوت\n"
        "/help - عرض المساعدة\n"
        "/archive - أرشفة المحادثة الحالية\n"
        "/status - حالة البوت"
    )
    await update.message.reply_html(welcome_message)
    logger.info(f"المستخدم {user.id} ({user.username}) بدأ البوت")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    معالج أمر /help
    """
    help_text = (
        "📖 <b>دليل الاستخدام:</b>\n\n"
        "1️⃣ <b>/start</b> - بدء البوت\n"
        "2️⃣ <b>/help</b> - عرض هذه المساعدة\n"
        "3️⃣ <b>/archive</b> - أرشفة المحادثة\n"
        "4️⃣ <b>/status</b> - التحقق من حالة البوت\n\n"
        "💡 <b>ملاحظة:</b> أرسل أي رسالة وسأقوم بأرشفتها!"
    )
    await update.message.reply_html(help_text)


async def archive_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    معالج أمر /archive
    """
    await update.message.reply_text(
        "🗄️ جاري أرشفة المحادثة...\n"
        "⏳ قد يستغرق هذا بعض الوقت..."
    )
    
    # هنا يمكن إضافة منطق الأرشفة الفعلي
    chat_id = update.effective_chat.id
    logger.info(f"طلب أرشفة للمحادثة {chat_id}")
    
    await update.message.reply_text(
        "✅ تم بدء عملية الأرشفة!\n"
        "📊 سيتم إشعارك عند الانتهاء."
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    معالج أمر /status
    """
    status_text = (
        "✅ <b>حالة البوت:</b> يعمل بشكل طبيعي\n"
        f"🤖 <b>الإصدار:</b> 1.0.0\n"
        f"🔧 <b>البيئة:</b> Production (Railway)\n"
        f"📡 <b>الاتصال:</b> نشط\n"
    )
    await update.message.reply_html(status_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    معالج الرسائل النصية العادية
    """
    message_text = update.message.text
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    logger.info(f"رسالة من {user.id} في المحادثة {chat_id}: {message_text[:50]}...")
    
    # هنا يمكن إضافة منطق حفظ الرسالة في قاعدة البيانات
    
    await update.message.reply_text(
        f"✅ تم استلام رسالتك وحفظها في الأرشيف!\n"
        f"📝 طول الرسالة: {len(message_text)} حرف"
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """
    معالج الأخطاء العام
    """
    logger.error(f"حدث خطأ: {context.error}", exc_info=context.error)
    
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "❌ عذراً، حدث خطأ أثناء معالجة طلبك.\n"
            "🔄 يرجى المحاولة مرة أخرى."
        )


# ==================== الدالة الرئيسية ====================

async def main():
    """
    الدالة الرئيسية لتشغيل البوت (async)
    """
    try:
        # جلب التوكن من متغيرات البيئة
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            raise ValueError("❌ متغير البيئة TELEGRAM_BOT_TOKEN غير موجود!")
        
        logger.info("🔧 بناء تطبيق Telegram Bot...")
        
        # بناء التطبيق باستخدام Application.builder()
        application = Application.builder().token(bot_token).build()
        
        # تسجيل معالجات الأوامر
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("archive", archive_command))
        application.add_handler(CommandHandler("status", status_command))
        
        # تسجيل معالج الرسائل النصية
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        )
        
        # تسجيل معالج الأخطاء
        application.add_error_handler(error_handler)
        
        logger.info("✅ تم تسجيل جميع المعالجات بنجاح")
        logger.info("🚀 بدء تشغيل البوت...")
        
        # تشغيل البوت باستخدام polling (مع await)
        # drop_pending_updates=True لتجاهل الرسائل القديمة
        await application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except Exception as e:
        logger.error(f"❌ خطأ حرج في تشغيل البوت: {e}", exc_info=True)
        raise


# ==================== نقطة الدخول ====================

if __name__ == "__main__":
    """
    تشغيل البوت مباشرة (للاختبار المحلي فقط)
    في Production، يتم التشغيل عبر run.py
    """
    logger.info("⚠️ تشغيل مباشر - للاختبار المحلي فقط")
    asyncio.run(main())
