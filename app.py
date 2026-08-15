import base64
import json
import streamlit as st
from PIL import Image
from groq import Groq

# Streamlit Secrets မှ Groq API Key ကို ယူသုံးခြင်း
client = Groq(api_key=st.secrets["GROQ_API_KEY"])
st.set_page_config(page_title="AI Medical Report Summarizer", layout="wide")
st.title("🏥 AI Medical Report Summarizer & Translator")
st.write("ဆေးစာရွက် (သို့မဟုတ်) ဆေးစစ်ချက် ဓာတ်ပုံကို တင်၍ မြန်မာဘာသာဖြင့် အနှစ်ချုပ် ရယူပါ။")

def analyze_medical_report(uploaded_file):
    bytes_data = uploaded_file.getvalue()
    base64_image = base64.b64encode(bytes_data).decode("utf-8")
    
    prompt = """
    Analyze this medical report image. Extract the following information and return strictly in valid JSON format:
    - patient_name (string)
    - test_date (string)
    - abnormal_findings (list of strings, in English and explained in Myanmar)
    - summary (string, clear summary in Myanmar language)
    - recommendations (list of strings, in Myanmar)
    - is_emergency (boolean: true if there are critical/dangerous values that need immediate doctor attention, otherwise false)
    
    Keys required in JSON: patient_name, test_date, abnormal_findings, summary, recommendations, is_emergency.
    """
    
    chat_completion = client.chat.completions.create(
        model="llama-3.2-11b-vision-preview",
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

uploaded_file = st.file_uploader("ဆေးစစ်ချက် ဓာတ်ပုံ တင်ရန်", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Medical Report", use_container_width=True)
    
    if st.button("🔍 AI ဖြင့် စစ်ဆေးမည်", type="primary"):
        with st.spinner("AI စစ်ဆေးနေပါပြီ... ခဏစောင့်ပါ"):
            try:
                res = analyze_medical_report(uploaded_file)
                
                # အရေးပေါ် အခြေအနေ ရှိမရှိ စစ်ဆေးခြင်း
                if res.get('is_emergency', False):
                    st.error("🚨 **သတိပေးချက် - အရေးပေါ် အခြေအနေ:** ဤဆေးစစ်ချက်တွင် အရေးကြီးသော သို့မဟုတ် ပုံမှန်မဟုတ်သည့် အချက်များ တွေ့ရှိရသဖြင့် ဆရာဝန်နှင့် ချက်ချင်းပြသသင့်ပါသည်။")
                
                st.success("စစ်ဆေးမှု ပြီးစီးပါပြီ!")
                st.write(f"**👤 လူနာအမည်:** {res.get('patient_name', 'မပါရှိပါ။')}")
                st.write(f"**📅 ရက်စွဲ:** {res.get('test_date', 'မပါရှိပါ။')}")
                st.info(f"**📝 အနှစ်ချုပ် (မြန်မာလို):** {res.get('summary', 'အချက်အလက် မရှိပါ။')}")
                
                st.write("### 🔴 မူမမှန်သည့် အချက်များ:")
                for item in res.get('abnormal_findings', []):
                    st.error(f"- {item}")
                    
                st.write("### 🟡 ဆရာဝန်၏ ညွှန်ကြားချက်များ / အကြံပြုချက်များ:")
                for rec in res.get('recommendations', []):
                    st.warning(f"- {rec}")
                    
            except Exception as e:
                st.error(f"မှားယွင်းမှု ရှိနေပါသည်: {e}")
