import base64
import json
import io
import textwrap

import streamlit as st
from groq import Groq
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="AI Medical Assistant",
    page_icon="🏥",
    layout="wide"
)


# =========================================================
# GROQ API KEY
# =========================================================

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

except Exception:
    st.error(
        "❌ GROQ_API_KEY မတွေ့ပါ။\n\n"
        "Streamlit Cloud > Settings > Secrets ထဲမှာ "
        "GROQ_API_KEY ထည့်ပေးပါ။"
    )
    st.stop()


# =========================================================
# GROQ CLIENT
# =========================================================

client = Groq(
    api_key=GROQ_API_KEY
)


# =========================================================
# VISION MODEL
# =========================================================

VISION_MODEL = (
    "meta-llama/llama-4-scout-17b-16e-instruct"
)


# =========================================================
# IMAGE ANALYSIS FUNCTION
# =========================================================

def analyze_report(image_bytes, mime_type):

    # -----------------------------------------------------
    # Convert image to Base64
    # -----------------------------------------------------

    base64_image = base64.b64encode(
        image_bytes
    ).decode("utf-8")


    # -----------------------------------------------------
    # Prompt
    # -----------------------------------------------------

    prompt = """
You are an AI assistant for analyzing medical laboratory
reports from images.

Carefully read the medical report.

IMPORTANT RULES:

1. Extract only information that is visible in the image.
2. Do not invent patient information.
3. Do not invent test values.
4. If information cannot be read, return an empty string.
5. Do not provide a final medical diagnosis.
6. Do not prescribe medicine or dosage.
7. Give general recommendations only.
8. The result must be valid JSON.
9. Do not use Markdown.
10. Do not use ```json.

Return exactly this JSON structure:

{
    "patient_name": "",
    "test_date": "",
    "summary": "",
    "abnormal_findings": [],
    "recommendations": []
}

FIELD RULES:

patient_name:
Return the patient's name visible in the report.
If unavailable, return "".

test_date:
Return the test date visible in the report.
If unavailable, return "".

summary:
Give a simple explanation in English.
Then give a simple explanation in Myanmar language.
Mention that this is not a medical diagnosis.

abnormal_findings:
Return a JSON list.
Include abnormal or potentially abnormal test results
that are visible in the report.
If none are clearly abnormal, return [].

recommendations:
Return a JSON list.
Give general recommendations such as consulting a doctor
when appropriate.
Do not prescribe medication.

Return JSON only.
"""


    # -----------------------------------------------------
    # Send request to Groq
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # Get AI response
    # -----------------------------------------------------

    content = (
        response
        .choices[0]
        .message
        .content
        .strip()
    )


    # -----------------------------------------------------
    # Remove accidental Markdown
    # -----------------------------------------------------

    content = content.replace(
        "```json",
        ""
    )

    content = content.replace(
        "```",
        ""
    )

    content = content.strip()


    # -----------------------------------------------------
    # Convert JSON to Python dictionary
    # -----------------------------------------------------

    result = json.loads(
        content
    )


    # -----------------------------------------------------
    # Make sure required keys exist
    # -----------------------------------------------------

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


