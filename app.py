import base64
import json
import sqlite3
import io
import streamlit as st
from PIL import Image
from groq import Groq
from pdf2image import convert_from_bytes
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Streamlit Secrets မှ Groq API Key ကို ယူသုံးခြင်း
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

st.set_page_config(page_title="AI Medical Report Summarizer", layout="wide")

# --- 1. Database Setup ---
def init_db():
    conn = sqlite3.connect('medical_reports.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT,
            test_date TEXT,
            summary TEXT,
            abnormal_findings TEXT,
            recommendations TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_report(patient_name, test_date, summary, abnormal_findings, recommendations):
    conn = sqlite3.connect('medical_reports.db')
    c = conn.cursor()
    abnormal_str = "||".join(abnormal_findings) if abnormal_findings else ""
    rec_str = "||".join(recommendations) if recommendations else ""
    c.execute('''
        INSERT INTO reports (patient_name, test_date, summary, abnormal_findings, recommendations)
        VALUES (?, ?, ?, ?, ?)
    ''', (patient_name, test_date, summary, abnormal_str, rec_str))
    conn.commit()
    conn.close()

init_db()

# --- 2. AI Analysis Function ---
def analyze_medical_report(image_bytes):
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    
    # Prompt ကို triple quotes (''') သုံးပြီး အမှားမဖြစ်အောင် ရေးထားသည်
    prompt = '''
    Analyze the provided medical report image. Return ONLY a valid JSON object with these keys:
    "patient_name", "test_date", "abnormal_findings" (list), "summary", "recommendations" (list), "is_emergency" (boolean).
    Ensure the summary is in Myanmar language.
    '''
    
    chat_completion = client.chat.completions.create(
        model="qwen/qwen3.6-27b",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                ],
            }
        ]
    )
    
    content = chat_completion.choices[0].message.content.strip()
    # Markdown ဖယ်ရှားခြင်း
    content = content.replace("```json", "").replace("```", "").strip()
    return json.loads(content)

# --- 3. PDF Function ---
def create_pdf(p_name, t_date, sum_text, abnormal, recs):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    try:
        pdfmetrics.registerFont(TTFont('Pyidaungsu', 'Pyidaungsu.ttf'))
        font = 'Pyidaungsu'
    except:
        font = 'Helvetica'
    
    c.setFont(font, 14)
    c.drawString(50, 750, "AI Medical Report Summary")
    c.setFont(font, 12)
    c.drawString(50, 720, f"Patient: {p_name}")
    c.drawString(50, 700, f"Date: {t_date}")
    
    text = c.beginText(50, 670)
    text.setFont(font, 11)
    text.textLines(sum_text)
    c.drawText(text)
    c.save()
    buffer.seek(0)
    return buffer

# --- 4. Streamlit UI ---
st.title("🏥 AI Medical Report Summarizer")
uploaded_file = st.file_uploader("Upload Report", type=["jpg", "png", "pdf"])

if uploaded_file:
    image_bytes = uploaded_file.getvalue()
    if st.button("🔍 စစ်ဆေးမည်"):
        with st.spinner("Processing..."):
            try:
                res = analyze_medical_report(image_bytes)
                st.success("အောင်မြင်ပါသည်။")
                st.write(f"**အမည်:** {res.get('patient_name')}")
                st.info(res.get('summary'))
                
                pdf_file = create_pdf(res.get('patient_name'), res.get('test_date'), 
                                      res.get('summary'), res.get('abnormal_findings'), res.get('recommendations'))
                
                st.download_button("📥 PDF ဒေါင်းလုဒ်ဆွဲရန်", pdf_file, file_name="report.pdf")
            except Exception as e:
                st.error(f"Error ဖြစ်နေသည်: {e}")
                
