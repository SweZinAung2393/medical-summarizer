import streamlit as st
import base64
from PIL import Image
from groq import Groq
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random

# Page Configuration
st.set_page_config(page_title="Pro Skincare Advisor System", layout="wide")

# Initialize Groq Client
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    st.error("Streamlit Secrets ထဲတွင် GROQ_API_KEY ထည့်သွင်းရန် လိုအပ်ပါသည်။")

# Session state initialization
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "reset_sent" not in st.session_state: st.session_state.reset_sent = False
if "otp_code" not in st.session_state: st.session_state.otp_code = ""

# ----------------- LOGIN SYSTEM ----------------- #
if not st.session_state.logged_in:
    st.title("🔐 Pro Skincare System")
    tab_login, tab_signup, tab_forgot = st.tabs(["Login", "Sign Up", "Forgot Password"])
    
    with tab_login:
        username = st.text_input("Username", key="l_user")
        password = st.text_input("Password", type="password", key="l_pass")
        if st.button("Login"):
            st.session_state.logged_in = True
            st.rerun()
    with tab_signup:
        st.write("အကောင့်သစ်ဖွင့်ရန် အချက်အလက်များဖြည့်ပါ။")
    with tab_forgot:
        st.write("စကားဝှက်မေ့ပါက အကူအညီရယူပါ။")
    st.stop()

# ----------------- MAIN DASHBOARD ----------------- #
st.sidebar.title("✨ Pro Skincare Menu")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

st.title("🌿 Pro Skincare & Medical Analysis System")

tabs = st.tabs([
    "၁. မျက်နှာစစ်ဆေးမှု", "၂. အသားအရေ", "၃. Ingredient", "၄. Skin Quiz", "၅. Routine", 
    "၆. Product နှိုင်းယှဉ်", "၇. ရာသီဥတု", "၈. အစားအသောက်", "၉. ရေဓာတ်", "၁၀. နေရောင်ကာကွယ်", 
    "၁၁. ဝက်ခြံ", "၁၂. အိုမင်းရင့်ရော်", "၁၃. အသားဖြူ", "၁၄. AI Chat", "၁၅. Medical Summary", 
    "၁၆. Email", "၁၇. မှတ်တမ်း", "၁၈. Recommend", "၁၉. ဆရာဝန်", "၂၀. သိမ်းဆည်းရန်"
])

# Feature 1: Face Analysis
with tabs[0]:
    st.subheader("၁။ မျက်နှာအသားအရေ စစ်ဆေးမှု")
    uploaded_file = st.file_uploader("မျက်နှာပုံ တင်ပါ", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        st.image(uploaded_file, caption="တင်ထားသော ပုံ", use_container_width=True)
        if st.button("စစ်ဆေးမှု စတင်ရန်"):
            with st.spinner("AI ဖြင့် သုံးသပ်နေပါပြီ..."):
                try:
                    # မော်ဒယ်နာမည်ကို 'llama-3.3-70b-versatile' ဟု ပြင်ထားသည်
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": "ဤမျက်နှာပုံကိုကြည့်ပြီး အသားအရေအခြေအနေနှင့် Skincare အကြံပြုချက်များကို မြန်မာဘာသာဖြင့် အသေးစိတ်ပြောပြပေးပါ။"}],
                        temperature=0.4
                    )
                    st.markdown(response.choices[0].message.content)
                except Exception as e:
                    st.error(f"Error: {e}")

# Features 2-20
feature_names = [
    "အသားအရေအမျိုးအစား ခွဲခြားခြင်း", "Skincare Ingredient Scanner", "Skin Quiz စစ်ဆေးခြင်း",
    "Skincare Routine ဖန်တီးပေးခြင်း", "Product များကို နှိုင်းယှဉ်ခြင်း", "ရာသီဥတုအလိုက် အကြံပြုချက်",
    "အသားအရေအတွက် အစားအသောက်များ", "ရေဓာတ်ထိန်းသိမ်းမှု အကြံပြုချက်", "Sunscreen ရွေးချယ်ပုံ လမ်းညွှန်",
    "ဝက်ခြံနှင့် အမာရွတ် ကုသနည်းများ", "အိုမင်းရင့်ရော်မှု ကာကွယ်ခြင်း", "မျက်ကွင်းညိုခြင်း ကာကွယ်ရန်",
    "AI Skincare Chatbot မေးခွန်းမေးရန်", "ဆရာဝန်ပြရန် Medical Summary ထုတ်ပေးခြင်း", "အချက်အလက်များကို Email ပို့ရန်",
    "သုံးစွဲသူ၏ ကျန်းမာရေး မှတ်တမ်းများ", "အကောင်းဆုံး Product Recommendations များ", "ဆရာဝန်နှင့် တိုက်ရိုက်တိုင်ပင်ရန် လမ်းညွှန်", "အချက်အလက်များ သိမ်းဆည်းရန် စနစ်"
]

for i in range(1, 20):
    with tabs[i]:
        st.subheader(f"{i+1}။ {feature_names[i-1]}")
        user_input = st.text_area(f"{feature_names[i-1]} အတွက် မေးမြန်းရန်", key=f"in_{i}")
        if st.button("ဖန်တီးမည်", key=f"btn_{i}"):
            if user_input:
                with st.spinner("ဆောင်ရွက်နေပါပြီ..."):
                    res = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": f"အောက်ပါအကြောင်းအရာအတွက် မြန်မာဘာသာဖြင့် အသေးစိတ် ရေးပေးပါ: {user_input}"}],
                        temperature=0.4
                    )
                    st.markdown(res.choices[0].message.content)                    
