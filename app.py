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

def get_report_history():
    conn = sqlite3.connect('medical_reports.db')
    c = conn.cursor()
    c.execute('SELECT patient_name, test_date, summary, timestamp FROM reports ORDER BY timestamp DESC')
    data = c.fetchall()
    conn.close()
    return data

init_db()

# --- 2. Medical Dictionary Data (ဆေးပညာ ဝေါဟာရ အဘိဓာန်) ---
medical_dictionary = {
    "Hypertension": "သွေးတိုးရောဂါ (သွေးလွှတ်ကြောများအတွင်း သွေးဖိအား ပုံမှန်ထက် မြင့်တက်နေခြင်း)",
    "Diabetes Mellitus": "ဆီးချိုရောဂါ (သွေးတွင်းသကြားဓာတ် ပမာဏ စည်းချက်မမှန်ဘဲ မြင့်မားနေခြင်း)",
    "Cholesterol": "သွေးတွင်းအဆီဓာတ် တစ်မျိုးဖြစ်ပြီး ပမာဏများပါက နှလုံးရောဂါ ဖြစ်ပွားနိုင်ချေ ရှိသည်။",
    "Anemia": "သွေးအားနည်းရောဂါ (ခန္ဓာကိုယ်တွင် အောက်ဆီဂျင် သယ်ဆောင်ပေးသည့် သွေးနီဥ ပမာဏ နည်းပါးခြင်း)",
    "Gastritis": "အစာအဟောင်းအိမ် ရောင်ရမ်းခြင်း (အစာအိမ်နံရံ ရောင်ရမ်းခြင်းကြောင့် ပچပچစက်စက် ဖြစ်ခြင်း)",
    "Arthritis": "အဆစ်အမြစ် ရောင်ရမ်းကိုက်ခဲသော ရောဂါ",
    "ECG / EKG": "နှလုံးလျှပ်စစ်စစ်ဆေးမှု (နှလုံးခုန်နှုန်းနှင့် စည်းချက်ကို စစ်ဆေးခြင်း)",
    "Ultrasound": "အသံလှိုင်းအသုံးပြု၍ ကိုယ်တွင်းအင်္ဂါများကို ကြည့်ရှုစစ်ဆေးခြင်း",
    "Biopsy": "ရောဂါရှာဖွေရန်အတွက် တစ်ရှူးနမူနာရယူ စစ်ဆေးခြင်း",
    "Benign": "အန္တရာယ်မရှိသော (ကင်ဆာမဟုတ်သော အကျိတ်)"
}

# --- 3. UI Layout & Navigation Tabs ---
st.title("🏥 AI Medical Report Summarizer & Dictionary")

tab1, tab2 = st.tabs(["📄 ဆေးစစ်ချက် စစ်ဆေးရန်", "📚 ဆေးပညာ ဝေါဟာရ အဘိဓာန်"])

with tab1:
    st.write("မည်သည့် ဆေးစစ်ချက် (ပုံ သို့မဟုတ် PDF) ကိုမဆို တင်၍ မြန်မာဘာသာဖြင့် အနှစ်ချုပ် ရယူပါ။")

    # Sidebar - မှတ်တမ်းဟောင်းများ ကြည့်ရန်
    st.sidebar.header("📂 ရှေ့ဟောင်း မှတ်တမ်းများ (History)")
    if st.sidebar.button("မှတ်တမ်းများ ပြန်ပြရန်"):
        history = get_report_history()
        if history:
            for idx, item in enumerate(history, 1):
                st.sidebar.markdown(f"**{idx}. လူနာ:** {item[0]} ({item[1]})")
                st.sidebar.caption(f"အချိန်: {item[3]}")
                st.sidebar.write(f"အနှစ်ချုပ်: {item[2][:50]}...")
                st.sidebar.markdown("---")
        else:
            st.sidebar.write("သိမ်းဆည်းထားသော မှတ်တမ်း မရှိသေးပါ။")

    # --- AI Analysis Function (Robust JSON Parsing & Fallback) ---
    def analyze_medical_report(image_bytes):
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        
        prompt = """
        Analyze the provided medical or health report image. Extract the information and return ONLY a valid JSON object (do not include any markdown formatting like ```json ... ```) with these exact keys:
        - "patient_name": (string, use "မပါရှိပါ" if not found)
        - "test_date": (string, use "မပါရှိပါ" if not found)
        - "abnormal_findings": (list of strings describing any abnormal or notable values, in English and explained in Myanmar. If none, return an empty list)
        - "summary": (string, clear overall summary of the report in Myanmar language)
        - "recommendations": (list of strings for medical or lifestyle recommendations in Myanmar. If none, provide general health advice)
        - "is_emergency": (boolean: true if critical/dangerous, otherwise false)
        """
        
        chat_completion = client.chat.completions.create(
            model="qwen/qwen3.6-27b",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ]
        )
        
        raw_content = chat_completion.choices[0].message.content.strip()
        
        if not raw_content:
            raise Exception("AI မှ တုံ့ပြန်ချက် အလွတ်သာ ပို့လာပါသည်။ ကျေးဇူးပြု၍ ခဏနေမှ ထပ်ကြိုးစားပါ။")
        
        if raw_content.startswith("```"):
            raw_content = raw_content.split("
