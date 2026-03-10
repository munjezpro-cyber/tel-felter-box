from flask import Flask, render_template, request, redirect, url_for, flash, session
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

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = Config.SECRET_KEY

# --- نظام تسجيل تليجرام ---
active_users = {}
user_lock = threading.Lock()

def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

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
    
    return render_template('telegram_login.html')

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
    
    return render_template('verify_code.html', session_id=session_id)

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
    
    return render_template('verify_2fa.html', session_id=session_id)

@app.route('/dashboard')
def dashboard():
    if 'telegram_user' not in session:
        return redirect(url_for('telegram_login'))
    
    accounts = get_all_accounts()
    keywords = get_keywords()
    ai_enabled = get_setting('ai_enabled') == 'True' if get_setting('ai_enabled') else Config.AI_ENABLED
    radar_enabled = radar.is_running()
    return render_template('dashboard.html', 
                          accounts=accounts, 
                          keywords=keywords,
                          ai_enabled=ai_enabled,
                          radar_enabled=radar_enabled)

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
