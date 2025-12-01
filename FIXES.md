# إصلاحات النشر على Railway

## التاريخ: 1 ديسمبر 2025

### المشاكل التي تم إصلاحها

#### 1. ✅ مشكلة Threading في البوت

**المشكلة:**
```
RuntimeWarning: coroutine 'Updater.start_polling' was never awaited
❌ خطأ في تشغيل البوت: set_wakeup_fd only works in main thread of the main interpreter
```

**السبب:**
- مكتبة `python-telegram-bot` الحديثة (v20+) تستخدم async/await
- `start_polling()` هي coroutine تحتاج await
- تشغيل البوت في thread منفصل يسبب مشاكل مع signal handlers

**الحل:**
- إنشاء event loop منفصل للبوت في الـ thread
- استخدام `asyncio.new_event_loop()` و `asyncio.set_event_loop()`
- تشغيل البوت بشكل صحيح باستخدام:
  ```python
  loop.run_until_complete(application.initialize())
  loop.run_until_complete(application.start())
  loop.run_until_complete(application.updater.start_polling())
  ```

**الملفات المعدلة:**
- `run.py` - تم إعادة كتابة دالة `run_bot_async()` بالكامل

---

#### 2. ✅ مشكلة 404 في الصفحة الرئيسية

**المشكلة:**
```
100.64.0.2 - - [01/Dec/2025 18:12:48] "GET / HTTP/1.1" 404 -
```

**السبب:**
- الكود يبحث عن ملف `index_v3.html` الذي لا يوجد
- الملف الموجود فعلياً هو `index.html` في مجلد `templates/`
- استخدام `send_from_directory('.', 'index_v3.html')` غير صحيح

**الحل:**
- تغيير المسار إلى: `send_from_directory(app.template_folder, 'index.html')`
- استخدام `app.template_folder` للإشارة إلى مجلد templates بشكل صحيح

**الملفات المعدلة:**
- `src/api/main.py` - السطر 284

---

#### 3. ✅ تحذير خادم التطوير

**المشكلة:**
```
WARNING: This is a development server. Do not use it in a production deployment.
```

**السبب:**
- استخدام Flask development server (`app.run()`) في الإنتاج
- هذا الخادم غير مناسب للإنتاج (أداء ضعيف، غير آمن)

**الحل:**
- إضافة `gunicorn` إلى `requirements.txt`
- تعديل `run.py` لاستخدام Gunicorn تلقائياً إذا كان متاحاً
- إعدادات Gunicorn:
  - 2 workers
  - timeout 120 ثانية
  - worker_class: sync
  - تفعيل access logs و error logs

**الملفات المعدلة:**
- `requirements.txt` - إضافة gunicorn
- `run.py` - إضافة دعم Gunicorn مع fallback إلى Flask

---

## التغييرات التفصيلية

### 1. `run.py`
- إعادة كتابة `run_bot_async()` لدعم async بشكل صحيح
- إضافة `run_server()` مع دعم Gunicorn
- تحسين معالجة الأخطاء وإضافة traceback

### 2. `src/api/main.py`
- إصلاح route الصفحة الرئيسية `/`
- تغيير من `index_v3.html` إلى `index.html`
- استخدام `app.template_folder` بدلاً من مسار نسبي

### 3. `requirements.txt`
- إضافة `gunicorn` للإنتاج

### 4. `Procfile`
- لم يتغير (يبقى `web: python run.py`)

---

## التوصيات للنشر

### خيار 1: النشر الحالي (موصى به)
استخدم الكود الحالي مع `Procfile` الموجود:
```
web: python run.py
```

هذا سيشغل البوت والخادم معاً في عملية واحدة.

### خيار 2: فصل البوت والخادم (للمشاريع الكبيرة)
إذا أردت فصل البوت والخادم في خدمتين منفصلتين على Railway:

**Procfile:**
```
web: gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 src.api.main:app
worker: python -m src.bot.main
```

ثم في Railway:
1. أنشئ خدمتين منفصلتين
2. الأولى تستخدم `web` process
3. الثانية تستخدم `worker` process

---

## اختبار الإصلاحات

### محلياً:
```bash
# تثبيت المتطلبات
pip install -r requirements.txt

# تشغيل المشروع
python run.py
```

### على Railway:
1. ادفع التغييرات إلى GitHub
2. Railway ستكتشف التغييرات وتعيد النشر تلقائياً
3. راقب السجلات للتأكد من عدم وجود أخطاء

---

## الحالة بعد الإصلاحات

✅ البوت يعمل بشكل صحيح مع async/await  
✅ الصفحة الرئيسية تعمل (لا مزيد من 404)  
✅ استخدام Gunicorn في الإنتاج  
✅ معالجة أفضل للأخطاء  
✅ سجلات أوضح  

---

## ملاحظات إضافية

### متغيرات البيئة المطلوبة
تأكد من إضافة هذه المتغيرات في Railway:
```
BOT_TOKEN=your_bot_token
TARGET_GROUP_ID=your_group_id
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SECRET_KEY=your_secret_key (اختياري)
```

### المنفذ (Port)
- Railway توفر متغير `PORT` تلقائياً
- الكود يقرأ من `config.PORT` الذي يستخدم `os.getenv('PORT', 8080)`

---

**تم بواسطة:** Manus AI  
**التاريخ:** 1 ديسمبر 2025
