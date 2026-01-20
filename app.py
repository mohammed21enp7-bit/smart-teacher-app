import streamlit as st
from openai import OpenAI
import PyPDF2
import base64

# --- 1. إعدادات الصفحة والتصميم ---
st.set_page_config(
    page_title="المعلم الذكي",
    page_icon="🎓",
    layout="wide",  # جعل الصفحة عريضة
    initial_sidebar_state="expanded" # القائمة الجانبية مفتوحة دائماً
)

# --- 2. الشريط الجانبي (الإعدادات) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712009.png", width=100)
    st.title("⚙️ إعدادات الدرس")
    
    # اختيار المرحلة
    student_level = st.selectbox(
        "اختر المرحلة الدراسية:",
        ["السادس الإعدادي", "الخامس العلمي", "الأول الجامعي", "مرحلة أخرى"]
    )
    
    # اختيار المادة
    subject = st.selectbox(
        "اختر المادة:",
        ["الفيزياء ⚛️", "الرياضيات 📐", "الكيمياء 🧪", "علوم الحاسوب 💻"]
    )
    
    st.markdown("---")
    st.write("💡 **تلميح:** يمكنك رفع صورة للمسألة أو ملف PDF للمحاضرة.")

# --- 3. المتن الرئيسي (العنوان) ---
st.title(f"🎓 المعلم الذكي: {subject} ({student_level})")
st.markdown("### 💬 اسألني وسأشرح لك باللهجة العراقية")

# --- 4. الربط مع الذكاء الاصطناعي ---
try:
    api_key = st.secrets["OPENAI_API_KEY"]
    client = OpenAI(api_key=api_key)
except:
    st.error("⚠️ لم يتم العثور على مفتاح API. يرجى إضافته في Secrets.")
    st.stop()

# --- 5. وظائف التعامل مع الملفات (صور و PDF) ---
def encode_image(uploaded_file):
    return base64.b64encode(uploaded_file.getvalue()).decode('utf-8')

# مساحة رفع الملفات
upload_col1, upload_col2 = st.columns([2, 1])

with upload_col1:
    upload_type = st.radio("نوع الملف:", ["📸 صورة (مسألة/رسم)", "📄 ملف PDF (نص)"], horizontal=True)

image_base64 = None
pdf_text = ""
file_ready = False

with upload_col2:
    if upload_type == "📸 صورة (مسألة/رسم)":
        uploaded_file = st.file_uploader("ارفع الصورة هنا", type=["png", "jpg", "jpeg"])
        if uploaded_file:
            st.toast("تم رفع الصورة بنجاح!", icon="✅")
            image_base64 = encode_image(uploaded_file)
            with st.expander("عرض الصورة المرفقة"):
                st.image(uploaded_file, use_container_width=True)
            file_ready = True
            
    else:
        uploaded_file = st.file_uploader("ارفع ملف PDF", type="pdf")
        if uploaded_file:
            try:
                pdf_reader = PyPDF2.PdfReader(uploaded_file)
                for page in pdf_reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        pdf_text += extracted + "\n"
                
                if pdf_text.strip():
                    st.toast("تم قراءة ملف PDF بنجاح!", icon="✅")
                    file_ready = True
                else:
                    st.warning("⚠️ الملف عبارة عن صور (Scanned). يفضل استخدام خيار 'صورة'.")
            except:
                st.error("خطأ في الملف.")

# --- 6. واجهة المحادثة (الشات) ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# عرض الرسائل القديمة
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

# --- 7. استقبال السؤال والمعالجة ---
if prompt := st.chat_input("اكتب سؤالك هنا..."):
    
    # عرض سؤال المستخدم
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # تجهيز التوجيه للنظام (System Prompt)
    system_instruction = f"""
    أنت معلم خصوصي خبير لمادة {subject} للمرحلة {student_level}.
    اشرح بوضوح وباللهجة العراقية الدارجة والمحببة.
    استخدم أمثلة واقعية لتبسيط الفكرة.
    """

    messages_payload = [{"role": "system", "content": system_instruction}]

    # إضافة المحتوى المرفق (صورة أو نص)
    if image_base64:
        user_msg = {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
            ]
        }
        messages_payload.append(user_msg)
    elif pdf_text:
        full_prompt = f"بناءً على هذا النص:\n{pdf_text}\n\nالسؤال: {prompt}"
        messages_payload.append({"role": "user", "content": full_prompt})
    else:
        messages_payload.append({"role": "user", "content": prompt})

    # الاتصال بـ OpenAI وعرض الرد
    with st.chat_message("assistant"):
        with st.spinner('جاري التفكير وحل المسألة... 🧠'):
            try:
                stream = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages_payload,
                    stream=True
                )
                response = st.write_stream(stream)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"حدث خطأ: {e}")
