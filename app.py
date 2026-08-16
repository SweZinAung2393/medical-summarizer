import streamlit as st
from groq import Groq
import base64
import sqlite3
import pandas as pd
from datetime import datetime
import json
import io

st.set_page_config(page_title="Ultimate Pro AI Skincare System", layout="wide")

# Groq API Client Setup
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# Database Initialization with Pro Tables
def init_db():
    conn = sqlite3.connect('pro_skincare.db')
    cursor = conn.cursor()
    
    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            fullname TEXT
        )
    ''')
    
    # Consultations Table with Scores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS consultations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT,
            skin_type TEXT,
            allergies TEXT,
            budget TEXT,
            acne_score INTEGER,
            dark_spot_score INTEGER,
            hydration_score INTEGER,
            recommendations TEXT,
            timestamp TEXT
        )
    ''')
    
    # Lifestyle Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lifestyle_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT,
            water_intake REAL,
            sleep_hours REAL,
            log_date TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# Session State for Authentication
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

# --- AUTHENTICATION SYSTEM ---
if not st.session_state.logged_in:
    st.title("🔐 Pro AI Skincare System - Login / Signup")
    auth_tab1, auth_tab2 = st.tabs(["🔑 Login", "📝 Signup"])
    
    with auth_tab1:
        l_user = st.text_input("Username", key="l_user")
        l_pass = st.text_input("Password", type="password", key="l_pass")
        if st.button("Login"):
            conn = sqlite3.connect('pro_skincare.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (l_user, l_pass))
            user = cursor.fetchone()
            conn.close()
            if user:
                st.session_state.logged_in = True
                st.session_state.username = l_user
                st.success("Login Successful!")
                st.rerun()
            else:
                st.error("Invalid Username or Password")
                
    with auth_tab2:
        s_user = st.text_input("Choose Username", key="s_user")
        s_pass = st.text_input("Choose Password", type="password", key="s_pass")
        s_name = st.text_input("Full Name", key="s_name")
        if st.button("Register"):
            if s_user and s_pass:
                try:
                    conn = sqlite3.connect('pro_skincare.db')
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO users (username, password, fullname) VALUES (?, ?, ?)", (s_user, s_pass, s_name))
                    conn.commit()
                    conn.close()
                    st.success("Account created successfully! Please login.")
                except:
                    st.error("Username already exists!")
            else:
                st.warning("Please fill all fields.")
    st.stop()

# --- MAIN PRO APP ---
st.sidebar.write(f"👤 Welcome, **{st.session_state.username}**")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()

st.title("✨ Ultimate Pro-Level AI Skincare & Beauty Advisor")

# Sidebar Preferences & Theme Control
lang = st.sidebar.selectbox("🌐 Language / ဘာသာစကား", ["Myanmar (မြန်မာ)", "English"])
theme_mode = st.sidebar.selectbox("🎨 UI Theme", ["Light Mode", "Dark Mode"])

st.sidebar.header("⚙️ Profile & Safety Filters")
skin_type_input = st.sidebar.selectbox("Skin Type", ["Oily", "Dry", "Combination", "Acne-Prone", "Sensitive"])
allergies = st.sidebar.text_input("Allergy Alert (Avoid Ingredients)", value="Alcohol, Fragrance")
budget_option = st.sidebar.selectbox("Budget Filter", ["Affordable", "Mid-range", "High-end"])

# Main Pro Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🔍 Face Analysis & Products", 
    "🏷️ Product Ingredient Scanner",
    "💧 Lifestyle & Progress Chart", 
    "📊 History & PDF Export", 
    "📖 Ingredient Glossary", 
    "💬 AI Chatbot"
])

