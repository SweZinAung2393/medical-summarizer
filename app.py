import base64
import json
import streamlit as st
from openai import OpenAI

client = OpenAI(
    api_key=(
        "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"
    )
)

st.set_page_config(page_title="AI Medical Summarizer", layout="wide")
st.title("🏥 AI Medical Report Summarizer")


def analyze_medical_report(uploaded_file):
  bytes_data = uploaded_file.getvalue()
  base64_image = base64.b64encode(bytes_data).decode("utf-8")
  prompt = """
    Analyze this medical report image. Extract patient name, test date, abnormal findings, summary, and recommendations.
    Return strictly in JSON format with keys: patient_name, test_date, abnormal_findings, summary, recommendations.
    """
  response = client.chat.completions.create(
      model="gpt-4o",
      messages=[{
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
      }],
      response_format={"type": "json_object"},
  )
  return json.loads(response.choices[0].message.content)


uploaded_file = st.file_uploader("ဆေးစစ်ချက် ဓာတ်ပုံ တင်ရန်", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    st.image(uploaded_file, caption="Uploaded Report", use_column_width=True)
    
    # ဤခလုတ်သည် if uploaded_file အောက်တွင် ဝင်ေနရပါမည် (Space 4 ခု ခြားရန်)
    if st.button("🔍 AI ဖြင့် စစ်ဆေးမည်", type="primary"):
        with st.spinner("AI စစ်ဆေးနေပါပြီ..."):
            res = analyze_medical_report(uploaded_file)
            st.success("ပြီးပါပြီ!")
            st.write(f"**👤 လူနာအမည်:** {res.get('patient_name')}")
            st.write(f"**📅 ရက်စွဲ:** {res.get('test_date')}")
            st.info(f"**📝 အနှစ်ချုပ်:** {res.get('summary')}")
