import base64
import json
import sqlite3
import streamlit as st
from PIL import Image
from groq import Groq

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
            recommendations TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_report(patient_name, test_date, summary, recommendations):
    conn = sqlite3.connect('medical_reports.db')
    c = conn.cursor()
    rec_str = "||".join(recommendations) if recommendations else ""
    c.execute('''
        INSERT INTO reports (patient_name, test_date, summary, recommendations)
        VALUES (?, ?, ?, ?)
    ''', (patient_name, test_date, summary, rec_str))
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

# --- 2. UI Layout ---
st.title("🏥 AI Medical Report Summarizer & Chatbot")
st.write("မည်သည့် ဆေးစစ်ချက် (သို့မဟုတ်) ကျန်းမာရေးဆိုင်ရာ ဓာတ်ပုံကိုမဆို တင်၍ မြန်မာဘာသာဖြင့် အနှစ်ချုပ် ရယူပါ။")

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

# --- 3. AI Analysis Function ---
def analyze_medical_report(uploaded_file):
    bytes_data = uploaded_file.getvalue()
    base64_image = base64.b64encode(bytes_data).decode("utf-8")
    
    prompt = """
    Analyze the provided medical or health report image. Some fields might be missing depending on the report type. 
    Extract whatever information is available and return ONLY a valid JSON object with these exact keys:
    - "patient_name": (string, use "မပါရှိပါ" if not found)
    - "test_date": (string, use "မပါရှိပါ" if not found)
    - "abnormal_findings": (list of strings describing any abnormal or notable values, in English and explained in Myanmar. If none, return an empty list)
    - "summary": (string, clear overall summary of the report in Myanmar language)
    - "recommendations": (list of strings for medical or lifestyle recommendations in Myanmar. If none, provide general health advice)
    - "is_emergency": (boolean: true if critical/dangerous, otherwise false)
    
    Ensure the output is strictly valid JSON format without any extra text or markdown formatting outside of it.
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
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(chat_completion.choices[0].message.content)

# Session State အတွက် Chat History ထိန်းသိမ်းရန်
if "messages" not in st.session_state:
    st.session_state.messages = []

if "report_context" not in st.session_state:
    st.session_state.report_context = ""

# --- 4. Main App Logic ---
uploaded_file = st.file_uploader("ဆေးစစ်ချက် (သို့မဟုတ်) ကျန်းမာရေး ဓာတ်ပုံ တင်ရန်", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Report Image", use_container_width=True)
    
    if st.button("🔍 AI ဖြင့် စစ်ဆေးမည်", type="primary"):
        with st.spinner("AI စစ်ဆေးနေပါပြီ... ခဏစောင့်ပါ"):
            try:
                res = analyze_medical_report(uploaded_file)
                
                p_name = res.get('patient_name', 'မပါရှိပါ')
                t_date = res.get('test_date', 'မပါရှိပါ')
                sum_text = res.get('summary', 'အနှစ်ချုပ် မပါရှိပါ။')
                recs = res.get('recommendations', [])
                
                # Database ထဲသို့ သိမ်းဆည်းခြင်း
                save_report(p_name, t_date, sum_text, recs)
                
                # Chat အတွက် Context ကို သိမ်းထားခြင်း
                st.session_state.report_context = f"Patient: {p_name}, Date: {t_date}, Summary: {sum_text}, Recommendations: {recs}"
                st.session_state.messages = [] # ပုံအသစ်တင်တိုင်း Chat ကို ရှင်းလင်းရန်
                
                if res.get('is_emergency', False):
                    st.error("🚨 **သတိပေးချက် - အရေးပေါ် အခြေအနေ:** ဤအစီရင်ခံစာတွင် အရေးကြီးသော သို့မဟုတ် ပုံမှန်မဟုတ်သည့် အချက်များ တွေ့ရှိရသဖြင့် ဆရာဝန်နှင့် ချက်ချင်းပြသသင့်ပါသည်။")
                
                st.success("စစ်ဆေးမှု ပြီးစီးပြီး Database ထဲသို့ သိမ်းဆည်းပြီးပါပြီ!")
                
                st.write(f"**👤 လူနာအမည်:** {p_name}")
                st.write(f"**📅 ရက်စွဲ:** {t_date}")
                st.write("---")
                st.write(f"**📝 အနှစ်ချုပ်:**")
                st.info(sum_text)
                
                st.write("**💡 အကြံပြုချက်များနှင့် လမ်းညွှန်ချက်များ:**")
                if recs:
                    for rec in recs:
                        st.markdown(f"- {rec}")
                else:
                    st.markdown("- ကျန်းမာရေးနှင့် ညီညွတ်သော လူနေမှုပုံစံကို ဆက်လက်ထိန်းသိမ်းပါ။")
                
            except Exception as e:
                st.error(f"မှားယွင်းမှု ရှိနေသည် (သို့မဟုတ်) ပုံကို တိုက်ရိုက်ဖတ်၍ မရပါ။ ကျေးဇူးပြု၍ ပုံအသစ် (သို့မဟုတ်) ရှင်းလင်းသော ပုံကို ထပ်တင်ပေးပါ။")

# --- 5. Chat with Medical Report Interface ---
if st.session_state.report_context:
    st.write("---")
    st.subheader("💬 ဤဆေးစာနှင့် ပတ်သက်၍ ထပ်မံမေးမြန်းရန်")
    
    # ရှေ့ဟောင်း မက်ဆေ့ချ်များကို ပြသခြင်း
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
    # အသုံးပြုသူက စာရိုက်၍ မေးမြန်းခြင်း
    if user_query := st.chat_input("ဤဆေးစာနှင့် ပတ်သက်၍ မေးလိုသည်များကို မေးမြန်းပါ..."):
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)
            
        with st.chat_message("assistant"):
            with st.spinner("AI ဖြေကြားနေပါပြီ..."):
                # AI သို့ Context နှင့်အတူ မေးခွန်းပို့ရန်
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
            
