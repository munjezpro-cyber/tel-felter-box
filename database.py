import psycopg2
from psycopg2.extras import RealDictCursor
from config import Config
import os

def get_db_connection():
    """الحصول على اتصال بقاعدة البيانات"""
    return psycopg2.connect(Config.DATABASE_URL)

def init_db():
    """تهيئة قاعدة البيانات"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # جدول الحسابات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            phone TEXT PRIMARY KEY,
            api_id INTEGER NOT NULL,
            api_hash TEXT NOT NULL,
            alert_group TEXT,
            enabled BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول الكلمات المفتاحية
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT UNIQUE NOT NULL
        )
    ''')
    
    # جدول الإعدادات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # جدول السجلات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # إضافة كلمات افتراضية
    default_keywords = [
        'طلب', 'مساعدة', 'ساعدوني', 'ساعدني', 'أبي أحد', 'أبي حد', 'أبي مساعدة',
        'محتاج', 'محتاجة', 'ضروري', 'مستعجل', 'أرجوكم', 'لو سمحتم', 'واجب', 'واجبات',
        'تكليف', 'تكاليف', 'حل', 'يحل', 'اسايمنت', 'assignment', 'homework',
        'بحث', 'بحوث', 'تقرير', 'تقارير', 'ريبورت', 'report', 'research',
        'مشروع', 'مشاريع', 'بروجكت', 'project', 'مشروع تخرج', 'مشاريع تخرج',
        'برزنتيشن', 'presentation', 'بوربوينت', 'powerpoint', 'عرض', 'عروض',
        'تصميم', 'تصاميم', 'فيديو', 'فيديوهات', 'مونتاج', 'مقطع', 'تصوير',
        'اختبار', 'اختبارات', 'كويز', 'كويزات', 'فاينل', 'ميد', 'امتحان',
        'شرح', 'يشرح', 'درس', 'دروس', 'ملخص', 'ملخصات', 'مذكرة', 'مذكرات',
        'رياضيات', 'فيزياء', 'كيمياء', 'أحياء', 'إنجليزي', 'عربي', 'تاريخ',
        'دكتور خصوصي', 'مدرس خصوصي', 'معلم خصوصي', 'مدرسة خصوصية',
        'تعرفون أحد', 'تعرفون حد', 'من يعرف', 'من تعرف', 'أحد يعرف', 'حد يعرف',
        'جامعة', 'كلية', 'دراسة', 'أكاديمي', 'تعليم', 'مدرسة', 'طالب', 'طالبة',
        'ترجمة', 'تلخيص', 'تدقيق', 'صياغة', 'كتابة', 'إعداد', 'تنفيذ',
        'مراجعة', 'ليالي الامتحان', 'أسئلة', 'إجابات', 'نماذج', 'تجميعات',
        'رسالة ماجستير', 'رسالة دكتوراه', 'أطروحة', 'بحث علمي', 'نشر',
        'برمجة', 'كود', 'برنامج', 'تطبيق', 'موقع', 'نظام', 'قاعدة بيانات',
        'رسم', 'أوتوكاد', 'سوليدوركس', 'ريفيت', 'ديزاين', 'تصميم معماري',
        'فوتوشوب', 'إليستريتور', 'ان ديزاين', 'جرافيك', 'graphic design',
        'أحد يساعد', 'أحد يحل', 'أحد يشرح', 'أحد يعمل', 'أحد يسوي', 'أحد يصمم',
        'أحد يبرمج', 'أحد يترجم', 'أحد يلخص', 'أحد يدقق', 'أحد يراجع'
    ]
    
    for keyword in default_keywords:
        try:
            cursor.execute('INSERT INTO keywords (keyword) VALUES (%s) ON CONFLICT (keyword) DO NOTHING', (keyword,))
        except:
            pass
    
    conn.commit()
    cursor.close()
    conn.close()

def add_account(phone, api_id, api_hash, alert_group=None):
    """إضافة حساب جديد"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO accounts (phone, api_id, api_hash, alert_group)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (phone) DO NOTHING
        ''', (phone, api_id, api_hash, alert_group))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def get_all_accounts():
    """الحصول على جميع الحسابات"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT * FROM accounts ORDER BY created_at DESC')
    accounts = cursor.fetchall()
    cursor.close()
    conn.close()
    return accounts

def delete_account(phone):
    """حذف حساب"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM accounts WHERE phone = %s', (phone,))
    conn.commit()
    cursor.close()
    conn.close()

def update_account(phone, alert_group=None, enabled=None):
    """تحديث حساب"""
    conn = get_db_connection()
    cursor = conn.cursor()
    if alert_group is not None:
        cursor.execute('UPDATE accounts SET alert_group = %s WHERE phone = %s', (alert_group, phone))
    if enabled is not None:
        cursor.execute('UPDATE accounts SET enabled = %s WHERE phone = %s', (enabled, phone))
    conn.commit()
    cursor.close()
    conn.close()

def get_keywords():
    """الحصول على جميع الكلمات"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT keyword FROM keywords ORDER BY id')
    keywords = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return keywords

def save_keywords(keywords):
    """حفظ الكلمات"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM keywords')
    for keyword in keywords:
        if keyword.strip():
            cursor.execute('INSERT INTO keywords (keyword) VALUES (%s)', (keyword.strip(),))
    conn.commit()
    cursor.close()
    conn.close()

def get_setting(key):
    """الحصول على إعداد"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = %s', (key,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result[0] if result else None

def set_setting(key, value):
    """حفظ إعداد"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO settings (key, value)
        VALUES (%s, %s)
        ON CONFLICT (key) DO UPDATE SET value = %s
    ''', (key, value, value))
    conn.commit()
    cursor.close()
    conn.close()

def add_log(message):
    """إضافة سجل"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO logs (message) VALUES (%s)', (message,))
    conn.commit()
    cursor.close()
    conn.close()

def get_logs(limit=100):
    """الحصول على آخر السجلات"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT * FROM logs ORDER BY created_at DESC LIMIT %s', (limit,))
    logs = cursor.fetchall()
    cursor.close()
    conn.close()
    return logs
