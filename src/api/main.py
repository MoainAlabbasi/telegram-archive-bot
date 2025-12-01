#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask API للتحكم في البوت ومراقبة حالته
يستخدم مسارات مطلقة لمجلد templates
"""

import os
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, request

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== إعداد المسارات المطلقة ====================

# الحصول على المسار المطلق لهذا الملف
base_dir = os.path.dirname(os.path.abspath(__file__))

# بناء المسار المطلق لمجلد templates (خطوتين للخلف)
template_dir = os.path.join(base_dir, '../../templates')

# تحويل المسار إلى مسار مطلق نهائي
template_dir = os.path.abspath(template_dir)

logger.info(f"📁 مسار ملف API: {base_dir}")
logger.info(f"📁 مسار templates: {template_dir}")

# التحقق من وجود المجلد
if not os.path.exists(template_dir):
    logger.warning(f"⚠️ مجلد templates غير موجود: {template_dir}")
    logger.info("🔧 إنشاء مجلد templates...")
    os.makedirs(template_dir, exist_ok=True)

# ==================== إنشاء تطبيق Flask ====================

app = Flask(
    __name__,
    template_folder=template_dir  # استخدام المسار المطلق
)

# إعدادات Flask
app.config['JSON_AS_ASCII'] = False  # دعم اللغة العربية في JSON
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True


# ==================== المسارات (Routes) ====================

@app.route('/')
def index():
    """
    الصفحة الرئيسية
    """
    try:
        return render_template('index.html', 
                             app_name="Telegram Archive Bot",
                             version="1.0.0",
                             status="running")
    except Exception as e:
        logger.error(f"❌ خطأ في عرض الصفحة الرئيسية: {e}", exc_info=True)
        # في حالة عدم وجود template، نعرض صفحة HTML بسيطة
        return """
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Telegram Archive Bot</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                }
                .container {
                    text-align: center;
                    background: rgba(255, 255, 255, 0.1);
                    padding: 3rem;
                    border-radius: 20px;
                    backdrop-filter: blur(10px);
                    box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
                }
                h1 { font-size: 2.5rem; margin-bottom: 1rem; }
                .status { 
                    display: inline-block;
                    background: #10b981;
                    padding: 0.5rem 1.5rem;
                    border-radius: 25px;
                    margin-top: 1rem;
                }
                .emoji { font-size: 3rem; margin-bottom: 1rem; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="emoji">🤖</div>
                <h1>Telegram Archive Bot</h1>
                <p>البوت يعمل بشكل طبيعي</p>
                <div class="status">✅ Online</div>
            </div>
        </body>
        </html>
        """


@app.route('/health')
def health():
    """
    فحص صحة التطبيق (Health Check)
    """
    return jsonify({
        'status': 'healthy',
        'service': 'telegram-archive-bot',
        'timestamp': datetime.utcnow().isoformat(),
        'components': {
            'flask': 'operational',
            'telegram_bot': 'operational'
        }
    })


@app.route('/api/status')
def api_status():
    """
    حالة البوت (API)
    """
    return jsonify({
        'bot_status': 'running',
        'version': '1.0.0',
        'uptime': 'N/A',  # يمكن إضافة حساب الوقت الفعلي
        'environment': os.environ.get('RAILWAY_ENVIRONMENT', 'development'),
        'timestamp': datetime.utcnow().isoformat()
    })


@app.route('/api/stats')
def api_stats():
    """
    إحصائيات البوت
    """
    # هنا يمكن إضافة إحصائيات حقيقية من قاعدة البيانات
    return jsonify({
        'total_messages': 0,
        'total_users': 0,
        'total_chats': 0,
        'archives_created': 0,
        'last_updated': datetime.utcnow().isoformat()
    })


@app.route('/api/webhook', methods=['POST'])
def webhook():
    """
    نقطة نهاية Webhook (للاستخدام المستقبلي)
    """
    try:
        data = request.get_json()
        logger.info(f"📥 تم استلام webhook: {data}")
        
        # هنا يمكن إضافة معالجة Webhook
        
        return jsonify({'status': 'received'}), 200
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة webhook: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    """
    معالج خطأ 404
    """
    return jsonify({
        'error': 'Not Found',
        'message': 'المسار المطلوب غير موجود',
        'status': 404
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """
    معالج خطأ 500
    """
    logger.error(f"خطأ داخلي في الخادم: {error}", exc_info=True)
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'حدث خطأ داخلي في الخادم',
        'status': 500
    }), 500


# ==================== نقطة الدخول ====================

if __name__ == "__main__":
    """
    تشغيل Flask مباشرة (للاختبار المحلي فقط)
    في Production، يتم التشغيل عبر run.py
    """
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"⚠️ تشغيل مباشر - للاختبار المحلي فقط على المنفذ {port}")
    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )
