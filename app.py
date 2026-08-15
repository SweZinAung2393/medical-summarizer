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

    # --- AI Analysis Function (Robust JSON Parsing) ---
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
        
        if raw_content.startswith("```"):
            raw_content = raw_content.split("```")[1]
            if raw_content.startswith("json"):
                raw_content = raw_content[4:]
        raw_content = raw_content.strip()
        
        return json.loads(raw_content)

    # --- PDF Generation Function (Pyidaungsu Font Support) ---
    def create_pdf(p_name, t_date, sum_text, abnormal, recs):
        pdf_buffer = io.BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=letter)
        width, height = letter
        
        try:
            pdfmetrics.registerFont(TTFont('Pyidaungsu', 'Pyidaungsu.ttf'))
            font_name = 'Pyidaungsu'
        except:
            font_name = 'Helvetica'
        
        c.setFont(font_name, 14)
        c.drawString(50, height - 50, "AI Medical Report Summary")
        
        c.setFont(font_name, 11)
        c.drawString(50, height - 80, f"Patient Name: {p_name}")
        c.drawString(50, height - 100, f"Test Date: {t_date}")
        
        c.setFont(font_name, 12)
        c.drawString(50, height - 130, "Summary:")
        
        text_object = c.beginText(50, height - 150)
        text_object.setFont(font_name, 10)
        
        for line in sum_text.split('\n'):
            text_object.textLine(line)
        c.drawText(text_object)
        
        c.save()
        pdf_buffer.seek(0)
        return pdf_buffer

    # Session State
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "report_context" not in st.session_state:
        st.session_state.report_context = ""

    # --- Main App Logic ---
    uploaded_file = st.file_uploader("ဆေးစစ်ချက် (ပုံ သို့မဟုတ် PDF) တင်ရန်", type=["jpg", "jpeg", "png", "pdf"])

    image_bytes = None

    if uploaded_file is not None:
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        if file_extension == 'pdf':
            with st.spinner("PDF ကို ပုံအဖြစ် ပြောင်းနေပါပြီ..."):
                pdf_bytes = uploaded_file.getvalue()
                images = convert_from_bytes(pdf_bytes)
                if images:
                    image_bytes_io = io.BytesIO()
                    images[0].save(image_bytes_io, format='JPEG')
                    image_bytes = image_bytes_io.getvalue()
                    st.image(images[0], caption="Uploaded PDF First Page", use_container_width=True)
        else:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Report Image", use_container_width=True)
            image_bytes = uploaded_file.getvalue()
        
        if image_bytes and st.button("🔍 AI ဖြင့် စစ်ဆေးမည်", type="primary"):
            with st.spinner("AI စစ်ဆေးနေပါပြီ... ခဏစောင့်ပါ"):
                try:
                    res = analyze_medical_report(image_bytes)
                    
                    p_name = res.get('patient_name', 'မပါရှိပါ')
                    t_date = res.get('test_date', 'မပါရှိပါ')
                    sum_text = res.get('summary', 'အနှစ်ချုပ် မပါရှိပါ။')
                    abnormal = res.get('abnormal_findings', [])
                    recs = res.get('recommendations', [])
                    
                    save_report(p_name, t_date, sum_text, abnormal, recs)
                    
                    st.session_state.report_context = f"Patient: {p_name}, Date: {t_date}, Summary: {sum_text}, Abnormal Findings: {abnormal}, Recommendations: {recs}"
                    st.session_state.messages = []
                    
                    if res.get('is_emergency', False):
                        st.error("🚨 **သတိပေးချက် - အရေးပေါ် အခြေအနေ:** ဤအစီရင်ခံစာတွင် အရေးကြီးသော သို့မဟုတ် ပုံမှန်မဟုတ်သည့် အချက်များ တွေ့ရှိရသဖြင့် ဆရာဝန်နှင့် ချက်ချင်းပြသသင့်ပါသည်။")
                    
                    st.success("စစ်ဆေးမှု ပြီးစီးပြီး Database ထဲသို့ အောင်မြင်စွာ သိမ်းဆည်းပြီးပါပြီ!")
                    
                    st.write(f"**👤 လူနာအမည်:** {p_name}")
                    st.write(f"**📅 ရက်စွဲ:** {t_date}")
                    st.write("---")
                    st.write(f"**📝 အနှစ်ချုပ်:**")
                    st.info(sum_text)
                    
                    if abnormal:
                        st.write("**⚠️ ပုံမှန်မဟုတ်သော အချက်များ (Abnormal Findings):**")
                        for ab in abnormal:
                            st.markdown(f"- {ab}")
                    
                    st.write("**💡 အကြံပြုချက်များနှင့် လမ်းညွှန်ချက်များ:**")
                    if recs:
                        for rec in recs:
                            st.markdown(f"- {rec}")
                    else:
                        st.markdown("- ကျန်းမာရေးနှင့် ညီညွတ်သော လူနေမှုပုံစံကို ဆက်လက်ထိန်းသိမ်းပါ။")
                    
                    pdf_file = create_pdf(p_name, t_date, sum_text, abnormal, recs)
                    st.download_button(
                        label="📥 အနှစ်ချုပ်ကို PDF ဖြင့် Download ဆွဲရန်",
                        data=pdf_file,
                        file_name=f"Medical_Summary_{p_name}.pdf",
                        mime="application/pdf"
                    )
                    
                except Exception as e:
                    st.error(f"မှားယွင်းမှု ရှိနေသည် (သို့မဟုတ်) ပုံ/ဖိုင်ကို ဖတ်၍ မရပါ။ (Error: {e})")

    # --- Chat Interface ---
    if st.session_state.report_context:
        st.write("---")
        st.subheader("💬 ဤဆေးစာနှင့် ပတ်သက်၍ ထပ်မံမေးမြန်းရန်")
        
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
        if user_query := st.chat_input("ဤဆေးစာနှင့် ပတ်သက်၍ မေးလိုသည်များကို မေးမြန်းပါ..."):
            st.session_state.messages.append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.markdown(user_query)
                
            with st.chat_message("assistant"):
                with st.spinner("AI ဖြေကြားနေပါပြီ..."):
                    chat_prompt = f"""
                    You are a helpful medical assistant. Based on the following medical report context, answer the user's question clearly in Myanmar language.
                    
                    Medical Report Context:
                    {st.session_state.report_context}
                    
                    User Question: {user_query}
                    """
                    
                    chat_completion = client.chat.completions.create(
                        model="qwen/qwen3.6-27b",
                        messages=[{"role": "user", "content": chat_prompt}]
                    )
                    ai_response = chat_completion.choices[0].message.content
                    st.markdown(ai_response)
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})

with tab2:
    st.header("📚 ဆေးပညာ ဝေါဟာရ အဘိဓာန် (Medical Dictionary)")
    st.write("ဆေးစာများတွင် တွေ့ရလေ့ရှိသော ခက်ခဲသည့် ဝေါဟာရများနှင့် အဓိပ္ပာယ်များကို ဤနေရာတွင် ရှာဖွေဖတ်ရှုနိုင်ပါသည်။")
    
    search_term = st.text_input("🔍 ရှာဖွေလိုသော ဆေးပညာ ဝေါဟာရကို ရိုက်ထည့်ပါ (ဥပမာ - Hypertension):")
    
    filtered_dict = {k: v for k, v in medical_dictionary.items() if search_term.lower() in k.lower() or search_term.lower() in v.lower()}
    
    st.markdown("---")
    
    for term, meaning in filtered_dict.items():
        st.markdown(f"### 🔹 {term}")
        st.info(meaning)
    
    if not filtered_dict:
        st.warning("ရှာဖွေနေသော ဝေါဟာရ မရှိသေးပါ။")
        
