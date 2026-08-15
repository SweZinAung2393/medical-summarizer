import base64
import json
import io
import textwrap

import streamlit as st
from groq import Groq

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AI Medical Assistant",
    page_icon="🏥",
    layout="wide"
)


# ============================================================
# GROQ API CLIENT
# ============================================================

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

    client = Groq(
        api_key=GROQ_API_KEY
    )

except Exception:
    st.error(
        "GROQ_API_KEY မတွေ့ပါ။ "
        "Streamlit Secrets ထဲမှာ GROQ_API_KEY ထည့်ပေးပါ။"
    )
    st.stop()


# ============================================================
# VISION MODEL
# ============================================================

VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


# ============================================================
# AI MEDICAL REPORT ANALYSIS
# ============================================================

def analyze_report(image_bytes, mime_type):

    # Convert image to Base64
    base64_image = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    # Prompt
    prompt = """
You are an AI assistant that analyzes medical laboratory
reports from images.

IMPORTANT:
- Read the medical report carefully.
- Extract only information that is visible in the image.
- Do NOT invent missing information.
- If a value cannot be read, use an empty string.
- Do not make a final medical diagnosis.
- Recommendations should be general and should encourage
  consultation with a qualified doctor when appropriate.

Return ONLY valid JSON.

The JSON MUST contain exactly these keys:

{
    "patient_name": "",
    "test_date": "",
    "summary": "",
    "abnormal_findings": [],
    "recommendations": []
}

Requirements:

patient_name:
- Patient name shown in the report.
- If unavailable, return "".

test_date:
- Test/report date shown in the report.
- If unavailable, return "".

summary:
- Explain the report in simple English.
- Then provide a simple Myanmar explanation.
- Clearly mention that this is not a medical diagnosis.

abnormal_findings:
- Return a JSON list.
- Include abnormal or potentially abnormal results visible
  in the report.
- If there are no obvious abnormal findings, return [].

recommendations:
- Return a JSON list.
- Give general health/doctor-follow-up recommendations.
- Do not prescribe medication or dosage.

Do not use Markdown.
Do not use ```json.
Return JSON only.
"""

    try:

        response = client.chat.completions.create(

            model=VISION_MODEL,

            messages=[
                {
                    "role": "user",
                    "content": [

                        {
                            "type": "text",
                            "text": prompt
                        },

                        {
                            "type": "image_url",
                            "image_url": {
                                "url": (
                                    f"data:{mime_type};base64,"
                                    f"{base64_image}"
                                )
                            }
                        }

                    ]
                }
            ],

            temperature=0.1,

            max_completion_tokens=2048,

            response_format={
                "type": "json_object"
            }
        )

        content = (
            response
            .choices[0]
            .message
            .content
            .strip()
        )

        # Remove accidental Markdown
        content = content.replace(
            "```json",
            ""
        )

        content = content.replace(
            "```",
            ""
        )

        content = content.strip()

        # Convert JSON string to Python dictionary
        result = json.loads(content)

        # Make sure all required keys exist
        result.setdefault(
            "patient_name",
            ""
        )

        result.setdefault(
            "test_date",
            ""
        )

        result.setdefault(
            "summary",
            ""
        )

        result.setdefault(
            "abnormal_findings",
            []
        )

        result.setdefault(
            "recommendations",
            []
        )

        return result

    except json.JSONDecodeError:

        raise Exception(
            "AI က valid JSON ပြန်မပေးနိုင်ပါ။ "
            "ပုံကို ပိုရှင်းအောင် ပြန်တင်ကြည့်ပါ။"
        )

    except Exception as e:

        raise Exception(
            f"Groq API Error: {str(e)}"
        )


# ============================================================
# PDF GENERATION
# ============================================================

