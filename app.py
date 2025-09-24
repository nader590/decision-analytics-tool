import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
import io

# ============== Simulation Function ==============
def run_simulation(data, n_simulations=1000):
    results = []
    for _, row in data.iterrows():
        decision = row['decision']
        dist = row['distribution']
        params = eval(row['params'])
        p_success = row['success_prob']

        if dist == "normal":
            values = np.random.normal(params['mean'], params['std'], n_simulations)
        elif dist == "uniform":
            values = np.random.uniform(params['low'], params['high'], n_simulations)
        elif dist == "triangular":
            values = np.random.triangular(params['left'], params['mode'], params['right'], n_simulations)
        elif dist == "beta":
            values = np.random.beta(params['a'], params['b'], n_simulations) * params['scale']
        else:
            values = np.zeros(n_simulations)

        success = np.random.binomial(1, p_success, n_simulations)
        results.append(pd.DataFrame({
            "decision": decision,
            "value": values,
            "success": success
        }))

    return pd.concat(results)

# ============== Report Generator ==============
def generate_pdf_report(summary_df, lang="ar"):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    title = "تقرير قرارات" if lang == "ar" else "Decision Report"
    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 12))

    for _, row in summary_df.iterrows():
        if lang == "ar":
            txt = f"الخيار: {row['decision']} - القيمة المتوقعة: {row['expected_value']:.2f} - معدل النجاح: {row['success_rate']:.2f}"
        else:
            txt = f"Decision: {row['decision']} - Expected Value: {row['expected_value']:.2f} - Success Rate: {row['success_rate']:.2f}"
        story.append(Paragraph(txt, styles["Normal"]))
        story.append(Spacer(1, 8))

    doc.build(story)
    buffer.seek(0)
    return buffer

# ============== Streamlit App ==============
st.title("📊 Decision Analytics Simulator")

uploaded_file = st.file_uploader("📂 Upload your decisions CSV file", type=["csv"])

if uploaded_file:
    data = pd.read_csv(uploaded_file)
    st.write("### Preview of Data")
    st.dataframe(data)

    results = run_simulation(data)

    summary = results.groupby("decision").agg(
        expected_value=("value", "mean"),
        success_rate=("success", "mean"),
        avg_cost=("value", "median")
    ).reset_index()

    st.write("### 📈 Summary of Decisions")
    st.dataframe(summary)

    st.write("### Distribution of Values")
    fig, ax = plt.subplots()
    sns.kdeplot(data=results, x="value", hue="decision", fill=True, ax=ax)
    st.pyplot(fig)

    st.write("### Success Rate by Decision")
    fig, ax = plt.subplots()
    sns.barplot(data=summary, x="decision", y="success_rate", ax=ax)
    st.pyplot(fig)

    st.download_button(
        "⬇️ Download JSON Results",
        data=json.dumps(summary.to_dict(orient="records"), ensure_ascii=False, indent=2),
        file_name="results.json",
        mime="application/json"
    )

    lang = st.selectbox("🌍 اختر اللغة / Choose language", ["ar", "en"])
    pdf_buffer = generate_pdf_report(summary, lang)
    st.download_button(
        "⬇️ Download PDF Report",
        data=pdf_buffer,
        file_name="decision_report.pdf",
        mime="application/pdf"
    )
