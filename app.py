import streamlit as st
from PIL import Image
from groq import Groq
import io
import base64

# Page Configuration
st.set_page_config(page_title="Pro Skincare Advisor System", layout="wide")

# Initialize Groq Client
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error("Streamlit Secrets ထဲတွင် GROQ_API_KEY ထည့်သွင်းရန် လိုအပ်ပါသည်။")

# Session state initialization
if "logged_in" not in st.session_state: st.session_state.logged_in = False

# ----------------- LOGIN SYSTEM ----------------- #
if not st.session_state.logged_in:
    st.title("🔐 Pro Skincare System - ဝင်ရောက်ရန်")
    tab_login, tab_signup = st.tabs(["Login", "Sign Up"])
    
    with tab_login:
        l_username = st.text_input("Username သို့မဟုတ် Gmail", key="l_user")
        l_password = st.text_input("Password", type="password", key="l_pass")
        if st.button("Login ဝင်မည်"):
            if l_username and l_password:
                st.session_state.logged_in = True
                st.success("အကောင့်ဝင်ရောက်မှု အောင်မြင်ပါသည်။")
                st.rerun()
            else:
                st.warning("အချက်အလက်များကို အပြည့်အစုံထည့်ပါ။")
                
    with tab_signup:
        st.subheader("အကောင့်အသစ်ဖွင့်ရန်")
        s_username = st.text_input("New Username", key="s_user")
        s_password = st.text_input("New Password", type="password", key="s_pass")
        if st.button("အကောင့်ဖွင့်မည်"):
            st.success("အကောင့်ဖွင့်ပြီးပါပြီ။ Login သို့သွားပါ။")
    st.stop()

# ----------------- MAIN DASHBOARD ----------------- #
st.sidebar.title("✨ Pro Skincare Menu")
if st.sidebar.button("Logout ထွက်မည်"):
    st.session_state.logged_in = False
    st.rerun()

st.title("🌿 Pro Skincare & Medical Analysis System (Vision AI)")

# မျက်နှာစစ်ဆေးခြင်းနှင့် အချက်အလက်များ ထည့်သွင်းခြင်း
st.subheader("မျက်နှာအသားအရေ စစ်ဆေးမှုနှင့် လိုအပ်ချက်များ")
uploaded_file = st.file_uploader("သင့်၏ မျက်နှာပုံကို တင်ပါ", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="တင်ထားသော မျက်နှာပုံ", use_container_width=True)
    
    user_note = st.text_input("ထပ်မံဖြည့်စွက် ပြောလိုသည်များ ရှိပါက ရေးပါ")
    
    if st.button("ပုံကို AI ဖြင့် စစ်ဆေးမည်"):
        with st.spinner("မျက်နှာပုံကို AI ဖြင့် သုံးသပ်နေပါပြီ... ခဏစောင့်ပါ။"):
            try:
                # Convert image to base64 data URL
                buffered = io.BytesIO()
                image.save(buffered, format="JPEG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                image_url = f"data:image/jpeg;base64,{img_base64}"
                
                prompt = (
                    "ဒီမျက်နှာပုံကို သေချာလေ့လာပြီး အောက်ပါအချက် (၈) ချက်ကို မြန်မာဘာသာဖြင့် အသေးစိတ် သုံးသပ်ပေးပါ-\n"
                    "၁။ ဝက်ခြံအခြေအနေ (ပေါက်ရောက်မှု အနေအထား၊ အမျိုးအစားနှင့် ပမာဏ)\n"
                    "၂။ ဝက်ခြံအမာရွတ်များနှင့် အသားအရေ အထစ်အဆင်း မညီညာမှုများ\n"
                    "၃။ အမဲစက်၊ နေလောင်ကွက်နှင့် အသားအရေ ညစ်နွမ်းနေသည့် နေရာများ\n"
                    "၄။ ချွေးပေါက်ကျယ်ခြင်း (အထူးသဖြင့် နှာခေါင်းနှင့် ပါးပြင်တစ်ဝိုက်)\n"
                    "၅။ အသားအရေ အမျိုးအစား (ခြောက်သွေ့၊ အဆီပြန်၊ ပေါင်းစပ်) နှင့် သင့်လျော်သော ကုသနည်းများ\n"
                    "၆။ သုံးသင့်သည့် Skincare ပစ္စည်းများ (Cleanser, Toner, Serum, Moisturizer, Sunscreen စသည်ဖြင့် သင့်လျော်သော Ingredient များနှင့်တကွ ဖော်ပြရန်)\n"
                    "၇။ ဤ Skincare ပစ္စည်းများကို မြန်မာနိုင်ငံတွင် ဝယ်ယူရရှိနိုင်မည့်နေရာများ (Supermarket များ၊ Online Skincare Shops များ၊ Pharmacy ဆေးဆိုင်များ)\n"
                    "၈။ အစားအသောက်နှင့် နေထိုင်မှုပုံစံ အကြံပြုချက်များ (ဝက်ခြံ၊ အမဲစက်နှင့် ချွေးပေါက်ကျယ်ခြင်းများ သက်သာစေရန် ရှောင်ရန်/ဆောင်ရန်များ)\n"
                    f"အသုံးပြုသူ၏ ဖြည့်စွက်ချက်: {user_note}"
                )
                
                completion = client.chat.completions.create(
                    model="qwen/qwen3.6-27b",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": image_url}
                                },
                            ],
                        }
                    ],
                    temperature=0.4,
                    max_tokens=2048
                )
                
                st.success("စစ်ဆေးမှု ပြီးဆုံးပါပြီ!")
                st.markdown(completion.choices[0].message.content)
            except Exception as e:
                st.error(f"အမှားအယွင်း ဖြစ်ပေါ်နေပါသည်: {e}")                   
