import aiohttp
import json
from config import Config

PROMPT = """
أنت مساعد ذكي متخصص في تحليل رسائل تليجرام وتصنيف المرسلين بدقة عالية. المهمة: تحديد ما إذا كان المرسل **طالباً يطلب مساعدة** (seeker) أم **معلناً يروج لخدمات** (marketer).

### **معايير التصنيف الدقيقة**

#### **أولاً: فئة الطالب (seeker)**
- السمات: يطلب مساعدة في مجاله الدراسي أو الأكاديمي.
- أمثلة: "حد يعرف دكتور يشرح عملي الفارما؟"، "أبي أحد يحل واجب الرياضيات ضروري"
- علامات الطالب:
  - أسئلة استفهامية
  - طلب مساعدة مباشرة
  - لا يحتوي على روابط تواصل
  - لا يحتوي على قوائم خدمات
  - لهجة طلبية (أبي، ساعدني، من يعرف)

#### **ثانياً: فئة المعلن (marketer)**
- السمات: يقدم خدمات تجارية، يحتوي على روابط واتساب أو تليجرام، قوائم طويلة بالخدمات، رموز تزيينية.
- أمثلة: "✨📚 خدمات طلابية شاملة لدعم نجاحك الأكاديمي! 🎓✨"
- علامات المعلن:
  - روابط واتساب/تليجرام
  - قوائم خدمات طويلة
  - رموز تزيينية (✨, ✅, 🎓, 💯)
  - عبارات تجارية (نقدم لكم، لدينا، للتواصل)
  - دعوة للتواصل الخاص

### **تعليمات خاصة**
- إذا كانت الرسالة تحتوي على روابط + قائمة خدمات → **marketer**
- إذا كانت الرسالة استفهاماً وتخلو من الروابط وقوائم الخدمات → **seeker**
- انتبه للهجة الخليجية: "أبي أحد" تدل على طالب، "نقدم لكم" تدل على معلن
- الثقة يجب أن تكون بين 0-100

### **المخرجات المطلوبة**
يجب أن تكون النتيجة بصيغة JSON فقط:
{"type": "seeker" أو "marketer", "confidence": 0-100, "reason": "سبب مختصر"}

الرسالة المراد تحليلها:
{message}
"""

async def classify_message(message):
    """تصنيف الرسالة باستخدام الذكاء الاصطناعي"""
    if not Config.AI_ENABLED or not Config.OPENROUTER_API_KEY:
        return {"type": "seeker", "confidence": 50, "reason": "AI غير مفعل"}
    
    try:
        prompt = PROMPT.replace("{message}", message)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {Config.OPENROUTER_API_KEY}',
                    'Content-Type': 'application/json',
                    'HTTP-Referer': 'https://radar.telegram.com',
                    'X-Title': 'Telegram Radar'
                },
                json={
                    'model': Config.AI_MODEL,
                    'messages': [{'role': 'user', 'content': prompt}]
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data['choices'][0]['message']['content']
                    try:
                        json_start = content.find('{')
                        json_end = content.rfind('}') + 1
                        if json_start != -1 and json_end != -1:
                            result = json.loads(content[json_start:json_end])
                            return result
                    except:
                        pass
                return {"type": "seeker", "confidence": 50, "reason": "AI Error"}
    except Exception as e:
        return {"type": "seeker", "confidence": 50, "reason": f"AI Error: {str(e)}"}
