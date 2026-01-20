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

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

st.set_page_config(page_title="معهدي - المدرس الذكي", page_icon="🎓", layout="wide")

# --- 🎨 التصميم (CSS) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; }
    div[data-testid="stChatMessage"]:nth-child(odd) { background-color: #e3f2fd !important; border: 1px solid #bbdefb !important; border-radius: 15px; color: #000 !important; }
    div[data-testid="stChatMessage"]:nth-child(even) { background-color: #ffffff !important; border: 1px solid #e0e0e0 !important; border-radius: 15px; color: #000 !important; }
    div[data-testid="stChatMessage"] p { color: #000000 !important; font-size: 18px; }
    div.stButton > button { background: linear-gradient(45deg, #2563eb, #0ea5e9); color: white !important; border-radius: 12px; font-weight: 600; }
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

if "history" not in st.session_state: st.session_state.history = load_history()
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = str(datetime.datetime.now())
    st.session_state.history[st.session_state.current_chat_id] = {"title": "محادثة جديدة", "messages": []}

current_id = st.session_state.current_chat_id
st.session_state.messages = st.session_state.history[current_id]["messages"]
if "suggestion_clicked" not in st.session_state: st.session_state.suggestion_clicked = None
if "quiz_trigger" not in st.session_state: st.session_state.quiz_trigger = False

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- القائمة الجانبية ---
with st.sidebar:
    st.markdown("### ⚙️ إعدادات الفصل")
    subject = st.selectbox("المادة:", ["الفيزياء", "الكيمياء", "الرياضيات", "الأحياء", "اللغة العربية"])
    level = st.selectbox("الصف:", ["الثالث متوسط", "الرابع علمي", "الخامس علمي", "السادس علمي", "السادس أدبي"])
    
    st.markdown("---")
    user_code = st.text_input("🔑 كود التفعيل:", type="password")
    current_limit = LIMITS.get(user_code, LIMITS["free"])
    st.write(f"📊 المحاولات: {st.session_state.usage_counter} / {current_limit}")
    st.progress(min(st.session_state.usage_counter / current_limit, 1.0))
    
    st.markdown("---")
    enable_voice = st.toggle("🔊 قراءة صوتية", value=False)
    enable_image_gen = st.toggle("🎨 رسم توضيحي", value=False)
    
    if st.button("➕ جلسة جديدة", type="primary"):
        st.session_state.current_chat_id = str(datetime.datetime.now())
        st.session_state.history[st.session_state.current_chat_id] = {"title": "محادثة جديدة", "messages": []}
        st.rerun()

    if st.button("📝 امتحان سريع"): st.session_state.quiz_trigger = True

# الواجهة الرئيسية
st.title(f"🎓 الأستاذ الذكي: {subject}")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "audio_content" in msg: st.audio(msg["audio_content"], format="audio/mp3")

with st.expander("📎 المرفقات"):
    c1, c2, c3 = st.columns(3)
    with c1: audio_in = st.audio_input("تسجيل")
    with c2: img_in = st.file_uploader("صورة", type=["jpg", "png"])
    with c3: pdf_in = st.file_uploader("PDF", type=["pdf"])

prompt_in = st.chat_input("اسأل أستاذك...")
final_prompt = None

if st.session_state.suggestion_clicked:
    final_prompt = st.session_state.suggestion_clicked
    st.session_state.suggestion_clicked = None
elif st.session_state.quiz_trigger:
    final_prompt = f"امتحان في {subject}."
    st.session_state.quiz_trigger = False
elif prompt_in: final_prompt = prompt_input = prompt_in
elif audio_in:
    try:
        transcript = client.audio.transcriptions.create(model="whisper-1", file=("audio.wav", audio_in, "audio/wav"), language="ar")
        final_prompt = transcript.text
    except: pass

if final_prompt:
    if st.session_state.usage_counter >= current_limit:
        st.error(f"🛑 انتهت محاولاتك ({current_limit}).")
    else:
        st.session_state.messages.append({"role": "user", "content": final_prompt})
        with st.chat_message("user"): st.markdown(final_prompt)
        
        pdf_txt = ""
        if pdf_in:
            reader = PyPDF2.PdfReader(pdf_in)
            for page in reader.pages: pdf_txt += page.extract_text()

        # --- 🧠 منطق الفصل المرن (The Flexible Persona) ---
        system_logic = f"""أنت "أستاذ مادة {subject}" للصف {level}.
        
        قوانين التعامل الذكي مع الأسئلة:
        1. الإطار العلمي: إذا كان السؤال ضمن {subject}، أجب بتعمق.
        2. التداخل العلمي (المهم): إذا سأل الطالب عن موضوع مشترك (مثلاً الكيمياء الفيزيائية وأنت في الفيزياء، أو الإحصاء وأنت في الرياضيات)، أجب بذكاء ووضح له كيف يرتبط هذا الموضوع بـ {subject}. لا ترفض الإجابة عن العلوم المتقاربة.
        3. الخروج التام: إذا كان السؤال بعيداً كلياً عن العلم (طبخ، شعر، أخبار فنانين) وأنت في درس علمي:
           - اعتذر بلهجة عراقية: "يا بطل، أنا أستاذ الـ{subject}، وما أريد نضيع وقتنا بغير مواضيع حتى نضبط المادة. خلينا بـ{subject}!"
        
        التعليمات:
        - اللهجة: عراقية محببة.
        - المعادلات: استخدم LaTeX بصيغة $$...$$.
        - لو طلب رسمة اكتب 'IMAGE_REQ'.
        - المقترحات: ضع 3 أسئلة بعد '###SUGGESTIONS###'."""

        with st.chat_message("assistant"):
            with st.spinner('🤔 جاري المعالجة...'):
                try:
                    content_list = [{"type": "text", "text": final_prompt}]
                    if img_in:
                        b64 = base64.b64encode(img_in.getvalue()).decode('utf-8')
                        content_list.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})

                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "system", "content": system_logic}, {"role": "user", "content": content_list}]
                    )
                    full_res = response.choices[0].message.content
                    
                    if "###SUGGESTIONS###" in full_res:
                        answer, suggs = full_res.split("###SUGGESTIONS###")
                        s_list = [s.strip() for s in suggs.strip().split('\n') if s.strip()][:3]
                    else:
                        answer, s_list = full_res, []

                    st.markdown(answer)
                    msg_obj = {"role": "assistant", "content": answer}

                    if enable_voice:
                        speech = client.audio.speech.create(model="tts-1", voice="onyx", input=answer[:500])
                        msg_obj["audio_content"] = speech.content
                        st.audio(msg_obj["audio_content"])

                    if enable_image_gen and "IMAGE_REQ" in full_res:
                        img_gen = client.images.generate(model="dall-e-3", prompt=f"Scientific diagram about {final_prompt}", size="1024x1024")
                        st.image(img_gen.data[0].url)

                    if s_list:
                        st.markdown("---")
                        cols = st.columns(len(s_list))
                        for i, s in enumerate(s_list):
                            clean = s.replace("- ", "").replace("1. ", "").replace("2. ", "").replace("3. ", "")
                            if cols[i].button(clean, key=f"btn_{i}"):
                                st.session_state.suggestion_clicked = clean
                                st.rerun()

                    st.session_state.messages.append(msg_obj)
                    st.session_state.usage_counter += 1
                    save_history(st.session_state.history)
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")
