import streamlit as st
from openai import OpenAI
import json
import os
import datetime
import base64
import PyPDF2
import sys

# --- 🛠️ إعدادات الصلاحيات ---
LIMITS = {"free": 5, "VIP10": 15, "ADMIN": 1000}

# إصلاح ترميز اللغة العربية
try: sys.stdout.reconfigure(encoding='utf-8')
except: pass

st.set_page_config(page_title="معهدي - المدرس الذكي", page_icon="🎓", layout="wide")

# --- 🎨 التصميم (CSS) - كودك الأصلي بدون نقص ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; }
    div[data-testid="stChatMessage"]:nth-child(odd) { background-color: #e3f2fd !important; border: 1px solid #bbdefb !important; color: #000 !important; }
    div[data-testid="stChatMessage"]:nth-child(even) { background-color: #ffffff !important; border: 1px solid #e0e0e0 !important; color: #000 !important; }
    div[data-testid="stChatMessage"] p { color: #000000 !important; }
    div.stButton > button { background: linear-gradient(45deg, #2563eb, #0ea5e9); color: white !important; border-radius: 12px; }
</style>
""", unsafe_allow_html=True)

# --- إدارة الذاكرة ---
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
        msgs = [{"role": m["role"], "content": m["content"]} for m in v["messages"] if "audio_content" not in m]
        to_save[k] = {"title": v["title"], "messages": msgs}
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f: json.dump(to_save, f, ensure_ascii=False, indent=4)
    except: pass

# تحميل التاريخ والجلسة
if "history" not in st.session_state: st.session_state.history = load_history()
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = str(datetime.datetime.now())
    st.session_state.history[st.session_state.current_chat_id] = {"title": "محادثة جديدة", "messages": []}

current_id = st.session_state.current_chat_id
st.session_state.messages = st.session_state.history[current_id]["messages"]
if "suggestion_clicked" not in st.session_state: st.session_state.suggestion_clicked = None
if "quiz_trigger" not in st.session_state: st.session_state.quiz_trigger = False

# --- الاتصال بـ OpenAI ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- 2. القائمة الجانبية (استعادة كل الأزرار) ---
with st.sidebar:
    st.markdown("### ⚙️ إعدادات الفصل")
    subject = st.selectbox("المادة:", ["الفيزياء", "الكيمياء", "الرياضيات", "الأحياء", "اللغة العربية", "اللغة الإنجليزية"])
    level = st.selectbox("الصف:", ["الثالث متوسط", "الرابع علمي", "الخامس علمي", "السادس علمي", "السادس أدبي"])
    
    st.markdown("---")
    access_code = st.text_input("🔑 كود التفعيل:", type="password")
    user_limit = LIMITS.get(access_code, LIMITS["free"])
    st.write(f"📊 المحاولات: {st.session_state.usage_counter} / {user_limit}")
    st.progress(min(st.session_state.usage_counter / user_limit, 1.0))
    
    st.markdown("---")
    enable_voice = st.toggle("🔊 قراءة الشرح", value=False)
    enable_image_gen = st.toggle("🎨 رسم توضيحي", value=False)
    
    if st.button("➕ جلسة جديدة", type="primary"):
        st.session_state.current_chat_id = str(datetime.datetime.now())
        st.session_state.history[st.session_state.current_chat_id] = {"title": "محادثة جديدة", "messages": []}
        st.rerun()

    if st.button("📝 امتحان سريع"):
        st.session_state.quiz_trigger = True

    st.markdown("### 📂 السجل")
    for chat_id in reversed(list(st.session_state.history.keys())):
        if len(st.session_state.history[chat_id]["messages"]) > 0:
            if st.button(f"📄 {st.session_state.history[chat_id]['title'][:20]}", key=chat_id):
                st.session_state.current_chat_id = chat_id
                st.rerun()

# الواجهة الرئيسية
st.title(f"🎓 المساعد الذكي: {subject}")

# عرض الرسائل
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "audio_content" in msg: st.audio(msg["audio_content"], format="audio/mp3")

# المرفقات
with st.expander("📎 المرفقات"):
    c1, c2, c3 = st.columns(3)
    with c1: audio_val = st.audio_input("تسجيل")
    with c2: up_img = st.file_uploader("صورة", type=["jpg", "png"])
    with c3: up_pdf = st.file_uploader("PDF", type=["pdf"])

# معالجة المدخلات
prompt_text = st.chat_input("اكتب سؤالك...")
final_prompt = None

if st.session_state.suggestion_clicked:
    final_prompt = st.session_state.suggestion_clicked
    st.session_state.suggestion_clicked = None
elif st.session_state.quiz_trigger:
    final_prompt = f"اعمل لي امتحان سريع وقصير في مادة {subject}."
    st.session_state.quiz_trigger = False
elif prompt_text:
    final_prompt = prompt_text
elif audio_val:
    try:
        transcript = client.audio.transcriptions.create(model="whisper-1", file=("audio.wav", audio_val, "audio/wav"), language="ar")
        final_prompt = transcript.text
    except: pass

# --- تنفيذ الطلب ---
if final_prompt:
    if st.session_state.usage_counter >= user_limit:
        st.error(f"🛑 عذراً! انتهت محاولاتك ({user_limit}).")
    else:
        st.session_state.messages.append({"role": "user", "content": final_prompt})
        with st.chat_message("user"): st.markdown(final_prompt)
        
        pdf_txt = ""
        if up_pdf:
            reader = PyPDF2.PdfReader(up_pdf)
            for page in reader.pages: pdf_txt += page.extract_text()
            
        system_msg = f"""أنت مدرس {subject} خبير للصف {level}.
        - استخدم اللهجة العراقية المحببة.
        - استخدم LaTeX للمعادلات بصيغة $$...$$.
        - إذا كان هناك نص PDF، اعتمد عليه: {pdf_txt[:2000]}
        - لو طلب رسمة أو احتاج الأمر لرسم اكتب: 'IMAGE_REQ'.
        - بعد إجابتك، اقترح 3 أسئلة قصيرة للمتابعة بفاصل '###SUGGESTIONS###'."""

        with st.chat_message("assistant"):
            with st.spinner('🤔 جاري التحضير...'):
                try:
                    # تحضير محتوى المستخدم (نص + صورة)
                    user_content = [{"type": "text", "text": final_prompt}]
                    if up_img:
                        base64_img = base64.b64encode(up_img.getvalue()).decode('utf-8')
                        user_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}})

                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_content}]
                    )
                    full_res = response.choices[0].message.content
                    
                    # معالجة المقترحات (كودك الأصلي)
                    if "###SUGGESTIONS###" in full_res:
                        ans_part, sugg_part = full_res.split("###SUGGESTIONS###")
                        suggestions = [s.strip() for s in sugg_part.strip().split('\n') if s.strip()][:3]
                    else:
                        ans_part, suggestions = full_res, []

                    st.markdown(ans_part)
                    new_msg = {"role": "assistant", "content": ans_part}

                    if enable_voice:
                        speech = client.audio.speech.create(model="tts-1", voice="onyx", input=ans_part[:500])
                        new_msg["audio_content"] = speech.content
                        st.audio(new_msg["audio_content"])

                    if enable_image_gen and "IMAGE_REQ" in full_res:
                        img = client.images.generate(model="dall-e-3", prompt=f"Educational diagram about {final_prompt}", size="1024x1024")
                        st.image(img.data[0].url)

                    # عرض أزرار المقترحات
                    if suggestions:
                        st.markdown("---")
                        cols = st.columns(len(suggestions))
                        for i, s in enumerate(suggestions):
                            clean_s = s.replace("- ", "").replace("1. ", "").replace("2. ", "").replace("3. ", "")
                            if cols[i].button(clean_s, key=f"s_{i}"):
                                st.session_state.suggestion_clicked = clean_s
                                st.rerun()

                    st.session_state.messages.append(new_msg)
                    st.session_state.usage_counter += 1
                    save_history(st.session_state.history)
                    st.rerun()
                except Exception as e: st.error(f"خطأ: {e}")
