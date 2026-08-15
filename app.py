import base64
import json
import sqlite3
import io
import streamlit as st
from PIL import Image
from groq import Groq
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

client = Groq(api_key=st.secrets["GROQ_API_KEY"])
st.set_page_config(page_title="AI Medical Assistant", layout="wide")

# --- 1. Database Setup ---
def init_db():
    conn = sqlite3.connect('medical_reports.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS reports 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_name TEXT, test_date TEXT, summary TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# --- 2. AI Analysis Functions ---
def analyze_report(image_bytes):
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    prompt = "Analyze this medical report and return JSON with keys: patient_name, test_date, summary, abnormal_findings, recommendations."
    
    response = client.chat.completions.create(
        model="qwen/qwen3.6-27b",
        messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

# --- 3. PDF Generation Function (Pyidaungsu Font Support) ---
def create_pdf(p_name, t_date, sum_text):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    # Pyidaungsu ဖောင့် မှတ်ပုံတင်ခြင်း
    try:
        pdfmetrics.registerFont(TTFont('Pyidaungsu', 'Pyidaungsu.ttf'))
        font = 'Pyidaungsu'
    except:
        font = 'Helvetica'
    
    c.setFont(font, 14)
    c.drawString(50, 750, "AI Medical Report Summary")
    c.setFont(font, 11)
    c.drawString(50, 720, f"Patient Name: {p_name}")
    c.drawString(50, 700, f"Test Date: {t_date}")
    
    text = c.beginText(50, 660)
    text.setFont(font, 10)
    for line in sum_text.split('\n'):
        text.textLine(line)
    c.drawText(text)
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
        if st.button("စစ်ဆေးမည်"):
            with st.spinner("AI စစ်ဆေးနေပါသည်..."):
                res = analyze_report(uploaded_file.getvalue())
                st.session_state.current_report = res
                st.success("Analysis Complete!")
                
                p_name = res.get('patient_name', 'မပါရှိပါ')
                t_date = res.get('test_date', 'မပါရှိပါ')
                sum_text = res.get('summary', 'အနှစ်ချုပ် မရှိပါ။')
                
                st.write(f"**Patient:** {p_name}")
                st.info(sum_text)
                
                # PDF Download Button with Pyidaungsu Font
                pdf_file = create_pdf(p_name, t_date, sum_text)
                st.download_button(
                    label="📥 PDF ဒေါင်းလုဒ်ဆွဲရန်",
                    data=pdf_file,
                    file_name=f"Medical_Summary_{p_name}.pdf",
                    mime="application/pdf"
                )

with col2:
    st.subheader("💬 AI နှင့် မေးမြန်းဆွေးနွေးရန်")
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    if prompt := st.chat_input("ဆေးစာနဲ့ပတ်သက်ပြီး ဘာမေးချင်ပါသလဲ?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        with st.chat_message("assistant"):
            context = f"Report Context: {json.dumps(st.session_state.get('current_report', 'No report uploaded'))}"
            full_prompt = f"{context}\n\nUser Question: {prompt}"
            
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": "You are a helpful medical assistant. Answer in Myanmar language."},
                          {"role": "user", "content": full_prompt}]
            )
            answer = response.choices[0].message.content
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
    
