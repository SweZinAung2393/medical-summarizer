import streamlit as st
from groq import Groq
import base64
import sqlite3
import pandas as pd
from datetime import datetime
import io
from PIL import Image

# Streamlit Page Config
st.set_page_config(page_title="Pro AI Skincare System (Myanmar)", layout="wide")

# API Key - သင့် Groq API Key ကို ထည့်ပါ
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# Database Initialization
def init_db():
    conn = sqlite3.connect('pro_skincare.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, fullname TEXT)')
    cursor.execute('''CREATE TABLE IF NOT EXISTS consultations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, user_name TEXT, skin_type TEXT, 
                        allergies TEXT, budget TEXT, recommendations TEXT, timestamp TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS routine_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_name TEXT, routine_type TEXT, completed_date TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS skin_gallery (id INTEGER PRIMARY KEY AUTOINCREMENT, user_name TEXT, image_blob BLOB, note TEXT, upload_date TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS lifestyle_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_name TEXT, water_intake REAL, sleep_hours REAL, log_date TEXT)''')
    conn.commit()
    conn.close()

init_db()

# Login State
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Pro AI Skincare System - ဝင်ရောက်ရန်")
    user = st.text_input("အသုံးပြုသူအမည်")
    pw = st.text_input("စကားဝှက်", type="password")
    if st.button("Login"):
        st.session_state.logged_in = True
        st.session_state.username = user
        st.rerun()
    st.stop()

# Sidebar
st.sidebar.write(f"👤 အသုံးပြုသူ: **{st.session_state.username}**")
skin_type_input = st.sidebar.selectbox("အသားအရေအမျိုးအစား", ["Oily", "Dry", "Combination", "Acne-Prone", "Sensitive"])
allergies = st.sidebar.text_input("မတည့်သော ပစ္စည်းများ (ရှောင်ရန်)", value="Alcohol, Fragrance")
budget_option = st.sidebar.selectbox("ဘတ်ဂျက်", ["Affordable", "Mid-range", "High-end"])

# Tabs
tabs = st.tabs(["🔍 အသားအရေ စစ်ဆေးရန်", "🏷️ ပစ္စည်းများ စစ်ဆေးခြင်း", "📝 အသားအရေ စစ်တမ်း", "☀️ Routine", "📸 ဓာတ်ပုံမှတ်တမ်း", "💧 လူနေမှုပုံစံ", "📊 မှတ်တမ်း", "📖 အချက်အလက်", "🤖 AI အဆင့်မြင့်", "💬 AI Chatbot", "🇲🇲 ရာသီဥတုအကြံပြုချက်"])

with tabs[0]:
    st.subheader("၁။ အသားအရေ စစ်ဆေးမှုနှင့် မြန်မာဈေးကွက် အကြံပြုချက်")
    uploaded_file = st.file_uploader("မျက်နှာပုံ တင်ပါ", type=["jpg", "png"])
    if uploaded_file and st.button("စစ်ဆေးမှု ပြီးစီးပါပြီ"):
        with st.spinner("AI စစ်ဆေးနေပါပြီ..."):
            base64_image = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
            prompt = f"""
            You are an expert dermatologist in Myanmar. Analyze the image strictly in Burmese language.
            Constraints: Skin Type: {skin_type_input}, Avoid: {allergies}, Budget: {budget_option}.
            Structure your response in Burmese:
            1. အမှတ်ပေးစနစ် (ACNE_SCORE: 1-10, DARK_SPOT_SCORE: 1-10, HYDRATION_SCORE: 1-10)
            2. အသားအရေ ခွဲခြမ်းစိတ်ဖြာချက် (အသေးစိတ် မြန်မာလို)
            3. နေ့စဉ်သုံးရမည့် Skincare Routine (မနက်/ည - မြန်မာလို)
            4. ပစ္စည်းအကြံပြုချက်နှင့် မြန်မာနိုင်ငံအတွင်း ဝယ်နိုင်သောနေရာများ (ဈေးနှုန်းနှင့်အတူ မြန်မာလို)
            """
            response = client.chat.completions.create(model="qwen/qwen3.6-27b", messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}])
            st.markdown(response.choices[0].message.content)

with tabs[1]:
    st.subheader("၂။ ပစ္စည်းပါဝင်ပစ္စည်းများ စစ်ဆေးခြင်း")
    st.write("အလှကုန်ဘူးကို ပုံရိုက်ပြီး တင်ပေးပါ။ AI က မြန်မာလို စစ်ဆေးပေးပါမယ်။")

with tabs[8]:
    st.subheader("🤖 AI အဆင့်မြင့် လုပ်ဆောင်ချက်များ")
    task = st.selectbox("လုပ်ဆောင်ချက် ရွေးပါ", ["Natural Mask ဖော်စပ်နည်း", "Skincare ဓာတ်ပြုမှု စစ်ဆေးခြင်း"])
    user_q = st.text_input("မေးခွန်းရိုက်ထည့်ပါ")
    if st.button("AI ထံမှ အကြံဉာဏ်ရယူရန်"):
        res = client.chat.completions.create(model="qwen/qwen3.6-27b", messages=[{"role": "user", "content": f"Answer in Burmese: {task} - {user_q}"}])
        st.markdown(res.choices[0].message.content)

with tabs[9]:
    st.subheader("💬 AI Beauty Chatbot (မြန်မာလို မေးပါ)")
    q = st.text_input("အလှအပရေးရာ မေးမြန်းရန်")
    if st.button("မေးရန်"):
        res = client.chat.completions.create(model="qwen/qwen3.6-27b", messages=[{"role": "user", "content": f"မြန်မာလို ဖြေပေးပါ: {q}"}])
        st.markdown(res.choices[0].message.content)

with tabs[10]:
    st.subheader("🇲🇲 မြန်မာနိုင်ငံ ရာသီဥတုအတွက် အကြံပြုချက်")
    st.write("မြန်မာနိုင်ငံ၏ ပူပြင်းစွတ်စိုသော ရာသီဥတုတွင် Gel-based moisturizer သုံးရန်နှင့် နေရောင်ကာကွယ်ဆေး SPF 50 ကို နေ့စဉ်သုံးရန် အထူးအကြံပြုပါသည်။")    
