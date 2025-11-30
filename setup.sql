-- إنشاء جدول files لحفظ معلومات الملفات
CREATE TABLE IF NOT EXISTS files (
    id SERIAL PRIMARY KEY,
    file_name TEXT NOT NULL,
    file_size BIGINT DEFAULT 0,
    file_type TEXT NOT NULL,
    mime_type TEXT,
    telegram_file_id TEXT NOT NULL,
    file_url TEXT,
    message_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- إنشاء فهرس للبحث السريع
CREATE INDEX IF NOT EXISTS idx_files_created_at ON files(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_files_file_type ON files(file_type);
CREATE INDEX IF NOT EXISTS idx_files_file_name ON files(file_name);

-- تفعيل Row Level Security (RLS)
ALTER TABLE files ENABLE ROW LEVEL SECURITY;

-- السماح بالقراءة للجميع
CREATE POLICY "Allow public read access" ON files
    FOR SELECT
    USING (true);

-- السماح بالإدراج للجميع (يمكن تقييده لاحقاً)
CREATE POLICY "Allow public insert access" ON files
    FOR INSERT
    WITH CHECK (true);

-- السماح بالحذف للجميع (يمكن تقييده لاحقاً)
CREATE POLICY "Allow public delete access" ON files
    FOR DELETE
    USING (true);
