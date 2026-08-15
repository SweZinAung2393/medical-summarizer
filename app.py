import base64
import json
import streamlit as st
from PIL import Image
from groq import Groq

# Streamlit Secrets မှ Groq API Key ကို ယူသုံးခြင်း
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

st.set_page_config(page_title="AI Medical Report Summarizer", layout="wide")
st.title("🏥 AI Medical Report Summarizer & Translator")
st.write("မည်သည့် ဆေးစစ်ချက် (သို့မဟုတ်) ကျန်းမာရေးဆိုင်ရာ ဓာတ်ပုံကိုမဆို တင်၍ မြန်မာဘာသာဖြင့် အနှစ်ချုပ် ရယူပါ။")

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

uploaded_file = st.file_uploader("ဆေးစစ်ချက် (သို့မဟုတ်) ကျန်းမာရေး ဓာတ်ပုံ တင်ရန်", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Report Image", use_container_width=True)
    
    if st.button("🔍 AI ဖြင့် စစ်ဆေးမည်", type="primary"):
        with st.spinner("AI စစ်ဆေးနေပါပြီ... ခဏစောင့်ပါ"):
            try:
                res = analyze_medical_report(uploaded_file)
                
                # အရေးပေါ် အခြေအနေ ရှိမရှိ စစ်ဆေးခြင်း
                if res.get('is_emergency', False):
                    st.error("🚨 **သတိပေးချက် - အရေးပေါ် အခြေအနေ:** ဤအစီရင်ခံစာတွင် အရေးကြီးသော သို့မဟုတ် ပုံမှန်မဟုတ်သည့် အချက်များ တွေ့ရှိရသဖြင့် ဆရာဝန်နှင့် ချက်ချင်းပြသသင့်ပါသည်။")
                
                st.success("စစ်ဆေးမှု ပြီးစီးပါပြီ!")
                
                # ၁။ လူနာ၏ အချက်အလက်များ
                st.write(f"**👤 လူနာအမည်:** {res.get('patient_name', 'မပါရှိပါ')}")
                st.write(f"**📅 ရက်စွဲ:** {res.get('test_date', 'မပါရှိပါ')}")
                
                # ၂။ အနှစ်ချုပ်
                st.write("---")
                st.write(f"**📝 အနှစ်ချုပ်:**")
                st.info(res.get('summary', 'အနှစ်ချုပ် မပါရှိပါ။'))
                
                # ၃။ အကြံပြုချက်များ
                st.write("**💡 အကြံပြုချက်များနှင့် လမ်းညွှန်ချက်များ:**")
                recommendations = res.get('recommendations', [])
                if recommendations:
                    for rec in recommendations:
                        st.markdown(f"- {rec}")
                else:
                    st.markdown("- ကျန်းမာရေးနှင့် ညီညွတ်သော လူနေမှုပုံစံကို ဆက်လက်ထိန်းသိမ်းပါ။")
                
            except Exception as e:
                st.error(f"မှားယွင်းမှု ရှိနေသည် (သို့မဟုတ်) ပုံကို တိုက်ရိုက်ဖတ်၍ မရပါ။ ကျေးဇူးပြု၍ ပုံအသစ် (သို့မဟုတ်) ရှင်းလင်းသော ပုံကို ထပ်တင်ပေးပါ။")
                
            
