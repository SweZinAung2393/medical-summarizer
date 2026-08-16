import base64
import io
import textwrap
import sqlite3
import streamlit as st
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

# --- 2. Helper function to encode image to base64 ---
def encode_image(image_bytes):
    return base64.b64encode(image_bytes).decode('utf-8')

# --- 3. AI Analysis Function ---
def analyze_medical_image(image_bytes, mime_type):
    base64_image = encode_image(image_bytes)
    
    prompt = """
    Analyze this medical report image carefully. Provide the response clearly in the following format:
    
    Patient Name: [လူနာအမည် ဖော်ပြရန်]
    Test Date: [စစ်ဆေးသည့်ရက်စွဲ ဖော်ပြရန်]
    Summary: [English နှင့် မြန်မာ နှစ်ဘာသာဖြင့် အသေးစိတ် အနှစ်ချုပ် ရေးသားပေးပါ]
    """
    
    response = client.chat.completions.create(
        model="qwen/qwen3.6-27b",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}"
                        },
                    },
                ],
            }
        ],
        temperature=0.1
    )
    return response.choices[0].message.content

# --- 4. PDF Generation Function ---
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
    c.drawString(50, height - 50, "Medical Report Summary (English & Myanmar)")
    
    c.setFont(font, 11)
    c.drawString(50, height - 80, f"Patient Name: {p_name}")
    c.drawString(50, height - 100, f"Test Date: {t_date}")
    
    c.setFont(font, 12)
    c.drawString(50, height - 130, "Summary (အနှစ်ချုပ်):")
    
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

# --- 5. Streamlit UI ---
st.title("🏥 AI Medical Assistant & Summarizer")

if "messages" not in st.session_state:
    st.session_state.messages = []

uploaded_file = st.file_uploader("ဆေးစာပုံကို တင်ပါ (Upload Medical Report Image)", type=["jpg", "jpeg", "png"])

col1, col2 = st.columns([1, 1])

with col1:
    if uploaded_file:
        st.image(uploaded_file, caption="Uploaded Report", use_container_width=True)
        if st.button("🔍 စစ်ဆေးမည်"):
            with st.spinner("AI စစ်ဆေးနေပါသည်..."):
                try:
                    image_bytes = uploaded_file.getvalue()
                    mime_type = uploaded_file.type
                    
                    result_text = analyze_medical_image(image_bytes, mime_type)
                    st.session_state.current_report = result_text
                    st.success("Analysis Complete!")
                    
                    st.info(result_text)
                    
                    # Database ထဲသို့ သိမ်းဆည်းခြင်း
                    conn = sqlite3.connect('medical_reports.db')
                    c = conn.cursor()
                    c.execute("INSERT INTO reports (patient_name, test_date, summary) VALUES (?, ?, ?)", 
                              ("Patient", "Unknown", result_text))
                    conn.commit()
                    conn.close()
                    
                    pdf_file = create_pdf("Patient", "Unknown", result_text)
                    st.download_button(
                        label="📥 PDF ဖိုင် ရယူရန် (English & Myanmar)",
                        data=pdf_file,
                        file_name="Medical_Summary.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"AI Analysis Error: {e}")

with col2:
    st.subheader("💬 AI နှင့် နှစ်ဘာသာဖြင့် မေးမြန်းဆွေးနွေးရန်")
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    if prompt := st.chat_input("ဆေးစာနဲ့ပတ်သက်ပြီး ဘာမေးချင်ပါလဲ? (Ask in English or Myanmar)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        with st.chat_message("assistant"):
            context = f"Report Context: {st.session_state.get('current_report', 'No report uploaded')}"
            full_prompt = f"{context}\n\nUser Question: {prompt}\n\nInstruction: Answer in both English and Myanmar language."
            
            response = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=[
                    {"role": "system", "content": "You are a helpful medical assistant. Always provide answers in both English and Myanmar language."},
                    {"role": "user", "content": full_prompt}
                ]
            )
            answer = response.choices[0].message.content
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})

# --- 6. Transaction / History Table View ---
st.divider()
st.subheader("📊 ဆေးစစ်ချက် မှတ်တမ်းဇယား (Transaction & History Logs)")

conn = sqlite3.connect('medical_reports.db')
c = conn.cursor()
c.execute("SELECT id, patient_name, test_date, timestamp, summary FROM reports ORDER BY timestamp DESC")
rows = c.fetchall()
conn.close()

if rows:
    # Search Filter ထည့်သွင်းခြင်း
    search_term = st.text_input("🔍 မှတ်တမ်းများထဲတွင် ရှာဖွေရန် (Search Transactions)")
    
    # Data များကို Table သို့မဟုတ် List ဖြင့် သေသေသပ်သပ် ပြသရန်
    for row in rows:
        # Search လုပ်ထားလျှင် စစ်ဆေးရန်
        if search_term and search_term.lower() not in row[1].lower() and search_term.lower() not in row[3].lower():
            continue
            
        with st.expander(f"🆔 Transaction ID: {row[0]} | ရက်စွဲ: {row[3]}"):
            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.write(f"**Patient Name:** {row[1]}")
                st.write(f"**Test Date:** {row[2]}")
            with col_info2:
                st.write(f"**Saved Time:** {row[3]}")
            
            st.markdown("---")
            st.write(f"**Summary:**\n{row[4]}")
            
            # တစ်ခုချင်းစီအတွက် Delete လုပ်နိုင်သော ခလုတ်
            if st.button(f"🗑️ ဤမှတ်တမ်းကို ဖျက်မည် (ID: {row[0]})", key=f"del_{row[0]}"):
                conn = sqlite3.connect('medical_reports.db')
                c = conn.cursor()
                c.execute("DELETE FROM reports WHERE id = ?", (row[0],))
                conn.commit()
                conn.close()
                st.success(f"Transaction ID {row[0]} ကို ဖျက်ပြီးပါပြီ။")
                st.rerun()
else:
    st.info("ယခုထိ သိမ်းဆည်းထားသော ဆေးစစ်ချက် မှတ်တမ်း (Transactions) မရှိသေးပါ။")
