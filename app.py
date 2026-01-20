import streamlit as st
from openai import OpenAI
import PyPDF2

# إعداد الصفحة
st.set_page_config(page_title="المعلم الذكي", page_icon="🎓")

# العنوان
st.title("🎓 المعلم الذكي: مساعدك في حل المسائل")

# جلب المفتاح من أسرار Streamlit
api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

# رفع الملف
uploaded_file = st.file_uploader("قم برفع ملف المحاضرة (PDF)", type="pdf")

# متغير لتخزين نص الملف
pdf_text = ""

if uploaded_file is not None:
    # قراءة ملف PDF
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            pdf_text += page.extract_text()
        st.success("تم قراءة الملف بنجاح! الآن يمكنك طرح أسئلتك.")
    except Exception as e:
        st.error(f"حدث خطأ أثناء قراءة الملف: {e}")

# صندوق المحادثة
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "system", "content": "أنت معلم ذكي ومساعد دراسي. ساعد الطالب في فهم وحل المسائل بناءً على المحتوى المقدم من الملف."}]

# عرض الرسائل السابقة
for msg in st.session_state.messages:
    if msg["role"] != "system":
        st.chat_message(msg["role"]).write(msg["content"])

# استقبال سؤال المستخدم
if prompt := st.chat_input("اكتب سؤالك هنا..."):
    # إضافة سؤال المستخدم للمحادثة
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    # تجهيز الرسالة الكاملة (السؤال + محتوى الملف)
    full_prompt = prompt
    if pdf_text:
        full_prompt = f"بناءً على هذا النص من الملف المرفق:\n{pdf_text}\n\nالسؤال هو: {prompt}"

    # إرسال الطلب للذكاء الاصطناعي
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # أو gpt-3.5-turbo
            messages=[
                {"role": "system", "content": "أنت معلم خبير."},
                {"role": "user", "content": full_prompt}
            ]
        )
        msg_content = response.choices[0].message.content
        
        # عرض الرد وحفظه
        st.session_state.messages.append({"role": "assistant", "content": msg_content})
        st.chat_message("assistant").write(msg_content)
        
    except Exception as e:
        st.error(f"حدث خطأ: {e}")
