import streamlit as st
from openai import OpenAI
import PyPDF2

# إعداد الصفحة
st.set_page_config(page_title="المعلم الذكي", page_icon="🎓")
st.title("🎓 المعلم الذكي: مساعدك الدراسي")

# جلب المفتاح
try:
    api_key = st.secrets["OPENAI_API_KEY"]
    client = OpenAI(api_key=api_key)
except:
    st.error("لم يتم العثور على مفتاح API. تأكد من وضعه في Secrets.")
    st.stop()

# تهيئة الذاكرة لتخزين نص الملف
if "pdf_content" not in st.session_state:
    st.session_state.pdf_content = ""

# رفع الملف
uploaded_file = st.file_uploader("ارفع ملف المحاضرة (PDF)", type="pdf")

if uploaded_file is not None:
    # قراءة الملف مرة واحدة وتخزينه
    if st.session_state.pdf_content == "":
        try:
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in pdf_reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            
            st.session_state.pdf_content = text
            
            if text.strip():
                st.success("✅ تم استخراج النص بنجاح!")
            else:
                st.warning("⚠️ الملف يبدو فارغاً أو عبارة عن صور (Scanned). الروبوت قد لا يستطيع قراءته.")
                
        except Exception as e:
            st.error(f"حدث خطأ في القراءة: {e}")

    # عرض ما يراه الروبوت (للتأكد)
    with st.expander("👀 اضغط هنا لترَ ما قرأه الروبوت من الملف"):
        st.text(st.session_state.pdf_content)

# إدارة المحادثة
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# استقبال السؤال
if prompt := st.chat_input("اسأل عن شيء في الملف..."):
    # عرض سؤال المستخدم
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    # تجهيز الرسالة للذكاء
    if st.session_state.pdf_content:
        full_prompt = f"""
        لديك هذا المحتوى من ملف دراسي:
        {st.session_state.pdf_content}
        
        بناءً على المحتوى السابق، أجب على هذا السؤال باللهجة العراقية وشرح مبسط:
        {prompt}
        """
    else:
        # إذا لم يكن هناك نص مستخرج
        full_prompt = prompt 

    # الإرسال لـ OpenAI
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "أنت معلم فيزياء شاطر باللهجة العراقية."},
                {"role": "user", "content": full_prompt}
            ]
        )
        msg_content = response.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": msg_content})
        st.chat_message("assistant").write(msg_content)
        
    except Exception as e:
        st.error(f"حدث خطأ في الاتصال: {e}")
