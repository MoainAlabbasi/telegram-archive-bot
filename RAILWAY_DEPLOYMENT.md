# 🚀 دليل النشر السريع على Railway

## الخطوات:

### 1️⃣ إعداد Supabase (مرة واحدة)
1. افتح [Supabase](https://supabase.co) → SQL Editor
2. انسخ محتوى `setup.sql` وشغّله
3. اذهب إلى Settings → API واحفظ:
   - Project URL
   - Anon Key

### 2️⃣ النشر على Railway
1. افتح [Railway](https://railway.app)
2. اضغط **New Project** → **Deploy from GitHub**
3. اختر المستودع: `MoainAlabbasi/telegram-archive-bot`
4. أضف المتغيرات البيئية:
   ```
   BOT_TOKEN=8526337520:AAEIWegHcbKfnIt3f9UtPCVMGrGrpma4DV8
   TARGET_GROUP_ID=-1002469448517
   SUPABASE_URL=https://gmtcbemfxirorrsznlcr.supabase.co
   SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdtdGNiZW1meGlyb3Jyc3pubGNyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQ0Njg0OTYsImV4cCI6MjA4MDA0NDQ5Nn0.oc0YeWFgWOx1AyaH3yfsyBWJ3wAQ0jlMHuF6CYPeokA
   PORT=8080
   ```
5. اضغط **Deploy**

### 3️⃣ التحقق
- **الموقع**: سيعطيك Railway رابط (مثل: https://your-app.railway.app)
- **البوت**: سيعمل تلقائياً في الخلفية (Worker)

## ⚠️ هام جداً:
- Railway سينشئ **خدمتين**:
  - `web`: الموقع (server.py)
  - `worker`: البوت (bot.py)
- تأكد من تشغيل **الخدمتين معاً**

## 🔗 الروابط:
- **المستودع**: https://github.com/MoainAlabbasi/telegram-archive-bot
- **Railway**: https://railway.app
- **Supabase**: https://supabase.co

✅ انتهى!
