import streamlit as st
from openai import OpenAI
import json
import os
import datetime
import base64
import PyPDF2
import sys

# --- 🛠️ إصلاح مشكلة ترميز اللغة العربية ---
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# 1. إعدادات الصفحة
st.set_page_config(
    page_title="معهدي - المدرس الذكي",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 🎨 التصميم العصري (CSS) - تثبيت الكتابة السوداء ---
st.markdown("""
<style>
    /* استيراد خط عربي حديث */
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
    }

    /* ============================================================
       🚨 تثبيت ألوان الفقاعات لتكون دائماً فاتحة وكتابة سوداء
       سواء كان الوضع ليلي أو نهاري (لضمان القراءة)
    ============================================================ */

    /* 1. فقاعة الطالب (User) - دائماً سماوي فاتح وكتابة سوداء */
    div[data-testid="stChatMessage"]:nth-child(odd) {
        background-color: #e3f2fd !important;
        border: 1px solid #bbdefb !important;
        color: #000000 !important;
    }

    /* 2. فقاعة الأستاذ (Assistant) - دائماً أبيض وكتابة سوداء */
    div[data-testid="stChatMessage"]:nth-child(even) {
        background-color: #ffffff !important;
        border: 1px solid #e0e0e0 !important;
        color: #000000 !important;
    }

    /* 3. إجبار جميع النصوص داخل الفقاعات على اللون الأسود */
    div[data-testid="stChatMessage"] p,
    div[data-testid="stChatMessage"] h1,
    div[data-testid="stChatMessage"] h2,
    div[data-testid="stChatMessage"] h3,
    div[data-testid="stChatMessage"] li,
    div[data-testid="stChatMessage"] div {
        color: #000000 !important;
    }

    /* ============================================================ */

    /* تنسيق الأزرار (Gradient) */
    div.stButton > button {
        background: linear-gradient(45deg, #2563eb, #0ea5e9);
        color: white !important;
        border: none;
        border-radius: 12px;
        transition: transform 0.2s;
    }
    div.stButton > button:hover {
        transform: scale(1.02);
    }

    /* الوضع الليلي (فقط للخلفيات العامة، لا يلمس الفقاعات) */
    @media (prefers-color-scheme: dark) {
        .stApp {
            background-color: #0e1117; /* خلفية التطبيق العامة غامقة */
        }
        [data-testid="stSidebar"] {
            background-color: #161b22;
            border-right: 1px solid #30363d;
        }
        h1, h2, h3 {
            color: #e6edf3; /* العناوين الرئيسية تبقى فاتحة */
        }
        .stTextInput input {
            color: white !important;
        }
    }

</style>
""", unsafe_allow_html=True)

# --- دوال التعامل مع الذاكرة ---
HISTORY_FILE = "chat_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_history(history_dict):
    history_to_save = {}
    for k, v in history_dict.items():
        clean_messages = []
        for msg in v["messages"]:
            clean_msg = {key: val for key, val in msg.items() if key not in ["audio_content", "generated_image"]}
            clean_messages.append(clean_msg)
        history_to_save[k] = {"title": v["title"], "messages": clean_messages}
        
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history_to_save, f, ensure_ascii=True, indent=4)
    except Exception as e:
        print(f"Warning: Could not save history: {e}")

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

def get_pdf_text(pdf_file):
    text = ""
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    except Exception as e:
        return f"خطأ في قراءة الملف: {e}"
    return text

# تحميل التاريخ
if "history" not in st.session_state:
    st.session_state.history = load_history()

if "current_chat_id" not in st.session_state:
    new_id = str(datetime.datetime.now())
    st.session_state.current_chat_id = new_id
    st.session_state.history[new_id] = {"title": "محادثة جديدة", "messages": []}

current_id = st.session_state.current_chat_id

if current_id not in st.session_state.history:
     st.session_state.history[current_id] = {"title": "محادثة جديدة", "messages": []}

st.session_state.messages = st.session_state.history[current_id]["messages"]

if "suggestion_clicked" not in st.session_state:
    st.session_state.suggestion_clicked = None

