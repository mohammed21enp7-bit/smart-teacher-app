import streamlit as st
from openai import OpenAI
import json
import os
import datetime
import base64
import PyPDF2
import sys

# --- 🛠️ إعدادات الصلاحيات (Limits) ---
LIMITS = {
    "free": 5,      # المستخدم العادي
    "VIP10": 15,    # كود تفعيلي للأصدقاء
    "ADMIN": 1000   # كودك الشخصي (مفتوح)
}

# إصلاح ترميز اللغة العربية للنظام
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# 1. إعدادات الصفحة الأساسية
st.set_page_config(
    page_title="معهدي - المدرس الذكي",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 🎨 التصميم العصري (CSS) - النسخة الكاملة والمثبتة ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; }

    /* تنسيق فقاعات الدردشة */
    div[data-testid="stChatMessage"]:nth-child(odd) {
        background-color: #e3f2fd !important;
        border: 1px solid #bbdefb !important;
        border-radius: 15px;
        color: #000 !important;
    }
    div[data-testid="stChatMessage"]:nth-child(even) {
        background-color: #ffffff !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 15px;
        color: #000 !important;
    }
    div[data-testid="stChatMessage"] p { color: #000000 !important; font-size: 18px; }

    /* تنسيق الأزرار */
    div.stButton > button {
        background: linear-gradient(45deg, #2563eb, #0ea5e9);
        color: white !important;
        border: none;
        border-radius: 12px;
        font-weight: 600;
        transition: 0.3s;
    }
    div.stButton > button:hover { transform: scale(1.02); opacity: 0.9; }
</style>
""", unsafe_allow_html=True)

# --- إدارة الذاكرة والتاريخ ---
HISTORY_FILE = "chat_history.json"
if "usage_counter" not in st.session_state: st.session_state.usage_counter = 0

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def save_history(history_dict):
    to_save = {}
    for k, v in history_dict.items():
        # نحفظ النصوص فقط لتقليل الحجم وتجنب مشاكل الملفات الكبيرة
        msgs = [{"role": m["role"], "content": m["content"]} for m in v["messages"] if "audio_content" not in m]
        to_save[k] = {"title": v["title"], "messages": msgs}
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(to_save, f, ensure_ascii=False, indent=4)
    except: pass

# تهيئة الجلسة والتاريخ
if "history" not in st.session_state: st.session_state.history = load_history()
if "current_chat_id" not in st.session_state:
    new_id = str(datetime.datetime.now())
    st.session_state.current_chat_id = new_id
    st.session_state.history[new_id] = {"title": "محادثة جديدة", "messages": []}

current_id = st.session_state.current_chat_id
st.session_state.messages = st.session_state.history[current_id]["messages"]

# متغيرات التحكم
if "suggestion_clicked" not in st.session_state: st.session_state.suggestion_clicked = None
if "quiz_trigger" not in st.session_state: st.session_state.quiz_trigger = False

# الاتصال بـ OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- 2. القائمة الجانبية (لوحة التحكم) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712009.png", width=70)
    st.markdown("### ⚙️ إعدادات الفصل")
    subject = st.selectbox("المادة الحالية:", ["الفيزياء", "الكيمياء", "الرياضيات", "الأحياء", "اللغة العربية"])
    level = st.selectbox("الصف الدراسي:", ["الثالث متوسط", "الرابع علمي", "الخامس علمي", "السادس علمي", "السادس أدبي"])
    
    st.markdown("---")
    # نظام الأكواد والعداد
    user_code = st.text_input("🔑 كود التفعيل (اختياري):", type="password")
    current_limit = LIMITS.get(user_code, LIMITS["free"])
    
    st.write(f"📊 المحاولات المستخدمة: **{st.session_state.usage_counter} / {current_limit}**")
    st.progress(min(st.session_state.usage_counter / current_limit, 1.0))
    
    st.markdown("---")
    enable_voice = st.toggle("🔊 قراءة الإجابة صوتياً", value=False)
    enable_image_gen = st.toggle("🎨 ميزة الرسم التوضيحي", value=False)
    
    if st.button("➕ افتح جلسة دراسية جديدة", type="primary"):
        new_chat_id = str(datetime.datetime.now())
        st.session_state.current_chat_id = new_chat_id
        st.session_state.history[new_chat_id] = {"title": "محادثة جديدة", "messages": []}
        st.rerun()

    if st.button("📝 امتحان سريع في المادة"):
        st.session_state.quiz_trigger = True

    st.markdown("### 📂 سجل الدروس")
    for chat_id in reversed(list(st.session_state.history.keys())):
        if len(st.session_state.history[chat_id]["messages"]) > 0:
            if st.button(f"📄 {st.session_state.history[chat_id]['title'][:25]}", key=chat_id):
                st.session_state.current_chat_id = chat_id
                st.rerun()

# الواجهة الرئيسية
st.title(f"🎓 الأستاذ الذكي لمادة {subject}")
st.info(f"أهلاً بك يا بطل! أنت الآن في درس {subject} لطلبة {level}.")

# عرض الرسائل السابقة
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "audio_content" in msg: st.audio(msg["audio_content"], format="audio/mp3")

# منطقة المرفقات
with st.expander("📎 هل لديك ملف أو صورة للمسألة؟", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1: audio_input = st.audio_input("اسأل بصوتك")
    with c2: img_file = st.file_uploader("ارفع صورة", type=["jpg", "png", "jpeg"])
    with c3: pdf_file = st.file_uploader("ارفع ملف PDF", type=["pdf"])

# معالجة المدخلات (نص، صوت، امتحان، مقترح)
prompt_input = st.chat_input("اكتب سؤالك بخصوص المادة هنا...")
final_prompt = None

if st.session_state.suggestion_clicked:
    final_prompt = st.session_state.suggestion_clicked
    st.session_state.suggestion_clicked = None
elif st.session_state.quiz_trigger:
    final_prompt = f"اريد امتحان قصير ومكثف في مادة {subject}."
    st.session_state.quiz_trigger = False
elif prompt_input:
    final_prompt = prompt_input
elif audio_input:
    try:
        transcript = client.audio.transcriptions.create(model="whisper-1", file=("audio.wav", audio_input, "audio/wav"), language="ar")
        final_prompt = transcript.text
    except: pass

# --- تنفيذ طلب الذكاء الاصطناعي ---
if final_prompt:
    # التحقق من العداد قبل الإرسال
    if st.session_state.usage_counter >= current_limit:
        st.error(f"🛑 عذراً يا بطل! لقد استهلكت جميع محاولاتك المتاحة ({current_limit}). تواصل مع الأستاذ للحصول على كود تفعيل إضافي.")
    else:
        st.session_state.messages.append({"role": "user", "content": final_prompt})
        with st.chat_message("user"):
            st.markdown(final_prompt)
            if img_file: st.image(img_file, width=250)
        
        # استخراج نص الـ PDF
        pdf_text = ""
        if pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            for page in reader.pages: pdf_text += page.extract_text()
            
        # --- السستم برومبت المطوّر (الفصل الذكي) ---
        system_instruction = f"""أنت "الأستاذ الخبير" لمادة {subject} لطلبة {level}.
        
        قواعد الإجابة الصارمة:
        1. إذا كان السؤال في صلب مادة {subject} أو يرتبط بها علمياً (مثل علاقة الكيمياء بالفيزياء)، أجب بذكاء وباللهجة العراقية.
        2. إذا كان السؤال خارج مادة {subject} تماماً (مثلاً يسأل عن شعراء وهو في الفيزياء):
           - لا تجب على السؤال إطلاقاً.
           - اعتذر بلهجة محببة: "يا بطل، أنا أستاذ الـ{subject}، وما أريد نشتت انتباهنا عن قوانين المادة حتى نضمن الـ100. خلينا بموضوعنا!"
        
        التعليمات التقنية:
        - استخدم LaTeX للمعادلات بصيغة $$...$$.
        - اعتمد على نص الملف المرفق إن وجد: {pdf_text[:2000]}
        - لو طلب رسمة توضيحية اكتب حصراً: 'IMAGE_REQ'.
        - بعد إجابتك، اقترح 3 أسئلة قصيرة للمتابعة بفاصل '###SUGGESTIONS###'."""

        with st.chat_message("assistant"):
            with st.spinner('🤔 جاري التفكير بذكاء...'):
                try:
                    # تحضير المحتوى
                    content_payload = [{"type": "text", "text": final_prompt}]
                    if img_file:
                        b64_img = base64.b64encode(img_file.getvalue()).decode('utf-8')
                        content_payload.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}})

                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "system", "content": system_instruction}, {"role": "user", "content": content_payload}]
                    )
                    full_text = response.choices[0].message.content
                    
                    # معالجة الاقتراحات
                    if "###SUGGESTIONS###" in full_text:
                        answer, sugg_raw = full_text.split("###SUGGESTIONS###")
                        suggestions_list = [s.strip() for s in sugg_raw.strip().split('\n') if s.strip()][:3]
                    else:
                        answer, suggestions_list = full_text, []

                    st.markdown(answer)
                    msg_data = {"role": "assistant", "content": answer}

                    # ميزة الصوت
                    if enable_voice:
                        audio_res = client.audio.speech.create(model="tts-1", voice="onyx", input=answer[:500])
                        msg_data["audio_content"] = audio_res.content
                        st.audio(msg_data["audio_content"])

                    # ميزة الرسم
                    if enable_image_gen and "IMAGE_REQ" in full_text:
                        img_res = client.images.generate(model="dall-e-3", prompt=f"Diagram for {subject}: {final_prompt}", size="1024x1024")
                        st.image(img_res.data[0].url, caption="رسم توضيحي من الأستاذ 🎨")

                    # عرض الأزرار المقترحة
                    if suggestions_list:
                        st.markdown("---")
                        st.caption("💡 جرب تسأل:")
                        cols = st.columns(len(suggestions_list))
                        for i, s in enumerate(suggestions_list):
                            clean_s = s.replace("- ", "").replace("1. ", "").replace("2. ", "").replace("3. ", "")
                            if cols[i].button(clean_s, key=f"sugg_{i}"):
                                st.session_state.suggestion_clicked = clean_s
                                st.rerun()

                    # تحديث السجل والعداد
                    st.session_state.messages.append(msg_data)
                    st.session_state.usage_counter += 1
                    save_history(st.session_state.history)
                    st.rerun()
                except Exception as e: st.error(f"حدث خطأ فني: {e}")
