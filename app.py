from flask import Flask, request, redirect, url_for, flash, session
from database import (
    init_db, add_account, get_all_accounts, delete_account, 
    update_account, get_keywords, save_keywords, get_setting, 
    set_setting, add_log, get_logs
)
from radar import radar
from config import Config
import asyncio
import os
import threading

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

active_users = {}
user_lock = threading.Lock()

def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

def get_html_page(page_type, session_id=None, keywords=None, accounts=None, ai_enabled=None, radar_enabled=None):
    """إرجاع HTML كـ string"""
    if page_type == 'login':
        return '''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تسجيل تليجرام</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <nav class="navbar navbar-dark bg-primary">
        <div class="container-fluid">
            <span class="navbar-brand mb-0 h1">🚀 رادار تليجرام الذكي</span>
        </div>
    </nav>
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-5">
                <div class="card">
                    <div class="card-body">
                        <h4 class="card-title text-center mb-4">🔐 تسجيل دخول تليجرام</h4>
                        {% for category, message in get_flashed_messages(with_categories=true) %}
                            <div class="alert alert-{{ category }}">{{ message }}</div>
                        {% endfor %}
                        <form action="{{ url_for('telegram_login') }}" method="POST">
                            <div class="mb-3">
                                <label class="form-label">API ID</label>
                                <input type="number" name="api_id" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">API HASH</label>
                                <input type="text" name="api_hash" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">رقم الهاتف</label>
                                <input type="text" name="phone" class="form-control" placeholder="+967XXXXXXXXX" required>
                            </div>
                            <button type="submit" class="btn btn-primary w-100">إرسال الكود</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>'''
    elif page_type == 'verify_code':
        return f'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>التحقق من الكود</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <nav class="navbar navbar-dark bg-primary">
        <div class="container-fluid">
            <span class="navbar-brand mb-0 h1">🚀 رادار تليجرام الذكي</span>
        </div>
    </nav>
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body">
                        <h4 class="card-title text-center mb-4">📱 أدخل الكود</h4>
                        <form action="{{ url_for('verify_code') }}" method="POST">
                            <input type="hidden" name="session_id" value="{session_id}">
                            <div class="mb-3">
                                <label class="form-label">الكود المرسل</label>
                                <input type="text" name="code" class="form-control" required>
                            </div>
                            <button type="submit" class="btn btn-primary w-100">تأكيد</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>'''
    elif page_type == 'verify_2fa':
        return f'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>التحقق بخطوتين</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <nav class="navbar navbar-dark bg-primary">
        <div class="container-fluid">
            <span class="navbar-brand mb-0 h1">🚀 رادار تليجرام الذكي</span>
        </div>
    </nav>
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body">
                        <h4 class="card-title text-center mb-4">🔑 التحقق بخطوتين</h4>
                        <form action="{{ url_for('verify_2fa') }}" method="POST">
                            <input type="hidden" name="session_id" value="{session_id}">
                            <div class="mb-3">
                                <label class="form-label">كلمة المرور</label>
                                <input type="password" name="password" class="form-control" required>
                            </div>
                            <button type="submit" class="btn btn-primary w-100">دخول</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>'''
    elif page_type == 'dashboard':
        accounts_html = ''
        for account in accounts:
            status = 'نشط' if account['enabled'] else 'معطل'
            status_class = 'active' if account['enabled'] else 'inactive'
            accounts_html += f'''
            <tr>
                <td>{account['phone']}</td>
                <td><span class="status-{status_class}">{status}</span></td>
                <td>
                    <a href="{{ url_for('toggle_account', phone=account['phone']) }}" class="btn btn-sm btn-info">
                        {{ 'تعطيل' if account['enabled'] else 'تفعيل' }}
                    </a>
                    <a href="{{ url_for('delete_account_api', phone=account['phone']) }}" class="btn btn-sm btn-danger">حذف</a>
                </td>
            </tr>
            '''
        
        return f'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لوحة التحكم</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .status-active {{ color: #28a745; }}
        .status-inactive {{ color: #dc3545; }}
    </style>
</head>
<body class="bg-light">
    <nav class="navbar navbar-dark bg-primary">
        <div class="container-fluid">
            <span class="navbar-brand mb-0 h1">🚀 رادار تليجرام الذكي</span>
            <a href="{{ url_for('logout') }}" class="btn btn-outline-light btn-sm">تسجيل خروج</a>
        </div>
    </nav>
    <div class="container mt-4">
        {% for category, message in get_flashed_messages(with_categories=true) %}
            <div class="alert alert-{{ category }} alert-dismissible fade show">
                {{ message }}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        {% endfor %}
        
        <div class="row">
            <div class="col-md-12 mb-4">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">حالة الرادار</h5>
                        <p class="card-text">
                            الحالة: <span class="status-{{ 'active' if radar_enabled else 'inactive' }}">
                                {{ 'يعمل' if radar_enabled else 'متوقف' }}
                            </span>
                        </p>
                        <form action="{{ url_for('toggle_radar') }}" method="POST">
                            <button type="submit" class="btn btn-{{ 'danger' if radar_enabled else 'success' }}">
                                {{ 'إيقاف الرادار' if radar_enabled else 'تشغيل الرادار' }}
                            </button>
                        </form>
                    </div>
                </div>
            </div>
            
            <div class="col-md-6 mb-4">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">إضافة حساب تليجرام</h5>
                        <form action="{{ url_for('add_account_api') }}" method="POST">
                            <div class="mb-3">
                                <label class="form-label">رقم الهاتف</label>
                                <input type="text" name="phone" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">API ID</label>
                                <input type="number" name="api_id" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">API HASH</label>
                                <input type="text" name="api_hash" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">مجموعة الإشعارات (اختياري)</label>
                                <input type="text" name="alert_group" class="form-control">
                            </div>
                            <button type="submit" class="btn btn-primary w-100">إضافة</button>
                        </form>
                    </div>
                </div>
            </div>
            
            <div class="col-md-6 mb-4">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">الحسابات المضافة ({{ accounts|length }})</h5>
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                    <th>رقم الهاتف</th>
                                    <th>الحالة</th>
                                    <th>إجراءات</th>
                                </tr>
                            </thead>
                            <tbody>
                                {{ accounts_html|safe }}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            
            <div class="col-md-12 mb-4">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">الكلمات المفتاحية</h5>
                        <form action="{{ url_for('save_keywords_api') }}" method="POST">
                            <textarea name="keywords" class="form-control" rows="10" required>{{ keywords|join('\n') }}</textarea>
                            <button type="submit" class="btn btn-primary mt-2">حفظ الكلمات</button>
                        </form>
                    </div>
                </div>
            </div>
            
            <div class="col-md-12 mb-4">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">إعدادات الذكاء الاصطناعي</h5>
                        <form action="{{ url_for('toggle_ai') }}" method="POST">
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" name="ai_enabled" {% if ai_enabled %}checked{% endif %}>
                                <label class="form-check-label">تفعيل تصنيف الذكاء الاصطناعي</label>
                            </div>
                            <button type="submit" class="btn btn-primary mt-2">حفظ الإعدادات</button>
                        </form>
                    </div>
                </div>
            </div>
            
            <div class="col-md-12 mb-4">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">سجل الأحداث</h5>
                        <textarea id="logs" class="form-control" rows="10" readonly></textarea>
                        <button onclick="updateLogs()" class="btn btn-primary mt-2">تحديث السجل</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        async function updateLogs() {
            const response = await fetch('/api/logs');
            const data = await response.json();
            document.getElementById('logs').value = data.logs.join('\n');
        }
        setInterval(updateLogs, 5000);
        updateLogs();
    </script>
</body>
</html>'''

@app.route('/')
def index():
    if 'telegram_user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('telegram_login'))

@app.route('/telegram/login', methods=['GET', 'POST'])
def telegram_login():
    if request.method == 'POST':
        api_id = request.form['api_id']
        api_hash = request.form['api_hash']
        phone = request.form['phone']
        
        session_id = phone.replace('+', '').replace(' ', '')
        
        with user_lock:
            active_users[session_id] = {
                'client': None,
                'phone': phone,
                'api_id': api_id,
                'api_hash': api_hash,
                'status': 'waiting_code'
            }
        
        try:
            from telethon import TelegramClient
            client = TelegramClient('session', int(api_id), api_hash)
            active_users[session_id]['client'] = client
            
            run_async(client.connect())
            run_async(client.send_code_request(phone))
            flash('تم إرسال الكود إلى تليجرام، أدخله في الصفحة التالية', 'success')
            return redirect(url_for('verify_code', session_id=session_id))
        except Exception as e:
            flash(f'خطأ: {str(e)}', 'danger')
            return redirect(url_for('telegram_login'))
    
    return get_html_page('login')

@app.route('/telegram/verify_code', methods=['GET', 'POST'])
def verify_code():
    session_id = request.args.get('session_id') or request.form.get('session_id')
    
    if request.method == 'POST':
        code = request.form['code']
        
        with user_lock:
            if session_id not in active_users:
                return redirect(url_for('telegram_login'))
            
            session_data = active_users[session_id]
            client = session_data['client']
            
            try:
                run_async(client.sign_in(phone=session_data['phone'], code=code))
                
                if client.is_user_authorized():
                    me = run_async(client.get_me())
                    user_id = me.id if me else None
                    
                    add_account(session_data['phone'], session_data['api_id'], session_data['api_hash'], None)
                    
                    session['telegram_user'] = session_data['phone']
                    session_data['status'] = 'logged_in'
                    session_data['user_id'] = user_id
                    flash('تم تسجيل الدخول بنجاح!', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    session_data['status'] = 'waiting_2fa'
                    flash('يوجد تحقق بخطوتين، أدخل كلمة المرور', 'warning')
                    return redirect(url_for('verify_2fa', session_id=session_id))
                    
            except Exception as e:
                flash(f'خطأ: {str(e)}', 'danger')
                return redirect(url_for('telegram_login'))
    
    return get_html_page('verify_code', session_id=session_id)

@app.route('/telegram/verify_2fa', methods=['GET', 'POST'])
def verify_2fa():
    session_id = request.args.get('session_id') or request.form.get('session_id')
    
    if request.method == 'POST':
        password = request.form['password']
        
        with user_lock:
            if session_id not in active_users:
                return redirect(url_for('telegram_login'))
            
            session_data = active_users[session_id]
            client = session_data['client']
            
            try:
                run_async(client.sign_in(password=password))
                
                                me = run_async(client.get_me())
                user_id = me.id if me else None
                
                add_account(session_data['phone'], session_data['api_id'], session_data['api_hash'], None)
                
                session['telegram_user'] = session_data['phone']
                session_data['status'] = 'logged_in'
                session_data['user_id'] = user_id
                flash('تم تسجيل الدخول بنجاح!', 'success')
                return redirect(url_for('dashboard'))
            except Exception as e:
                flash(f'كلمة المرور خاطئة: {str(e)}', 'danger')
                return redirect(url_for('verify_2fa', session_id=session_id))
    
    return get_html_page('verify_2fa', session_id=session_id)

@app.route('/dashboard')
def dashboard():
    if 'telegram_user' not in session:
        return redirect(url_for('telegram_login'))
    
    accounts = get_all_accounts()
    keywords = get_keywords()
    ai_enabled = get_setting('ai_enabled') == 'True' if get_setting('ai_enabled') else Config.AI_ENABLED
    radar_enabled = radar.is_running()
    return get_html_page('dashboard', keywords=keywords, accounts=accounts, ai_enabled=ai_enabled, radar_enabled=radar_enabled)

@app.route('/api/accounts/add', methods=['POST'])
def add_account_api():
    if 'telegram_user' not in session:
        return redirect(url_for('telegram_login'))
    
    phone = request.form['phone']
    api_id = request.form['api_id']
    api_hash = request.form['api_hash']
    alert_group = request.form.get('alert_group', '')
    
    if add_account(phone, api_id, api_hash, alert_group):
        flash('تم إضافة الحساب بنجاح', 'success')
    else:
        flash('فشل إضافة الحساب', 'danger')
    
    return redirect(url_for('dashboard'))

@app.route('/api/accounts/delete/<phone>')
def delete_account_api(phone):
    if 'telegram_user' not in session:
        return redirect(url_for('telegram_login'))
    
    delete_account(phone)
    flash('تم حذف الحساب', 'success')
    return redirect(url_for('dashboard'))

@app.route('/api/accounts/toggle/<phone>')
def toggle_account(phone):
    if 'telegram_user' not in session:
        return redirect(url_for('telegram_login'))
    
    accounts = get_all_accounts()
    for acc in accounts:
        if acc['phone'] == phone:
            update_account(phone, enabled=not acc['enabled'])
            break
    flash('تم تحديث حالة الحساب', 'success')
    return redirect(url_for('dashboard'))

@app.route('/api/keywords/save', methods=['POST'])
def save_keywords_api():
    if 'telegram_user' not in session:
        return redirect(url_for('telegram_login'))
    
    keywords_text = request.form['keywords']
    keywords = keywords_text.split('\n')
    save_keywords(keywords)
    flash('تم حفظ الكلمات', 'success')
    return redirect(url_for('dashboard'))

@app.route('/api/settings/ai', methods=['POST'])
def toggle_ai():
    if 'telegram_user' not in session:
        return redirect(url_for('telegram_login'))
    
    ai_enabled = request.form.get('ai_enabled') == 'on'
    set_setting('ai_enabled', 'True' if ai_enabled else 'False')
    Config.AI_ENABLED = ai_enabled
    flash('تم تحديث إعدادات الذكاء الاصطناعي', 'success')
    return redirect(url_for('dashboard'))

@app.route('/api/radar/toggle', methods=['POST'])
def toggle_radar():
    if 'telegram_user' not in session:
        return redirect(url_for('telegram_login'))
    
    if radar.is_running():
        asyncio.run(radar.stop_radar())
        set_setting('radar_enabled', 'False')
        flash('تم إيقاف الرادار', 'success')
    else:
        asyncio.run(radar.start_radar())
        set_setting('radar_enabled', 'True')
        flash('تم تشغيل الرادار', 'success')
    return redirect(url_for('dashboard'))

@app.route('/api/logs')
def get_logs_api():
    if 'telegram_user' not in session:
        return redirect(url_for('telegram_login'))
    
    logs = get_logs(100)
    return {'logs': [log['message'] for log in logs]}

@app.route('/logout')
def logout():
    session.pop('telegram_user', None)
    return redirect(url_for('telegram_login'))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8000)