# --- الاتصال الآمن (من ملف الأسرار) ---
try:
    api_key = st.secrets["OPENAI_API_KEY"]
    client = OpenAI(api_key=api_key)
except FileNotFoundError:
    st.error("لم يتم العثور على ملف الأسرار (.streamlit/secrets.toml). يرجى التأكد من إنشائه.")
    st.stop()
except KeyError:
    st.error("المفتاح OPENAI_API_KEY غير موجود داخل ملف secrets.toml.")
    st.stop()

# 2. القائمة الجانبية
with st.sidebar:
    st.markdown("### ⚙️ إعدادات الفصل")
    
    subject = st.selectbox("المادة:", ["الفيزياء", "الكيمياء", "الرياضيات", "الأحياء", "اللغة العربية", "اللغة الإنجليزية"])
    level = st.selectbox("الصف:", ["الثالث متوسط", "الرابع علمي", "الخامس علمي", "السادس علمي", "السادس أدبي"])
    
    st.markdown("---")
    enable_voice = st.toggle("🔊 قراءة الشرح", value=False)
    enable_image_gen = st.toggle("🎨 رسم توضيحي", value=False)
    
    st.markdown("---")
    if st.button("➕ جلسة جديدة", type="primary"):
        new_id = str(datetime.datetime.now())
        st.session_state.current_chat_id = new_id
        st.session_state.history[new_id] = {"title": "محادثة جديدة", "messages": []}
        st.session_state.suggestion_clicked = None
        st.rerun()

    st.markdown("### 📂 السجل")
    history_keys = reversed(list(st.session_state.history.keys()))
    for chat_id in history_keys:
        chat_data = st.session_state.history[chat_id]
        if len(chat_data["messages"]) > 0:
            if st.button(f"📄 {chat_data['title']}", key=chat_id):
                st.session_state.current_chat_id = chat_id
                st.session_state.suggestion_clicked = None
                st.rerun()
    
    st.markdown("---")
    if "confirm_delete" not in st.session_state: st.session_state.confirm_delete = False
    if st.button("🗑️ حذف السجل"): st.session_state.confirm_delete = True
    if st.session_state.confirm_delete:
        c1, c2 = st.columns(2)
        if c1.button("نعم"):
            if os.path.exists(HISTORY_FILE):
                try: os.remove(HISTORY_FILE)
                except: pass
            st.session_state.history = {}
            new_id = str(datetime.datetime.now())
            st.session_state.current_chat_id = new_id
            st.session_state.history[new_id] = {"title": "محادثة جديدة", "messages": []}
            st.session_state.confirm_delete = False
            st.rerun()
        if c2.button("لا"):
            st.session_state.confirm_delete = False
            st.rerun()
            
    if st.button("📝 امتحان سريع"): st.session_state.quiz_trigger = True

# الواجهة الرئيسية
st.title(f"🎓 المساعد الذكي: {subject}")

# 4. عرض الرسائل
for message in st.session_state.messages:
    role = message["role"]
    with st.chat_message(role):
        st.markdown(message["content"])
        if "audio_content" in message:
            st.audio(message["audio_content"], format="audio/mp3")
        if "generated_image" in message:
            st.image(message["generated_image"], caption="رسم توضيحي 🎨")

# --- المنطقة التفاعلية ---
st.markdown("---")
voice_text = ""
uploaded_image = None
audio_value = None
uploaded_pdf = None
pdf_content = ""

