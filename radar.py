from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.types import User, Chat, Channel
from database import get_all_accounts, get_keywords, add_log, get_setting
from ai_classifier import classify_message
from config import Config
import asyncio
import os
import threading

class Radar:
    def __init__(self):
        self.clients = {}
        self.running = False
        self.lock = threading.Lock()
    
    async def start_client(self, phone, api_id, api_hash, alert_group):
        """بدء عميل تليجرام"""
        try:
            client = TelegramClient(f'sessions/{phone}', int(api_id), api_hash)
            await client.connect()
            
            if not await client.is_user_authorized():
                add_log(f"❌ حساب {phone} غير مفعل - يحتاج تسجيل دخول")
                return False
            
            # إضافة مستمع للرسائل
            @client.on(events.NewMessage(chats=[alert_group]))
            async def handler(event):
                await self.handle_message(event, phone, alert_group)
            
            self.clients[phone] = client
            add_log(f"✅ تم تشغيل حساب {phone}")
            return True
        except Exception as e:
            add_log(f"❌ خطأ في حساب {phone}: {str(e)}")
            return False
    
    async def handle_message(self, event, phone, alert_group):
        """معالجة الرسالة"""
        message = event.message
        sender = await event.get_sender()
        
        # تجاهل الرسائل الخاصة
        if not isinstance(sender, (User, Chat, Channel)):
            return
        
        # تجاهل رسائل البوتات
        if sender.bot:
            return
        
        # تجاهل رسائل الحساب نفسه
        if sender.id == await self.clients[phone].get_me():
            return
        
        text = message.text
        if not text:
            return
        
        # البحث عن الكلمات المفتاحية
        keywords = get_keywords()
        found_keyword = None
        for keyword in keywords:
            if keyword.lower() in text.lower():
                found_keyword = keyword
                break
        
        if not found_keyword:
            return
        
        add_log(f"🔍 رصد كلمة '{found_keyword}' في مجموعة {alert_group}")
        
        # تصنيف الرسالة
        if Config.AI_ENABLED:
            result = await classify_message(text)
            add_log(f"🤖 تصنيف: {result['type']} (ثقة: {result['confidence']}%)")
            
            if result['type'] == 'marketer' and result['confidence'] > 60:
                add_log(f"🚫 تم تجاهل معلن (ثقة: {result['confidence']}%)")
                return
        else:
            add_log("🤖 AI غير مفعل - إرسال الرسالة")
        
        # إرسال الإشعار
        await self.send_alert(event, sender, alert_group, text, found_keyword)
    
    async def send_alert(self, event, sender, alert_group, text, keyword):
        """إرسال الإشعار للمجموعة"""
        try:
            # محاولة إعادة التوجيه
            try:
                await event.forward(alert_group)
                add_log(f"✅ تم إعادة توجيه الرسالة بنجاح")
            except:
                # إرسال نسخة
                footer = f"""
🚨 **رادار ذكي - طلب مساعدة**
━━━━━━━━━━━━━━━━━━━━
📝 **النص الأصلي**: {text}
👤 **المرسل**: {sender.first_name} {sender.last_name or ''}
🏢 **المجموعة**: {alert_group}
━━━━━━━━━━━━━━━━━━━━
"""
                await self.clients[alert_group].send_message(alert_group, footer)
                add_log(f"✅ تم إرسال نسخة من الرسالة")
        except FloodWaitError as e:
            add_log(f"⚠️ FloodWait: انتظر {e.seconds} ثانية")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            add_log(f"❌ خطأ في الإرسال: {str(e)}")
    
    async def start_radar(self):
        """بدء الرادار"""
        self.running = True
        add_log("🚀 بدء تشغيل الرادار...")
        
        accounts = get_all_accounts()
        for account in accounts:
            if account['enabled']:
                await self.start_client(
                    account['phone'],
                    account['api_id'],
                    account['api_hash'],
                    account['alert_group']
                )
        
        add_log("✅ الرادار يعمل!")
    
    async def stop_radar(self):
        """إيقاف الرادار"""
        self.running = False
        for client in self.clients.values():
            await client.disconnect()
        self.clients.clear()
        add_log("🛑 الرادار متوقف")
    
    def is_running(self):
        return self.running

# إنشاء كائن الرادار
radar = Radar()
