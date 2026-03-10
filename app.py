from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from database import (
    init_db, add_account, get_all_accounts, delete_account, 
    update_account, get_keywords, save_keywords, get_setting, 
    set_setting, add_log, get_logs
)
from radar import radar
from config import Config
import os

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return user_id

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        if email == Config.ADMIN_EMAIL and bcrypt.check_password_hash(password, Config.ADMIN_PASSWORD):
            session['user_id'] = email
            return redirect(url_for('dashboard'))
        else:
            flash('البريد الإلكتروني أو كلمة المرور غير صحيحة', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
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
@login_required
def add_account_api():
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
@login_required
def delete_account_api(phone):
    delete_account(phone)
    flash('تم حذف الحساب', 'success')
    return redirect(url_for('dashboard'))

@app.route('/api/accounts/toggle/<phone>')
@login_required
def toggle_account(phone):
    accounts = get_all_accounts()
    for acc in accounts:
        if acc['phone'] == phone:
            update_account(phone, enabled=not acc['enabled'])
            break
    flash('تم تحديث حالة الحساب', 'success')
    return redirect(url_for('dashboard'))

@app.route('/api/keywords/save', methods=['POST'])
@login_required
def save_keywords_api():
    keywords_text = request.form['keywords']
    keywords = keywords_text.split('\n')
    save_keywords(keywords)
    flash('تم حفظ الكلمات', 'success')
    return redirect(url_for('dashboard'))

@app.route('/api/settings/ai', methods=['POST'])
@login_required
def toggle_ai():
    ai_enabled = request.form.get('ai_enabled') == 'on'
    set_setting('ai_enabled', 'True' if ai_enabled else 'False')
    Config.AI_ENABLED = ai_enabled
    flash('تم تحديث إعدادات الذكاء الاصطناعي', 'success')
    return redirect(url_for('dashboard'))

@app.route('/api/radar/toggle', methods=['POST'])
@login_required
def toggle_radar():
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
@login_required
def get_logs_api():
    logs = get_logs(100)
    return {'logs': [log['message'] for log in logs]}

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8000)