def create_pdf(
    patient_name,
    test_date,
    summary,
    abnormal_findings,
    recommendations
):

    buffer = io.BytesIO()

    pdf = canvas.Canvas(
        buffer,
        pagesize=letter
    )

    width, height = letter

    # --------------------------------------------------------
    # Myanmar Font
    # --------------------------------------------------------

    font_name = "Helvetica"

    try:

        pdfmetrics.registerFont(
            TTFont(
                "Pyidaungsu",
                "Pyidaungsu.ttf"
            )
        )

        font_name = "Pyidaungsu"

    except Exception:

        font_name = "Helvetica"


    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    pdf.setFont(
        font_name,
        18
    )

    pdf.drawString(
        50,
        height - 50,
        "AI Medical Report Summary"
    )


    # --------------------------------------------------------
    # Patient Information
    # --------------------------------------------------------

    pdf.setFont(
        font_name,
        11
    )

    y = height - 90

    pdf.drawString(
        50,
        y,
        f"Patient: {patient_name}"
    )

    y -= 25

    pdf.drawString(
        50,
        y,
        f"Test Date: {test_date}"
    )

    y -= 40


    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    pdf.setFont(
        font_name,
        13
    )

    pdf.drawString(
        50,
        y,
        "Summary"
    )

    y -= 25

    pdf.setFont(
        font_name,
        10
    )

    summary_lines = textwrap.wrap(
        summary,
        width=90
    )

    for line in summary_lines:

        if y < 60:

            pdf.showPage()

            pdf.setFont(
                font_name,
                10
            )

            y = height - 50

        pdf.drawString(
            50,
            y,
            line
        )

        y -= 15


    # --------------------------------------------------------
    # Abnormal Findings
    # --------------------------------------------------------

    y -= 20

    pdf.setFont(
        font_name,
        13
    )

    pdf.drawString(
        50,
        y,
        "Abnormal Findings"
    )

    y -= 25

    pdf.setFont(
        font_name,
        10
    )

    if abnormal_findings:

        for finding in abnormal_findings:

            lines = textwrap.wrap(
                "• " + str(finding),
                width=85
            )

            for line in lines:

                if y < 60:

                    pdf.showPage()

                    pdf.setFont(
                        font_name,
                        10
                    )

                    y = height - 50

                pdf.drawString(
                    50,
                    y,
                    line
                )

                y -= 15

    else:

        pdf.drawString(
            50,
            y,
            "No obvious abnormal findings detected."
        )

        y -= 15


    # --------------------------------------------------------
    # Recommendations
    # --------------------------------------------------------

    y -= 20

    pdf.setFont(
        font_name,
        13
    )

    pdf.drawString(
        50,
        y,
        "Recommendations"
    )

    y -= 25

    pdf.setFont(
        font_name,
        10
    )

    if recommendations:

        for recommendation in recommendations:

            lines = textwrap.wrap(
                "• " + str(recommendation),
                width=85
            )

            for line in lines:

                if y < 60:

                    pdf.showPage()

                    pdf.setFont(
                        font_name,
                        10
                    )

                    y = height - 50

                pdf.drawString(
                    50,
                    y,
                    line
                )

                y -= 15

    else:

        pdf.drawString(
            50,
            y,
            "Please consult a qualified doctor if needed."
        )


    # --------------------------------------------------------
    # Disclaimer
    # --------------------------------------------------------

    y -= 35

    if y < 60:

        pdf.showPage()

        y = height - 50

    pdf.setFont(
        font_name,
        8
    )

    disclaimer = (
        "Disclaimer: This AI-generated summary is for "
        "informational purposes only and is not a medical "
        "diagnosis. Please consult a qualified healthcare "
        "professional for medical advice."
    )

    disclaimer_lines = textwrap.wrap(
        disclaimer,
        width=100
    )

    for line in disclaimer_lines:

        pdf.drawString(
            50,
            y,
            line
        )

        y -= 12


    # Finish PDF
    pdf.save()

    buffer.seek(0)

    return buffer


# ============================================================
# STREAMLIT USER INTERFACE
# ============================================================

st.title(
    "🏥 AI Medical Assistant"
)

st.write(
    "ဆေးစစ်ချက် / Medical Report ကို တင်ပြီး "
    "AI ဖြင့် အချက်အလက်များကို ခွဲခြမ်းစိတ်ဖြာနိုင်ပါသည်။"
)

st.info(
    "⚠️ AI result သည် ဆရာဝန်၏ diagnosis မဟုတ်ပါ။ "
    "အရေးကြီးသော ကျန်းမာရေးဆုံးဖြတ်ချက်များအတွက် "
    "ဆရာဝန်နှင့် တိုင်ပင်ပါ။"
)