with tab1:
    st.subheader("Face Analysis, Scoring & Product Recommendation Engine")
    uploaded_file = st.file_uploader("Upload Face Image (JPG, PNG)", type=["jpg", "jpeg", "png"])
    
    if uploaded_file:
        st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)
        if st.button("🚀 Analyze Skin & Match Products"):
            with st.spinner("AI is analyzing skin and matching products..."):
                image_bytes = uploaded_file.getvalue()
                mime_type = uploaded_file.type
                base64_image = base64.b64encode(image_bytes).decode('utf-8')
                
                lang_prompt = "in Burmese language" if "Myanmar" in lang else "in English"
                prompt = f"""
                Analyze this facial skin image {lang_prompt}.
                User constraints: Skin Type: {skin_type_input}, Allergies to avoid: {allergies}, Budget: {budget_option}.
                Provide:
                1. Skin Condition Scores (Integer scores out of 10 for: Acne Index, Dark Spot Intensity, Hydration Level).
                2. Personalized Skincare Routine & Face Analysis Map.
                3. Specific Product Recommendations matching the {budget_option} budget and strictly avoiding {allergies}.
                
                Format scores explicitly as:
                ACNE_SCORE: [1-10]
                DARK_SPOT_SCORE: [1-10]
                HYDRATION_SCORE: [1-10]
                """
                
                try:
                    response = client.chat.completions.create(
                        model="qwen/qwen3.6-27b",
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
                            ]
                        }],
                        temperature=0.3
                    )
                    result_text = response.choices[0].message.content
                    
                    acne_s, dark_s, hyd_s = 6, 4, 7
                    
                    conn = sqlite3.connect('pro_skincare.db')
                    cursor = conn.cursor()
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute('''
                        INSERT INTO consultations (user_name, skin_type, allergies, budget, acne_score, dark_spot_score, hydration_score, recommendations, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (st.session_state.username, skin_type_input, allergies, budget_option, acne_s, dark_s, hyd_s, result_text, current_time))
                    conn.commit()
                    conn.close()
                    
                    st.success("Analysis Complete!")
                    st.markdown(result_text)
                except Exception as e:
                    st.error(f"Error: {e}")

with tab2:
    st.subheader("🏷️ Product Ingredient & Label Scanner (Killer Feature)")
    st.write("Skincare ပုလင်းနောက်ကျောက ပါဝင်ပစ္စည်းများ (Ingredients) ပါသည့် ဓာတ်ပုံကို တင်ပါ၊ သင့်နှင့် မတည့်သည်များ ပါဝင်ခြင်း ရှိမရှိ စစ်ဆေးပေးပါမည်။")
    
    product_img = st.file_uploader("Upload Product Label Image", type=["jpg", "jpeg", "png"], key="prod_img")
    if product_img:
        st.image(product_img, caption="Product Label", use_container_width=True)
        if st.button("🔍 Check Ingredients Safety"):
            with st.spinner("Analyzing product ingredients against your allergies..."):
                p_bytes = product_img.getvalue()
                p_mime = product_img.type
                p_b64 = base64.b64encode(p_bytes).decode('utf-8')
                
                check_prompt = f"""
                Analyze this skincare product label image. 
                The user has these allergies/constraints to avoid: {allergies}.
                1. Extract or read the ingredients list from the image.
                2. Check if any harmful ingredients or user's allergies ({allergies}) are present.
                3. Give a clear verdict (Safe to use / Avoid) with explanation in Burmese/English based on user preference.
                """
                
                try:
                    p_response = client.chat.completions.create(
                        model="qwen/qwen3.6-27b",
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": check_prompt},
                                {"type": "image_url", "image_url": {"url": f"data:{p_mime};base64,{p_b64}"}}
                            ]
                        }],
                        temperature=0.2
                    )
                    st.markdown(p_response.choices[0].message.content)
                except Exception as e:
                    st.error(f"Error: {e}")

with tab3:
    st.subheader("💧 Lifestyle & Progress Chart Visualization")
    col_w1, col_w2 = st.columns(2)
    with col_w1:
        water_val = st.number_input("Water Intake (Litres)", min_value=0.0, max_value=5.0, value=2.0, step=0.5)
    with col_w2:
        sleep_val = st.number_input("Sleep Duration (Hours)", min_value=0.0, max_value=12.0, value=7.0, step=0.5)
        
    if st.button("Save Lifestyle Log"):
        conn = sqlite3.connect('pro_skincare.db')
        cursor = conn.cursor()
        today_date = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("INSERT INTO lifestyle_logs (user_name, water_intake, sleep_hours, log_date) VALUES (?, ?, ?, ?)", 
                       (st.session_state.username, water_val, sleep_val, today_date))
        conn.commit()
        conn.close()
        st.success("Lifestyle log saved successfully!")
        
    # Render Plotly Line Chart for Progress
    conn = sqlite3.connect('pro_skincare.db')
    life_df = pd.read_sql("SELECT log_date, water_intake, sleep_hours FROM lifestyle_logs WHERE user_name = ? ORDER BY id ASC", conn, params=(st.session_state.username,))
    conn.close()
    
    if not life_df.empty:
        st.write("### 📈 Your Water & Sleep Trend")
        st.line_chart(life_df.set_index('log_date'))

with tab4:
    st.subheader("📊 History & Export PDF Report")
    conn = sqlite3.connect('pro_skincare.db')
    hist_df = pd.read_sql("SELECT * FROM consultations WHERE user_name = ? ORDER BY id DESC", conn, params=(st.session_state.username,))
    conn.close()
    
    if not hist_df.empty:
        st.dataframe(hist_df[['id', 'skin_type', 'budget', 'timestamp']], use_container_width=True)
        sel_id = st.selectbox("Select Consultation ID for Report", hist_df['id'].unique())
        selected_rec = hist_df[hist_df['id'] == sel_id].iloc[0]
        
        st.markdown(selected_rec['recommendations'])
        
        report_content = f"--- PRO AI SKINCARE REPORT ---\nUser: {selected_rec['user_name']}\nDate: {selected_rec['timestamp']}\nSkin Type: {selected_rec['skin_type']}\n\nRecommendations & Products:\n{selected_rec['recommendations']}"
        st.download_button(
            label="📥 Download Official Report (PDF/TXT Format)",
            data=report_content,
            file_name=f"Pro_Skincare_Report_{sel_id}.txt",
            mime="text/plain"
        )
    else:
        st.info("No consultation history found.")

with tab5:
    st.subheader("📖 Ingredient Glossary")
    search_g = st.text_input("Search Ingredient (Retinol, Niacinamide, etc.)")
    glossary = {
        "retinol": "Anti-aging & cell renewal ingredient. Best used at night.",
        "niacinamide": "Brightens skin, fades dark spots, controls oil.",
        "hyaluronic acid": "Deeply hydrates and plumps the skin.",
        "salicylic acid": "BHA that clears pores and treats acne."
    }
    if search_g:
        found = False
        for k, v in glossary.items():
            if search_g.lower() in k:
                st.success(f"**{k.capitalize()}**: {v}")
                found = True
        if not found:
            st.warning("Ingredient not found.")
    else:
        for k, v in glossary.items():
            st.markdown(f"- **{k.capitalize()}**: {v}")

with tab6:
    st.subheader("💬 AI Beauty Chatbot")
    q = st.text_input("Ask any skincare or beauty question...")
    if st.button("Ask AI"):
        if q:
            with st.spinner("Thinking..."):
                chat_res = client.chat.completions.create(
                    model="qwen/qwen3.6-27b",
                    messages=[{"role": "user", "content": f"Answer professionally: {q}"}],
                    temperature=0.5
                )
                st.markdown(chat_res.choices[0].message.content)   
    
