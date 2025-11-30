-- ========================================
-- Telegram Archive Bot v3.0
-- Database Schema with Authentication & RBAC
-- ========================================

-- 1. جدول المستخدمين (Users)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) UNIQUE NOT NULL,  -- الرقم التعريفي
    full_name VARCHAR(255) NOT NULL,      -- الاسم الثلاثي
    email VARCHAR(255) UNIQUE,            -- البريد الإلكتروني (يضاف لاحقاً)
    password_hash VARCHAR(255),           -- كلمة المرور المشفرة
    is_active BOOLEAN DEFAULT FALSE,      -- حالة التفعيل
    is_admin BOOLEAN DEFAULT FALSE,       -- هل هو أدمن
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    activated_at TIMESTAMP WITH TIME ZONE,
    last_login TIMESTAMP WITH TIME ZONE
);

-- 2. جدول رموز التحقق (OTP Codes)
CREATE TABLE IF NOT EXISTS otp_codes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    code VARCHAR(6) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. جدول الصلاحيات (Roles)
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,    -- اسم الصلاحية
    description TEXT,                      -- وصف الصلاحية
    permissions JSONB DEFAULT '{}',        -- الصلاحيات بصيغة JSON
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. جدول ربط المستخدمين بالصلاحيات (User Roles)
CREATE TABLE IF NOT EXISTS user_roles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, role_id)
);

-- 5. تحديث جدول الملفات (Files)
DROP TABLE IF EXISTS files CASCADE;
CREATE TABLE files (
    id SERIAL PRIMARY KEY,
    file_name TEXT NOT NULL,
    file_size BIGINT DEFAULT 0,
    file_type TEXT NOT NULL,
    mime_type TEXT,
    telegram_file_id TEXT NOT NULL,
    file_url TEXT,
    message_id INTEGER,
    caption TEXT,                          -- الوصف المرافق للملف
    uploaded_by INTEGER REFERENCES users(id) ON DELETE SET NULL,  -- من قام بالرفع
    folder_id INTEGER,                     -- للمجلدات المستقبلية
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. جدول الجلسات (Sessions)
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. جدول روابط المشاركة (Share Links)
CREATE TABLE IF NOT EXISTS share_links (
    id SERIAL PRIMARY KEY,
    file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    token VARCHAR(64) UNIQUE NOT NULL,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    access_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ========================================
-- الفهارس (Indexes)
-- ========================================

CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_files_created_at ON files(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_files_file_type ON files(file_type);
CREATE INDEX IF NOT EXISTS idx_files_uploaded_by ON files(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_share_links_token ON share_links(token);
CREATE INDEX IF NOT EXISTS idx_otp_codes_email ON otp_codes(email);

-- ========================================
-- البيانات الافتراضية (Default Data)
-- ========================================

-- إنشاء حساب الأدمن الافتراضي
-- كلمة المرور: DefaultPassword (مشفرة بـ bcrypt)
INSERT INTO users (user_id, full_name, email, password_hash, is_active, is_admin, activated_at)
VALUES (
    'ADMIN001',
    'Super Admin',
    'Moain.learn@gmail.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIxnT7Q7EG',  -- DefaultPassword
    TRUE,
    TRUE,
    NOW()
) ON CONFLICT (user_id) DO NOTHING;

-- إنشاء صلاحيات افتراضية
INSERT INTO roles (name, description, permissions) VALUES
    ('admin', 'مدير النظام - صلاحيات كاملة', '{"upload": true, "delete": true, "edit": true, "manage_users": true, "view_all": true}'),
    ('editor', 'محرر - يمكنه الرفع والتعديل والحذف', '{"upload": true, "delete": true, "edit": true, "manage_users": false, "view_all": true}'),
    ('uploader', 'رافع - يمكنه الرفع والتعديل فقط', '{"upload": true, "delete": false, "edit": true, "manage_users": false, "view_all": false}'),
    ('viewer', 'مشاهد - يمكنه المشاهدة فقط', '{"upload": false, "delete": false, "edit": false, "manage_users": false, "view_all": true}')
ON CONFLICT (name) DO NOTHING;

-- ربط الأدمن بصلاحية admin
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id
FROM users u, roles r
WHERE u.user_id = 'ADMIN001' AND r.name = 'admin'
ON CONFLICT (user_id, role_id) DO NOTHING;

-- ========================================
-- Row Level Security (RLS)
-- ========================================

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE files ENABLE ROW LEVEL SECURITY;
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE share_links ENABLE ROW LEVEL SECURITY;

-- سياسات المستخدمين
CREATE POLICY "Users can view their own data" ON users
    FOR SELECT
    USING (auth.uid()::text = id::text OR is_admin = true);

-- سياسات الملفات
CREATE POLICY "Users can view files based on permissions" ON files
    FOR SELECT
    USING (true);  -- سيتم التحكم من خلال الصلاحيات في الكود

CREATE POLICY "Users can insert files if they have upload permission" ON files
    FOR INSERT
    WITH CHECK (true);  -- سيتم التحكم من خلال الصلاحيات في الكود

CREATE POLICY "Users can delete their own files or if they have delete permission" ON files
    FOR DELETE
    USING (true);  -- سيتم التحكم من خلال الصلاحيات في الكود

-- سياسات روابط المشاركة
CREATE POLICY "Anyone can access share links" ON share_links
    FOR SELECT
    USING (expires_at > NOW());

-- ========================================
-- Functions & Triggers
-- ========================================

-- دالة لتنظيف الجلسات المنتهية
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS void AS $$
BEGIN
    DELETE FROM sessions WHERE expires_at < NOW();
    DELETE FROM otp_codes WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- دالة للتحقق من صلاحيات المستخدم
CREATE OR REPLACE FUNCTION check_user_permission(
    p_user_id INTEGER,
    p_permission TEXT
)
RETURNS BOOLEAN AS $$
DECLARE
    has_permission BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM user_roles ur
        JOIN roles r ON ur.role_id = r.id
        WHERE ur.user_id = p_user_id
        AND r.permissions->p_permission = 'true'::jsonb
    ) INTO has_permission;
    
    RETURN has_permission;
END;
$$ LANGUAGE plpgsql;

-- ========================================
-- Notes
-- ========================================
-- 1. كلمة المرور الافتراضية للأدمن: DefaultPassword
-- 2. يجب تغيير كلمة المرور بعد أول تسجيل دخول
-- 3. نظام الصلاحيات يعتمد على JSONB للمرونة
-- 4. يمكن إضافة صلاحيات مخصصة حسب الحاجة