# =========================================================
# PDF FUNCTION
# =========================================================

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


    # -----------------------------------------------------
    # Title
    # -----------------------------------------------------

    pdf.setFont(
        "Helvetica-Bold",
        18
    )

    pdf.drawString(
        50,
        height - 50,
        "AI Medical Report Summary"
    )


    # -----------------------------------------------------
    # Patient Information
    # -----------------------------------------------------

    pdf.setFont(
        "Helvetica",
        11
    )

    y = height - 90

    pdf.drawString(
        50,
        y,
        "Patient: " + str(patient_name)
    )

    y -= 25

    pdf.drawString(
        50,
        y,
        "Test Date: " + str(test_date)
    )

    y -= 40


    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------

    pdf.setFont(
        "Helvetica-Bold",
        13
    )

    pdf.drawString(
        50,
        y,
        "Summary"
    )

    y -= 25

    pdf.setFont(
        "Helvetica",
        10
    )

    summary_lines = textwrap.wrap(
        str(summary),
        width=90
    )

    for line in summary_lines:

        if y < 60:

            pdf.showPage()

            pdf.setFont(
                "Helvetica",
                10
            )

            y = height - 50

        pdf.drawString(
            50,
            y,
            line
        )

        y -= 15


    # -----------------------------------------------------
    # Abnormal Findings
    # -----------------------------------------------------

    y -= 20

    pdf.setFont(
        "Helvetica-Bold",
        13
    )

    pdf.drawString(
        50,
        y,
        "Abnormal Findings"
    )

    y -= 25

    pdf.setFont(
        "Helvetica",
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
                        "Helvetica",
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


    # -----------------------------------------------------
    # Recommendations
    # -----------------------------------------------------

    y -= 20

    pdf.setFont(
        "Helvetica-Bold",
        13
    )

    pdf.drawString(
        50,
        y,
        "Recommendations"
    )

    y -= 25

    pdf.setFont(
        "Helvetica",
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
                        "Helvetica",
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

        y -= 15


    # -----------------------------------------------------
    # Disclaimer
    # -----------------------------------------------------

    y -= 30

    if y < 60:

        pdf.showPage()

        y = height - 50

    pdf.setFont(
        "Helvetica",
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


    # -----------------------------------------------------
    # Save PDF
    # -----------------------------------------------------

    pdf.save()

    buffer.seek(0)

    return buffer


# =========================================================
# STREAMLIT UI
# =========================================================

st.title(
    "🏥 AI Medical Assistant"
)

st.write(
    "ဆေးစစ်ချက် / Medical Report ကို တင်ပြီး "
    "AI ဖြင့် ခွဲခြမ်းစိတ်ဖြာနိုင်ပါသည်။"
)


# =========================================================
# WARNING
# =========================================================

st.warning(
    "⚠️ AI result သည် ဆရာဝန်၏ diagnosis မဟုတ်ပါ။ "
    "အရေးကြီးသော ကျန်းမာရေးဆုံးဖြတ်ချက်များအတွက် "
    "ဆရာဝန်နှင့် တိုင်ပင်ပါ။"
)


# =========================================================
# FILE UPLOADER
# =========================================================

uploaded_file = st.file_uploader(
    "📄 ဆေးစာရွက်တင်ရန်",
    type=[
        "jpg",
        "jpeg",
        "png"
    ]
)


# =========================================================
# IMAGE PREVIEW
# =========================================================

if uploaded_file:

    st.subheader(
        "📷 Uploaded Medical Report"
    )

    # IMPORTANT:
    # Image.open() မသုံးပါ။
    # Streamlit က uploaded file ကို တိုက်ရိုက်ပြနိုင်ပါတယ်။

    st.image(
        uploaded_file,
        caption="Medical Report",
        use_container_width=True
    )


# =========================================================
# ANALYZE BUTTON
# =========================================================

if uploaded_file:

    analyze_button = st.button(
        "🔍 စစ်ဆေးမည်",
        type="primary"
    )


    if analyze_button:

        with st.spinner(
            "🤖 AI က ဆေးစာရွက်ကို စစ်ဆေးနေပါသည်..."
        ):

            try:

                # ------------------------------------------------
                # Get uploaded image
                # ------------------------------------------------

                image_bytes = uploaded_file.getvalue()

                mime_type = uploaded_file.type


                # ------------------------------------------------
                # Check image size
                # ------------------------------------------------

                image_size_mb = (
                    len(image_bytes)
                    / (1024 * 1024)
                )


                if image_size_mb > 4:

                    st.error(
                        "❌ Image size က 4 MB ထက်ကြီးနေပါတယ်။ "
                        "ပုံကို compress လုပ်ပြီး ပြန်တင်ပါ။"
                    )

                    st.stop()


                # ------------------------------------------------
                # Analyze report
                # ------------------------------------------------

                result = analyze_report(
                    image_bytes,
                    mime_type
                )


                # ------------------------------------------------
                # Save result
                # ------------------------------------------------

                st.session_state[
                    "current_report"
                ] = result


                # ------------------------------------------------
                # Success
                # ------------------------------------------------

                st.success(
                    "✅ Analysis Complete!"
                )


                # =================================================
                # PATIENT INFORMATION
                # =================================================

                st.subheader(
                    "👤 Patient Information"
                )

                col1, col2 = st.columns(2)


                with col1:

                    st.write(
                        "**Patient Name**"
                    )

                    patient_name = result.get(
                        "patient_name",
                        ""
                    )

                    if patient_name:

                        st.info(
                            patient_name
                        )

                    else:

                        st.info(
                            "Not available"
                        )


                with col2:

                    st.write(
                        "**Test Date**"
                    )

                    test_date = result.get(
                        "test_date",
                        ""
                    )

                    if test_date:

                        st.info(
                            test_date
                        )

                    else:

                        st.info(
                            "Not available"
                        )


                # =================================================
                # SUMMARY
                # =================================================

                st.subheader(
                    "📋 Summary"
                )

                summary = result.get(
                    "summary",
                    ""
                )

                st.write(
                    summary
                )


                # =================================================
                # ABNORMAL FINDINGS
                # =================================================

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


                # =================================================
                # RECOMMENDATIONS
                # =================================================

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


                # =================================================
                # CREATE PDF
                # =================================================

                pdf_file = create_pdf(

                    patient_name,

                    test_date,

                    summary,

                    abnormal_findings,

                    recommendations
                )


                # =================================================
                # PDF DOWNLOAD
                # =================================================

                st.subheader(
                    "📥 Download Report"
                )

                st.download_button(

                    label="📥 PDF ဒေါင်းလုဒ်ဆွဲရန်",

                    data=pdf_file,

                    file_name=(
                        "medical_report_summary.pdf"
                    ),

                    mime="application/pdf"
                )


            # =====================================================
            # ERROR HANDLING
            # =====================================================

            except json.JSONDecodeError:

                st.error(
                    "❌ AI response ကို JSON အဖြစ် "
                    "ဖတ်မရပါ။ ပုံကို ပိုရှင်းအောင် "
                    "ပြန်တင်ပြီး စမ်းကြည့်ပါ။"
                )


            except Exception as e:

                st.error(
                    "❌ AI Analysis Error"
                )

                st.write(
                    str(e)
                )


# =========================================================
# FOOTER
# =========================================================

st.markdown("---")

st.caption(
    "🏥 AI Medical Assistant | "
    "AI-generated information is for educational and "
    "informational purposes only."
)
