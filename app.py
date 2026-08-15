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

# --- 2. Helper functions ---
def encode_image(image_bytes):
    return base64.b64encode(image_bytes).decode('utf-8')

def extract_info_from_text(text):
    p_name = "Unknown"
    t_date = "Unknown"
    
    name_match = re.search(r"Patient Name:\s*(.*)", text, re.IGNORECASE)
    if name_match:
        p_name = name_match.group(1).strip()
        
    date_match = re.search(r"Test Date:\s*(.*)", text, re.IGNORECASE)
    if date_match:
        t_date = date_match.group(1).strip()
        
    return p_name, t_date

# --- 3. AI Analysis Function (ပုံ ၁၀ ခုအထိ တစ်ပြိုင်နက် စစ်ဆေးရန်) ---
def analyze_medical_images(image_files):
    content_list = [
        {"type": "text", "text": "Analyze these medical report images carefully. Provide the response clearly in the following format:\n\nPatient Name: [လူနာအမည် ဖော်ပြရန်]\nTest Date: [စစ်ဆေးသည့်ရက်စွဲ ဖော်ပြရန်]\nSummary: [English နှင့် မြန်မာ နှစ်ဘာသာဖြင့် အသေးစိတ် အနှစ်ချုပ် ရေးသားပေးပါ]"}
    ]
    
    for uploaded_file in image_files:
        image_bytes = uploaded_file.getvalue()
        mime_type = uploaded_file.type
        base64_image = encode_image(image_bytes)
        content_list.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{base64_image}"
            }
        })
    
    response = client.chat.completions.create(
        model="qwen/qwen3.6-27b",
        messages=[{"role": "user", "content": content_list}],
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

# အများဆုံး ပုံ (၁၀) ခုအထိ တင်နိုင်ရန် accept_multiple_files=True သုံးထားပါသည်
uploaded_files = st.file_uploader("ဆေးစာပုံများကို တင်ပါ (အများဆုံး ပုံ ၁၀ ခုအထိ)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

col1, col2 = st.columns([1, 1])

with col1:
    if uploaded_files:
        st.write(f"တင်ထားသော ပုံအရေအတွက်: **{len(uploaded_files)} / 10**")
        
        if len(uploaded_files) > 10:
            st.warning("⚠️ ပုံ ၁၀ ခုထက် ပို၍ မတင်ပါနှင့်။ ပထမဆုံး ပုံ ၁၀ ခုကိုသာ စစ်ဆေးပေးပါမည်။")
            uploaded_files = uploaded_files[:10]
            
        for img in uploaded_files:
            st.image(img, caption=img.name, use_container_width=True)
            
        if st.button("🔍 ပုံများကို စစ်ဆေးမည်"):
            with st.spinner("AI စစ်ဆေးနေပါသည်..."):
                try:
                    result_text = analyze_medical_images(uploaded_files)
                    st.session_state.current_report = result_text
                    
                    extracted_name, extracted_date = extract_info_from_text(result_text)
                    
                    st.success("Analysis Complete!")
                    st.info(result_text)
                    
                    # Database ထဲသို့ သိမ်းဆည်းခြင်း
                    conn = sqlite3.connect('medical_reports.db')
                    c = conn.cursor()
                    c.execute("INSERT INTO reports (patient_name, test_date, summary) VALUES (?, ?, ?)", 
                              (extracted_name, extracted_date, result_text))
                    conn.commit()
                    conn.close()
                    
                    pdf_file = create_pdf(extracted_name, extracted_date, result_text)
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
            
    if prompt := st.chat_input("ဆေးစာနဲ့ပတ်သက်ပြီး ဘာမေးချင်ပါသလဲ? (Ask in English or Myanmar)"):
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

# --- 6. Main Page History / Transactions View (Search & Delete ပါဝင်သည်) ---
st.divider()
st.subheader("📜 ယခင်စစ်ဆေးခဲ့သော မှတ်တမ်းများ (History & Search)")

search_query = st.text_input("🔍 လူနာအမည် (သို့မဟုတ်) ရက်စွဲဖြင့် ရှာဖွေရန် (Search History)")

conn = sqlite3.connect('medical_reports.db')
c = conn.cursor()

if search_query:
    c.execute("SELECT id, patient_name, test_date, timestamp, summary FROM reports WHERE patient_name LIKE ? OR test_date LIKE ? ORDER BY timestamp DESC", 
              ('%' + search_query + '%', '%' + search_query + '%'))
else:
    c.execute("SELECT id, patient_name, test_date, timestamp, summary FROM reports ORDER BY timestamp DESC")

rows = c.fetchall()
conn.close()

if rows:
    for row in rows:
        cols = st.columns([6, 1])
        with cols[0]:
            with st.expander(f"ID: {row[0]} | လူနာ: {row[1]} | ရက်စွဲ: {row[2]}"):
                st.write(f"**Test Date:** {row[2]}")
                st.write(f"**Saved Time:** {row[3]}")
                st.write(f"**Summary:**\n{row[4]}")
        with cols[1]:
            if st.button("🗑️ ဖျက်မည်", key=f"del_{row[0]}"):
                conn = sqlite3.connect('medical_reports.db')
                c = conn.cursor()
                c.execute("DELETE FROM reports WHERE id = ?", (row[0],))
                conn.commit()
                conn.close()
                st.success(f"ID {row[0]} မှတ်တမ်းကို ဖျက်ပြီးပါပြီ။")
                st.rerun()
else:
    st.info("ရှာတွေ့သော မှတ်တမ်း မရှိပါ။")
