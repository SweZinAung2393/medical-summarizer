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
st.set_page_config(page_title="AI Medical Assistant", layout="wide")

# --- AI Analysis Function (Model ပြောင်းလဲပြီး Error ကင်းအောင်ပြင်ထားသည်) ---
def analyze_report(image_bytes):
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    
    # JSON ပုံစံဖြင့်သာ ပြန်ဖြေရန် တိုက်တွန်းသည့် Prompt
    prompt = """
    Analyze this medical report. Return ONLY a valid JSON object. Do not add any text outside the JSON.
    Required keys: "patient_name", "test_date", "summary" (English & Myanmar), "abnormal_findings" (list), "recommendations" (list).
    """
    
    # Model ကို llama-3.3-70b-versatile သို့ ပြောင်းသုံးထားသည်
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]}
        ]
    )
    
    content = response.choices[0].message.content.strip()
    # Markdown သန့်စင်ခြင်း
    content = content.replace("```json", "").replace("```", "").strip()
    return json.loads(content)

# --- PDF Generation Function ---
def create_pdf(p_name, t_date, sum_text):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    try:
        pdfmetrics.registerFont(TTFont('Pyidaungsu', 'Pyidaungsu.ttf'))
        font = 'Pyidaungsu'
    except:
        font = 'Helvetica'
    
    c.setFont(font, 14)
    c.drawString(50, height - 50, "Medical Report Summary")
    c.setFont(font, 11)
    c.drawString(50, height - 80, f"Patient: {p_name}")
    c.drawString(50, height - 100, f"Date: {t_date}")
    
    y = height - 140
    c.setFont(font, 10)
    for line in textwrap.wrap(sum_text, 80):
        c.drawString(50, y, line)
        y -= 15
    c.save()
    buffer.seek(0)
    return buffer

# --- Streamlit UI ---
st.title("🏥 AI Medical Assistant")
uploaded_file = st.file_uploader("ဆေးစာရွက်တင်ရန်", type=["jpg", "png", "jpeg"])

if uploaded_file and st.button("စစ်ဆေးမည်"):
    with st.spinner("AI စစ်ဆေးနေပါသည်..."):
        try:
            res = analyze_report(uploaded_file.getvalue())
            st.session_state.current_report = res
            st.success("Analysis Complete!")
            st.info(res.get('summary', ''))
            
            pdf = create_pdf(res.get('patient_name', ''), res.get('test_date', ''), res.get('summary', ''))
            st.download_button("📥 PDF ဒေါင်းလုဒ်ဆွဲရန်", pdf, file_name="report.pdf")
        except Exception as e:
            st.error(f"Error ဖြစ်ပွားသည်: {e}")
    
