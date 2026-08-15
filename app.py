import base64
import json
import sqlite3
import io
import textwrap
import streamlit as st
from PIL import Image
from groq import Groq
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

client = Groq(api_key=st.secrets["GROQ_API_KEY"])
st.set_page_config(page_title="AI Medical Assistant & Summarizer", layout="wide")

# --- 1. Database Setup ---
def init_db():
    conn = sqlite3.connect('medical_reports.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS reports 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_name TEXT, test_date TEXT, summary TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# --- 2. AI Analysis Functions (မြန်မာ/အင်္ဂလိပ် နှစ်ဘာသာဖြင့် ထွက်ရန်) ---
def analyze_report(image_bytes):
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    prompt = """
    Analyze this medical report image. 
    Return a valid JSON object with these exact keys:
    - "patient_name": (string)
    - "test_date": (string)
    - "summary": (string, Write a comprehensive summary in both English and Myanmar language. Format: [English Summary] \n\n [မြန်မာဘာသာဖြင့် အနှစ်ချုပ်])
    - "abnormal_findings": (list of strings, include both English and Myanmar translations)
    - "recommendations": (list of strings, include both English and Myanmar translations)
    """
    
    response = client.chat.completions.create(
        model="qwen/qwen3.6-27b",
        messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

# --- 3. PDF Generation Function (Pyidaungsu Font & နှစ်ဘာသာ ပါဝင်ရန်) ---
def create_pdf(p_name, t_date, sum_text, abnormal, recs):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    try:
        pdfmetrics.registerFont(TTFont('Pyidaungsu', 'Pyidaungsu.ttf'))
        font = 'Pyidaungsu'
    except:
        font = 'Helvetica'
    
    # ခေါင်းစဉ်
    c.setFont(font, 14)
    c.drawString(50, height - 50, "Medical Report Summary (English & Myanmar)")
    
    # လူနာအချက်အလက်
    c.setFont(font, 11)
    c.drawString(50, height - 80, f"Patient Name: {p_name}")
    c.drawString(50, height - 100, f"Test Date: {t_date}")
    
    c.setFont(font, 12)
    c.drawString(50, height - 130, "Summary (အနှစ်ချုပ်):")
    
    # စာသားများ PDF ထဲတွင် အဆင်ပြေစေရန် wrap လုပ်ခြင်း
    y_position = height - 150
    c.setFont(font, 10)
    
    wrapper = textwrap.TextWrapper(width=85)
    lines = wrapper.wrap(text=sum_text)
    
    for line in lines:
        if y_position < 50:
            c.showPage()
            c.setFont(font, 10)
            y_position = height - 50
        c.drawString(50, y_position, line)
        y_position -= 15
        
    c.save()
    buffer.seek(0)
    return buffer

# --- 4. Streamlit UI ---
st.title("🏥 AI Medical Assistant & Summarizer")

if "messages" not in st.session_state:
    st.session_state.messages = []

uploaded_file = st.file_uploader("ဆေးစာရွက်တင်ရန် (Upload Report)", type=["jpg", "png", "pdf"])

col1, col2 = st.columns([1, 1])

with col1:
    if uploaded_file:
        st.image(uploaded_file, caption="Uploaded Report", use_container_width=True)
        if st.button("🔍 စစ်ဆေးမည်"):
            with st.spinner("AI စစ်ဆေးနေပါသည်..."):
                res = analyze_report(uploaded_file.getvalue())
                st.session_state.current_report = res
                st.success("Analysis Complete!")
                
                p_name = res.get('patient_name', 'မပါရှိပါ')
                t_date = res.get('test_date', 'မပါရှိပါ')
                sum_text = res.get('summary', 'အနှစ်ချုပ် မရှိပါ။')
                abnormal = res.get('abnormal_findings', [])
                recs = res.get('recommendations', [])
                
                st.write(f"**Patient Name:** {p_name}")
                st.info(sum_text)
                
                # PDF Download Button (နှစ်ဘာသာပါသော summary ဖြင့်)
                pdf_file = create_pdf(p_name, t_date, sum_text, abnormal, recs)
                st.download_button(
                    label="📥 PDF ဖိုင် ရယူရန် (English & Myanmar)",
                    data=pdf_file,
                    file_name=f"Medical_Summary_{p_name}.pdf",
                    mime="application/pdf"
                )

with col2:
    st.subheader("💬 AI နှင့် နှစ်ဘာသာဖြင့် မေးမြန်းဆွေးနွေးရန်")
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    if prompt := st.chat_input("ဆေးစာနဲ့ပတ်သက်ပြီး ဘာမေးချင်ပါသလဲ? (Ask in English or Myanmar)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        with st.chat_message("assistant"):
            context = f"Report Context: {json.dumps(st.session_state.get('current_report', 'No report uploaded'))}"
            full_prompt = f"{context}\n\nUser Question: {prompt}\n\nInstruction: Answer in both English and Myanmar language."
            
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": "You are a helpful medical assistant. Always provide answers in both English and Myanmar language."},
                          {"role": "user", "content": full_prompt}]
            )
            answer = response.choices[0].message.content
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
            
