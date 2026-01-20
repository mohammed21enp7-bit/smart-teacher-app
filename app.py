import streamlit as st
from openai import OpenAI
import PyPDF2
import base64

# إعداد الصفحة
st.set_page_config(page_title="المعلم الذكي", page_icon="🎓")
st.title("🎓 المعلم الذكي: حل المسائل بالصور")

# جلب المفتاح
try:
    api_key = st.secrets["OPENAI_API_KEY"]
    client = OpenAI(api_key=api_key)
except:
    st.error("لم يتم العثور على مفتاح API. تأكد من وضعه في Secrets.")
    st.stop()

# دالة لتحويل الصورة إلى نص يفهمه الذكاء (Base64)
def encode_image(uploaded_file):
    return base64.b64encode(uploaded_file.getvalue()).decode('utf-8')

# اختيار نوع الملف (صورة أو PDF)
upload_type = st.radio("ماذا تريد أن ترفع؟", ["صورة للمسألة (أفضل وأضمن)", "ملف PDF (للنصوص فقط)"])

uploaded_file = None
image_base64 = None
pdf_text = ""

if upload_type == "صورة للمسألة (أفضل وأضمن)":
    uploaded_file = st.file_uploader("التقط صورة للمسألة وارفعها هنا", type=["png", "jpg", "jpeg"])
    if uploaded_file:
        st.image(uploaded_file, caption="الصورة المرفقة", use_container_width=True)
        # تحويل الصورة لتجهيزها للذكاء
        image_base64 = encode_image(uploaded_file)

else:
    uploaded_file = st.file_uploader("ارفع ملف المحاضرة (PDF)", type="pdf")
    if uploaded_file:
        try:
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            for page in pdf_reader.pages:
                extracted = page.extract_text()
                if extracted:
                    pdf_text += extracted + "\n"
            
            if pdf_text.strip():
                st.success("✅ تم استخراج النص من الملف.")
                with st.expander("عرض النص المستخرج"):
                    st.text(pdf_text)
            else:
                st.warning("⚠️ الملف عبارة عن صور (Scanned). يفضل استخدام خيار 'صورة للمسألة' في الأعلى.")
        except Exception as e:
            st.error("حدث خطأ في قراءة الملف.")

# إدارة المحادثة
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    if msg["role"] != "system":
        st.chat_message(msg["role"]).write(msg["content"])

# استقبال السؤال
if prompt := st.chat_input("اكتب سؤالك هنا (مثلاً: حل السؤال في الصورة)..."):
    
    # عرض سؤال المستخدم
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    # تجهيز الرسالة للذكاء الاصطناعي
    messages_payload = [
        {"role": "system", "content": "أنت معلم فيزياء خبير باللهجة العراقية. قم بتحليل المدخلات (سواء نص أو صورة) وقدم حلاً مفصلاً."}
    ]

    # حالة 1: المستخدم رفع صورة
    if image_base64:
        user_msg = {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }
                }
            ]
        }
        messages_payload.append(user_msg)
    
    # حالة 2: المستخدم رفع PDF نصي
    elif pdf_text:
        full_prompt = f"بناءً على هذا النص:\n{pdf_text}\n\nالسؤال: {prompt}"
        messages_payload.append({"role": "user", "content": full_prompt})
    
    # حالة 3: سؤال عام بدون ملفات
    else:
        messages_payload.append({"role": "user", "content": prompt})

    # الإرسال لـ OpenAI
    try:
        with st.spinner("جاري التفكير وحل المسألة..."):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages_payload,
                max_tokens=1000
            )
            msg_content = response.choices[0].message.content
            
            st.session_state.messages.append({"role": "assistant", "content": msg_content})
            st.chat_message("assistant").write(msg_content)
            
    except Exception as e:
        st.error(f"حدث خطأ: {e}")