# ============================================================
# FILE UPLOADER
# ============================================================

uploaded_file = st.file_uploader(
    "📄 ဆေးစာရွက်တင်ရန်",
    type=[
        "jpg",
        "jpeg",
        "png"
    ]
)


# ============================================================
# IMAGE PREVIEW
# ============================================================

if uploaded_file:

    st.subheader(
        "📷 Uploaded Medical Report"
    )

    image = Image.open(
        uploaded_file
    )

    st.image(
        image,
        caption="Medical Report",
        use_container_width=True
    )


# ============================================================
# ANALYZE BUTTON
# ============================================================

if uploaded_file:

    if st.button(
        "🔍 စစ်ဆေးမည်",
        type="primary"
    ):

        with st.spinner(
            "AI က ဆေးစာရွက်ကို စစ်ဆေးနေပါသည်..."
        ):

            try:

                # Get image bytes
                image_bytes = uploaded_file.getvalue()

                # Get correct MIME type
                mime_type = uploaded_file.type

                # Analyze
                result = analyze_report(
                    image_bytes,
                    mime_type
                )

                # Save result
                st.session_state[
                    "current_report"
                ] = result


                # ------------------------------------------------
                # SUCCESS
                # ------------------------------------------------

                st.success(
                    "✅ Analysis Complete!"
                )


                # ------------------------------------------------
                # PATIENT INFORMATION
                # ------------------------------------------------

                st.subheader(
                    "👤 Patient Information"
                )

                col1, col2 = st.columns(2)

                with col1:

                    st.write(
                        "**Patient Name:**"
                    )

                    st.write(
                        result.get(
                            "patient_name",
                            ""
                        )
                        or "Not available"
                    )

                with col2:

                    st.write(
                        "**Test Date:**"
                    )

                    st.write(
                        result.get(
                            "test_date",
                            ""
                        )
                        or "Not available"
                    )


                # ------------------------------------------------
                # SUMMARY
                # ------------------------------------------------

                st.subheader(
                    "📋 Summary"
                )

                st.write(
                    result.get(
                        "summary",
                        ""
                    )
                )


                # ------------------------------------------------
                # ABNORMAL FINDINGS
                # ------------------------------------------------

                st.subheader(
                    "⚠️ Abnormal Findings"
                )

                abnormal_findings = result.get(
                    "abnormal_findings",
                    []
                )

                if abnormal_findings:

                    for finding in abnormal_findings:

                        st.warning(
                            str(finding)
                        )

                else:

                    st.success(
                        "No obvious abnormal findings detected."
                    )


                # ------------------------------------------------
                # RECOMMENDATIONS
                # ------------------------------------------------

                st.subheader(
                    "💡 Recommendations"
                )

                recommendations = result.get(
                    "recommendations",
                    []
                )

                if recommendations:

                    for recommendation in recommendations:

                        st.write(
                            "• "
                            + str(recommendation)
                        )

                else:

                    st.write(
                        "Please consult a qualified doctor "
                        "if needed."
                    )


                # ------------------------------------------------
                # CREATE PDF
                # ------------------------------------------------

                pdf = create_pdf(

                    result.get(
                        "patient_name",
                        ""
                    ),

                    result.get(
                        "test_date",
                        ""
                    ),

                    result.get(
                        "summary",
                        ""
                    ),

                    result.get(
                        "abnormal_findings",
                        []
                    ),

                    result.get(
                        "recommendations",
                        []
                    )
                )


                # ------------------------------------------------
                # PDF DOWNLOAD
                # ------------------------------------------------

                st.download_button(

                    label="📥 PDF ဒေါင်းလုဒ်ဆွဲရန်",

                    data=pdf,

                    file_name="medical_report_summary.pdf",

                    mime="application/pdf"
                )


            # ====================================================
            # ERROR HANDLING
            # ====================================================

            except Exception as e:

                st.error(
                    "❌ Error ဖြစ်ပွားသည်။"
                )

                st.code(
                    str(e)
                )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "🏥 AI Medical Assistant | "
    "AI-generated results are for informational purposes only."
                    )