with st.expander("📎 المرفقات (صوت، صورة، PDF)", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        audio_value = st.audio_input("تسجيل")
        if audio_value:
            with st.spinner(".."):
                try:
                    transcript = client.audio.transcriptions.create(model="whisper-1", file=("audio.wav", audio_value, "audio/wav"), language="ar")
                    voice_text = transcript.text
                except: pass
    with c2:
        uploaded_image = st.file_uploader("صورة", type=["jpg", "png"])
    with c3:
        uploaded_pdf = st.file_uploader("PDF", type=["pdf"])
        if uploaded_pdf:
            with st.spinner(".."):
                pdf_content = get_pdf_text(uploaded_pdf)
                st.success("تم!")

# الإدخال
prompt_text = st.chat_input("اكتب سؤالك...")
final_prompt = None

if st.session_state.suggestion_clicked:
    final_prompt = st.session_state.suggestion_clicked
    st.session_state.suggestion_clicked = None
elif prompt_text:
    final_prompt = prompt_text
elif voice_text:
    if st.button("🚀 إرسال"): final_prompt = voice_text

if "quiz_trigger" not in st.session_state: st.session_state.quiz_trigger = False
if st.session_state.quiz_trigger:
    st.session_state.quiz_trigger = False
    final_prompt = f"امتحان قصير في {subject}."

if final_prompt:
    st.session_state.messages.append({"role": "user", "content": final_prompt})
    with st.chat_message("user"):
        st.markdown(final_prompt)
    
    pdf_instruction = ""
    if pdf_content:
        pdf_instruction = f"📎 PDF content:\n{pdf_content[:10000]}"

    system_prompt = f"""
    أنت مدرس {subject} للصف {level}.
    - {pdf_instruction}
    - اشرح بلهجة عراقية واضحة.
    - استخدم LaTeX للمعادلات.
    - لو طلب رسمة اكتب: 'IMAGE_REQ'.
    - بعد الإجابة، اقترح 3 أسئلة بفاصل '###SUGGESTIONS###'.
    """
    
    user_content = [{"type": "text", "text": final_prompt}]
    if uploaded_image:
        uploaded_image.seek(0)
        base64_image = encode_image(uploaded_image)
        user_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}})

    history_messages = [{"role": "system", "content": system_prompt}]
    for msg in st.session_state.messages[:-1]:
        content_curr = msg["content"]
        if isinstance(content_curr, list): content_curr = content_curr[0]["text"]
        history_messages.append({"role": msg["role"], "content": content_curr})
    history_messages.append({"role": "user", "content": user_content})

    with st.chat_message("assistant"):
        with st.spinner('🤔'):
            try:
                response = client.chat.completions.create(model="gpt-4o-mini", messages=history_messages)
                full_response = response.choices[0].message.content
                
                suggestions_list = []
                if "###SUGGESTIONS###" in full_response:
                    answer_part, suggestions_part = full_response.split("###SUGGESTIONS###")
                    suggestions_list = [s.strip() for s in suggestions_part.strip().split('\n') if s.strip()]
                    answer_display = answer_part.replace(r"\[", "$$").replace(r"\]", "$$").replace(r"\(", "$").replace(r"\)", "$")
                else:
                    answer_display = full_response.replace(r"\[", "$$").replace(r"\]", "$$").replace(r"\(", "$").replace(r"\)", "$")
                
                st.markdown(answer_display)
                current_msg = {"role": "assistant", "content": answer_display}

                if enable_voice:
                    speech = client.audio.speech.create(model="tts-1", voice="onyx", input=answer_display[:1000])
                    current_msg["audio_content"] = speech.content
                    st.audio(current_msg["audio_content"], format="audio/mp3")

                if enable_image_gen:
                    if "IMAGE_REQ" in full_response or any(k in final_prompt for k in ["ارسم", "رسم"]):
                        img = client.images.generate(model="dall-e-3", prompt=f"Edu diagram {subject}: {final_prompt}", size="1024x1024")
                        current_msg["generated_image"] = img.data[0].url
                        st.image(current_msg["generated_image"])

                if suggestions_list:
                    st.markdown("---")
                    st.caption("💡 مقترحات:")
                    cols = st.columns(len(suggestions_list))
                    for i, sugg in enumerate(suggestions_list):
                        clean = sugg.replace("- ", "").replace("1. ", "")
                        if cols[i].button(clean, key=f"s_{len(st.session_state.messages)}_{i}"):
                            st.session_state.suggestion_clicked = clean
                            st.rerun()

                st.session_state.messages.append(current_msg)
                st.session_state.history[current_id]["messages"] = st.session_state.messages
                save_history(st.session_state.history)

            except Exception as e:
                st.error(f"Error: {e}")
