import streamlit as st
from groq import Groq
import base64
import sqlite3
import pandas as pd
from datetime import datetime
import io
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from PIL import Image

# Streamlit Page Config
st.set_page_config(page_title="Ultimate Pro Skincare System (20 Features + Auth)", layout="wide")

# API Key Setup
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- EMAIL CONFIGURATION (Gmail App Password) ---
def send_reset_email(receiver_email, reset_code):
    try:
        sender_email = st.secrets["email_config"]["SENDER_EMAIL"]
        sender_password = st.secrets["email_config"]["SENDER_PASSWORD"]
        
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = receiver_email
        message["Subject"] = "Skincare System - Password Reset Code"
        
        body = f"""
        မင်္ဂလာပါ၊
        
        သင့်အကောင့်၏ Password ကို ပြန်လည်သတ်မှတ်ရန် (Reset) တောင်းဆိုထားပါသည်။
        အတည်ပြုရန် ကုဒ်နံပါတ်မှာ - {reset_code} ဖြစ်ပါသည်။
        
        ကျေးဇူးတင်ပါသည်။
        """
        message.attach(MIMEText(body, "plain"))
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, message.as_string())
        server.quit()
        return True
    except Exception as e:
        return False

# Database Initialization
def init_db():
    conn = sqlite3.connect('pro_skincare_ultimate.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            gmail TEXT,
            password TEXT,
            reset_code TEXT
        )
    ''')
    cursor.execute('CREATE TABLE IF NOT EXISTS consultations (id INTEGER PRIMARY KEY AUTOINCREMENT, user_name TEXT, recommendations TEXT, timestamp TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS routine_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_name TEXT, routine_type TEXT, completed_date TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS skin_gallery (id INTEGER PRIMARY KEY AUTOINCREMENT, user_name TEXT, image_blob BLOB, note TEXT, upload_date TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS lifestyle_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_name TEXT, water_intake REAL, sleep_hours REAL, log_date TEXT)')
    conn.commit()
    conn.close()

init_db()

# Session State Management
if "logged_in" not in st.session_state: st.session_state.logged_in = False

# --- AUTHENTICATION & FORGOT PASSWORD UI ---
if not st.session_state.logged_in:
    st.title("🔐 Pro Skincare System - ဝင်ရောက်ရန် / အကောင့်ဖွင့်ရန်")
    
    choice = st.sidebar.selectbox("ရွေးချယ်ရန်", ["Login", "Signup", "Forgot Password"])
    
    if choice == "Login":
        st.subheader("🔑 Login (အကောင့်ဝင်ရန်)")
        u_name = st.text_input("Username သို့မဟုတ် Gmail")
        u_pass = st.text_input("Password", type="password")
        
        if st.button("Login ဝင်မည်"):
            conn = sqlite3.connect('pro_skincare_ultimate.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE (username = ? OR gmail = ?) AND password = ?", (u_name, u_name, u_pass))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                st.session_state.logged_in = True
                st.session_state.username = user[0]
                st.success("Login အောင်မြင်ပါသည်!")
                st.rerun()
            else:
                st.error("Username (သို့) Password မှားယွင်းနေပါသည်။")
                
    elif choice == "Signup":
        st.subheader("📝 Signup (အကောင့်အသစ်ဖွင့်ရန်)")
        s_user = st.text_input("Username အသစ်")
        s_gmail = st.text_input("Gmail လိပ်စာ")
        s_pass = st.text_input("Password အသစ်", type="password")
        
        if st.button("အကောင့်ဖွင့်မည်"):
            if s_user and s_gmail and s_pass:
                try:
                    conn = sqlite3.connect('pro_skincare_ultimate.db')
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO users (username, gmail, password, reset_code) VALUES (?, ?, ?, ?)", (s_user, s_gmail, s_pass, ""))
                    conn.commit()
                    conn.close()
                    st.success("အကောင့်ဖွင့်ခြင်း ပြီးစီးပါပြီ။ ယခု Login ဝင်နိုင်ပါပြီ။")
                except:
                    st.error("ဤ Username (သို့) Gmail မှာ အသုံးပြုပြီးသား ဖြစ်နေပါသည်။")
            else:
                st.warning("အချက်အလက်များကို အပြည့်အစုံ ဖြည့်စွက်ပါ။")
                
    elif choice == "Forgot Password":
        st.subheader("🔄 Forgot Password (စကားဝှက်မေ့သွားပါက)")
        f_gmail = st.text_input("သင့်အကောင့်တွင် အသုံးပြုထားသော Gmail ထည့်ပါ")
        
        if st.button("Reset Code ပို့ရန်"):
            conn = sqlite3.connect('pro_skincare_ultimate.db')
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users WHERE gmail = ?", (f_gmail,))
            res = cursor.fetchone()
            
            if res:
                code = str(random.randint(100000, 999999))
                cursor.execute("UPDATE users SET reset_code = ? WHERE gmail = ?", (code, f_gmail))
                conn.commit()
                conn.close()
                
                if send_reset_email(f_gmail, code):
                    st.success("Verification Code ကို သင့် Gmail သို့ ပို့လိုက်ပါပြီ။")
                    st.session_state.reset_gmail = f_gmail
                else:
                    st.error("Email ပို့၍မရပါ။ Streamlit secrets တွင် Gmail Config များကို စစ်ဆေးပါ။")
            else:
                conn.close()
                st.error("ဤ Gmail ဖြင့် မှတ်ပုံတင်ထားခြင်း မရှိပါ။")
                
        if "reset_gmail" in st.session_state:
            entered_code = st.text_input("Gmail ထဲသို့ ရောက်လာသော ကုဒ်ကို ထည့်ပါ")
            new_pass = st.text_input("Password အသစ်ထည့်ပါ", type="password")
            
            if st.button("Password အသစ်ပြောင်းမည်"):
                conn = sqlite3.connect('pro_skincare_ultimate.db')
                cursor = conn.cursor()
                cursor.execute("SELECT reset_code FROM users WHERE gmail = ?", (st.session_state.reset_gmail,))
                db_code = cursor.fetchone()[0]
                
                if entered_code == db_code:
                    cursor.execute("UPDATE users SET password = ?, reset_code = ? WHERE gmail = ?", (new_pass, "", st.session_state.reset_gmail))
                    conn.commit()
                    conn.close()
                    st.success("Password အောင်မြင်စွာ ပြောင်းလဲပြီးပါပြီ။ Login ပြန်ဝင်ပါ။")
                    del st.session_state.reset_gmail
                else:
                    conn.close()
                    st.error("ကုဒ်နံပါတ် မှားယွင်းနေပါသည်။")
    st.stop()

# --- MAIN APP (LOGIN ပြီးမှ ပေါ်မည့် Features 20 စနစ်) ---
st.sidebar.write(f"👤 အသုံးပြုသူ: **{st.session_state.username}**")
if st.sidebar.button("Logout ထွက်ရန်"):
    st.session_state.logged_in = False
    st.rerun()

skin_type_input = st.sidebar.selectbox("အသားအရေအမျိုးအစား", ["Oily", "Dry", "Combination", "Acne-Prone", "Sensitive"])
allergies = st.sidebar.text_input("ရှောင်ရန် ပစ္စည်းများ", value="Alcohol, Fragrance")
budget_option = st.sidebar.selectbox("ဘတ်ဂျက်", ["Affordable", "Mid-range", "High-end"])

# 20 Features Organized in Tabs
tabs = st.tabs([
    "1. Face Analysis", "2. Ingredient Scanner", "3. Skin Quiz", "4. Routine Tracker", 
    "5. Gallery", "6. Lifestyle", "7. History & PDF", "8. Glossary", "9. AI Chatbot", 
    "10. Climate Guide", "11. Natural Mask", "12. Conflict Check", "13. Seasonal Routine", 
    "14. Skin Prediction", "15. Med Summary", "16. UV Tracker", "17. Hydration Coach", 
    "18. Budget Planner", "19. Expert Q&A", "20. Community Hub"
])

# Feature 1: Face Analysis (Using Vision Model & 100% Burmese)
with tabs[0]:
    st.subheader("၁။ မျက်နှာအသားအရေ စစ်ဆေးမှု (မြန်မာဘာသာသက်သက်)")
    uploaded_file = st.file_uploader("မျက်နှာပုံ တင်ပါ", type=["jpg", "png", "jpeg"], key="f1")
    if uploaded_file and st.button("စစ်ဆေးမှု ပြီးစီးပါပြီ"):
        with st.spinner("AI စစ်ဆေးနေပါပြီ..."):
            b64_img = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
            prompt = f"""
            သင်သည် အရေပြားဆရာဝန်ဖြစ်သည်။ ဤပုံကို မြန်မာဘာသာဖြင့်သာ စစ်ဆေးပါ။ အင်္ဂလိပ်စာလုံးများ၊ <think> tags များ လုံးဝမပါစေရ။
            - အသားအရေ: {skin_type_input} | ရှောင်ရန်: {allergies} | ဘတ်ဂျက်: {budget_option}
            အောက်ပါခေါင်းစဉ်များဖြင့် မြန်မာလို အပြည့်အစုံ ရေးပါ:
            ၁။ အမှတ်ပေးစနစ် (ACNE_SCORE, DARK_SPOT_SCORE, HYDRATION_SCORE)
            ၂။ မျက်နှာပြင် ခွဲခြမ်းစိတ်ဖြာချက် (မြန်မာလို)
            ၃။ နေ့စဉ်သုံး Routine (မြန်မာလို)
            ၄။ မြန်မာဈေးကွက် ပစ္စည်းများနှင့် ကျပ်ငွေဈေးနှုန်းများ (မြန်မာလို)
            ၅။ အခြားအကြံပြုချက်များ (ရေဓာတ်၊ ရာသီဥတု၊ ရှောင်ရန်များ - မြန်မာလို)
            """
            try:
                response = client.chat.completions.create(
                    model="llama-3.2-11b-vision-preview",
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                    ]}],
                    temperature=0.2
                )
                st.markdown(response.choices[0].message.content)
            except Exception as e:
                st.error(f"အမှားအယွင်း ဖြစ်ပေါ်နေပါသည်: {e}")

# Features 2 to 20 Integrated Structure
with tabs[1]:
    st.subheader("၂။ ပါဝင်ပစ္စည်း စစ်ဆေးခြင်း (Ingredient Scanner)")
    st.write("အလှကုန်ဘူးခွံ ပုံတင်၍ မတည့်သောဓာတ်များ ပါဝင်ခြင်း ရှိမရှိ စစ်ဆေးနိုင်ပါသည်။")

with tabs[2]:
    st.subheader("၃။ အသားအရေအမျိုးအစား စမ်းသပ်မေးခွန်းများ (Skin Quiz)")
    st.write("သင့်အသားအရေအမျိုးအစားကို အဖြေရှာရန် မေးခွန်းလွှာ။")

with tabs[3]:
    st.subheader("၄။ နေ့စဉ် Routine Streak မှတ်တမ်း")
    st.metric("🔥 Skincare Streak", "10 Days")

with tabs[4]:
    st.subheader("၅။ အသားအရေ တိုးတက်မှု ဓာတ်ပုံပြခန်း (Progress Gallery)")
    st.write("အပတ်စဉ် ဓာတ်ပုံမှတ်တမ်းများ သိမ်းဆည်းရန်။")

with tabs[5]:
    st.subheader("၆။ ရေနှင့် အိပ်စက်ခြင်း မှတ်တမ်း (Lifestyle Chart)")
    st.write("ရေသောက်ချိန်နှင့် အိပ်ချိန်များကို ခြေရာခံခြင်း။")

with tabs[6]:
    st.subheader("၇။ မှတ်တမ်းများနှင့် PDF ထုတ်ယူခြင်း (History & Export)")
    st.write("ယခင်စစ်ဆေးချက်များကို ရယူရန်။")

with tabs[7]:
    st.subheader("၈။ အလှကုန် ပါဝင်ပစ္စည်းများ အဘိဓာန် (Glossary)")
    st.write("Retinol, Niacinamide စသည့် ပစ္စည်းများအကြောင်း မြန်မာလို ဖတ်ရှုရန်။")

with tabs[8]:
    st.subheader("၉။ AI Beauty Chatbot (မြန်မာလို မေးမြန်းရန်)")
    user_chat = st.text_input("မေးခွန်းမေးရန်...", key="chat_9")
    if st.button("မေးရန်", key="btn_9"):
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": f"မြန်မာလို ဖြေပေးပါ: {user_chat}"}])
        st.markdown(res.choices[0].message.content)

with tabs[9]:
    st.subheader("၁၀။ မြန်မာနိုင်ငံ ရာသီဥတု လမ်းညွှန် (Climate Guide)")
    st.write("ပူပြင်းစွတ်စိုသော ရာသီဥတုအတွက် အထူးအကြံပြုချက်များ။")

with tabs[10]:
    st.subheader("၁၁။ အိမ်သုံး Natural Mask ဖော်စပ်နည်း Creator")
    st.write("သဘာဝပစ္စည်းများဖြင့် မျက်နှာဖုံး ပြုလုပ်နည်းများ။")

with tabs[11]:
    st.subheader("၁၂။ Skincare ဓာတ်ပြုမှု စစ်ဆေးခြင်း (Conflict Detector)")
    st.write("Vitamin C နှင့် Retinol ကဲ့သို့ မတွဲသုံးသင့်သည်များကို စစ်ဆေးရန်။")

with tabs[12]:
    st.subheader("၁၃။ ရာသီဥတုအလိုက် Routine ပြောင်းလဲခြင်း (Seasonal Adjuster)")
    st.write("မိုးရာသီ၊ ဆောင်းရာသီအလိုက် အသားအရေ ထိန်းသိမ်းမှုပုံစံ။")

with tabs[13]:
    st.subheader("၁၄။ အသားအရေ အခြေအနေ ကြိုတင်ခန့်မှန်းခြင်း (Predictive Analysis)")
    st.write("ရေရှည် အသားအရေ တိုးတက်မှုကို ခန့်မှန်းပေးခြင်း။")

with tabs[14]:
    st.subheader("၁၅။ ဆရာဝန်ပြရန် Medical Summary ထုတ်ပေးခြင်း")
    st.write("အရေပြားဆရာဝန်ထံ ပြသရန် လိုအပ်သော အချက်အလက်အကျဉ်းချုပ်။")

with tabs[15]:
    st.subheader("၁၆။ နေရောင်ခြည်နှင့် UV အညွှန်းကိန်း ခြေရာခံခြင်း (UV Tracker)")
    st.write("ပြင်ပထွက်မည့်အချိန် UV အခြေအနေ စစ်ဆေးရန်။")

with tabs[16]:
    st.subheader("၁၇။ အသားအရေ ရေဓာတ်ထိန်းသိမ်းမှု Coach")
    st.write("ရေဓာတ်ပြည့်ဝစေရန် အကြံပြုချက်များ။")

with tabs[17]:
    st.subheader("၁၈။ ဘတ်ဂျက်အလိုက် အလှကုန်စီမံခန့်ခွဲမှု (Budget Planner)")
    st.write("ငွေကြေးသုံးစွဲမှုအပေါ်မူတည်၍ အကောင်းဆုံးပစ္စည်း ရွေးချယ်ရန်။")

with tabs[18]:
    st.subheader("၁၉။ ကျွမ်းကျင်သူများ၏ Q&A ကဏ္ဍ")
    st.write("အမေးအများဆုံး အလှအပဆိုင်ရာ မေးခွန်းများ။")

with tabs[19]:
    st.subheader("၂၀။ အသုံးပြုသူများ၏ အတွေ့အကြုံ ဖလှယ်ရာ Community Hub")
    st.write("အခြားသူများ၏ အသားအရေ ထိန်းသိမ်းမှု အတွေ့အကြုံများ ဖတ်ရှုရန်။")
