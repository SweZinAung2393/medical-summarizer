import base64
import io
import textwrap
import sqlite3
import re
import streamlit as st
from groq import Groq
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# API Key ကို Streamlit secrets မှ ရယူပါ
client = Groq(api_key=st.secrets["GROQ_API_KEY"])
st.set_page_config(page_title="Medical AI Assistant", layout="centered")

# --- 1. Database Setup ---
def init_db():
    conn = sqlite3.connect('medical_reports.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS reports 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_name TEXT, test_date TEXT, summary TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# --- 2. AI Analysis Function (ပုံ ၁ ပုံတည်း) ---
def analyze_single_image(uploaded_file):
    image_bytes = uploaded_file.getvalue()
    mime_type = uploaded_file.type
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    response = client.chat.completions.create(
        model="qwen/qwen3.6-27b",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "Analyze this medical report. Format: Patient Name: [Name], Test Date: [Date], Summary: [Detail in English & Myanmar]."},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
            ]
        }],
        temperature=0.1
    )
    return response.choices[0].message.content

# --- 3. Streamlit UI ---
st.title("🏥 Medical Report AI Assistant")

uploaded_file = st.file_uploader("ဆေးစာပုံ ၁ ပုံ တင်ပါ", type=["jpg", "jpeg", "png"])

if uploaded_file:
    st.image(uploaded_file, caption="Uploaded Report", use_container_width=True)
    
    if st.button("🔍 AI နှင့် စစ်ဆေးမည်"):
        with st.spinner("စစ်ဆေးနေပါသည်..."):
            try:
                result = analyze_single_image(uploaded_file)
                st.session_state.last_result = result
                st.success("စစ်ဆေးမှု ပြီးဆုံးပါပြီ!")
                st.info(result)
                
                # အချက်အလက်ခွဲထုတ်ရန် (Regex)
                p_name = re.search(r"Patient Name:\s*(.*)", result, re.IGNORECASE)
                t_date = re.search(r"Test Date:\s*(.*)", result, re.IGNORECASE)
                
                name = p_name.group(1) if p_name else "Unknown"
                date = t_date.group(1) if t_date else "Unknown"
                
                # Database သိမ်းခြင်း
                conn = sqlite3.connect('medical_reports.db')
                c = conn.cursor()
                c.execute("INSERT INTO reports (patient_name, test_date, summary) VALUES (?, ?, ?)", (name, date, result))
                conn.commit()
                conn.close()
            except Exception as e:
                st.error(f"Error: {e}")

# --- 4. History Section ---
st.divider()
st.subheader("📜 မှတ်တမ်းများ")
if st.button("Refresh History"):
    st.rerun()

conn = sqlite3.connect('medical_reports.db')
c = conn.cursor()
c.execute("SELECT id, patient_name, test_date, summary FROM reports ORDER BY id DESC LIMIT 5")
rows = c.fetchall()
conn.close()

for row in rows:
    with st.expander(f"လူနာ - {row[1]} ({row[2]})"):
        st.write(row[3])
