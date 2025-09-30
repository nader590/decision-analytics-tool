import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
import seaborn as sns
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from openpyxl import Workbook
import streamlit as st

# ============== Data Validation ==============
def validate_data(df):
    required_cols = ["decision", "distribution", "params", "success_prob"]
    for col in required_cols:
        if col not in df.columns:
            st.error(f"❌ Missing required column: {col}")
            return False

    for _, row in df.iterrows():
        if not (0 <= row["success_prob"] <= 1):
            st.error(f"❌ Invalid success_prob in decision {row['decision']}")
            return False
        try:
            json.loads(row["params"].replace("'", '"'))
        except Exception as e:
            st.error(f"❌ Params not valid JSON for {row['decision']}: {e}")
            return False
    return True

# ============== Simulation Engine ==============
def run_simulation(data, n_simulations=1000):
    results = []
    for _, row in data.iterrows():
        decision = str(row['decision'])
        dist = str(row['distribution']).lower()
        params = json.loads(row["params"].replace("'", '"'))
        p_success = float(row["success_prob"])

        if dist == "normal":
            values = np.random.normal(params['mean'], params['std'], n_simulations)
        elif dist == "uniform":
            values = np.random.uniform(params['low'], params['high'], n_simulations)
        elif dist == "triangular":
            values = np.random.triangular(params['left'], params['mode'], params['right'], n_simulations)
        elif dist == "beta":
            values = np.random.beta(params['a'], params['b'], n_simulations) * params.get('scale', 1)
        elif dist == "exponential":
            values = np.random.exponential(params['scale'], n_simulations)
        elif dist == "lognormal":
            values = np.random.lognormal(params['mean'], params['sigma'], n_simulations)
        elif dist == "poisson":
            values = np.random.poisson(params['lam'], n_simulations)
        elif dist == "gamma":
            values = np.random.gamma(params['shape'], params['scale'], n_simulations)
        elif dist == "chi-square":
            values = np.random.chisquare(params['df'], n_simulations)
        elif dist == "binomial":
            values = np.random.binomial(params['n'], params['p'], n_simulations)
        else:
            raise ValueError(f"❌ Unsupported distribution: {dist}")

        success = np.random.binomial(1, p_success, n_simulations)

        results.append(pd.DataFrame({
            "decision": decision,
            "value": values,
            "success": success
        }))

    return pd.concat(results, ignore_index=True)

# ============== Visualization Helper ==============
def render_and_download(fig, filename, caption):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    st.image(buf, caption=caption)
    st.download_button(
        label=f"⬇️ Download {filename}",
        data=buf,
        file_name=filename,
        mime="image/png"
    )

# ============== Reports ==============
def generate_pdf_report(summary_df, lang="en"):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    title = "تقرير القرارات" if lang == "ar" else "Decision Report"
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

def generate_excel_report(summary_df):
    buffer = io.BytesIO()
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"

    ws.append(summary_df.columns.tolist())
    for _, row in summary_df.iterrows():
        ws.append(row.tolist())

    wb.save(buffer)
    buffer.seek(0)
    return buffer

# ============== Streamlit UI ==============
st.title("📈 Decision Analytics Tool")

uploaded_file = st.file_uploader("Upload your CSV", type="csv")
runs = st.slider("Number of simulations", 100, 5000, 1000, step=100)
lang = st.radio("Report Language", ["en", "ar"], horizontal=True)

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.write("Preview:", df.head())

    if validate_data(df):
        if st.button("Run Analysis"):
            results = run_simulation(df, runs)

            summary = results.groupby("decision").agg(
                expected_value=("value", "mean"),
                success_rate=("success", "mean"),
                avg_cost=("value", "median")
            ).reset_index()

            st.subheader("📑 Summary")
            st.dataframe(summary)

            st.subheader("📊 Visualizations")

            # KDE
            fig, ax = plt.subplots()
            sns.kdeplot(data=results, x="value", hue="decision", fill=True, ax=ax)
            render_and_download(fig, "kde_plot.png", "KDE Plot: Value Distribution per Decision")

            # Bar
            fig, ax = plt.subplots()
            sns.barplot(data=summary, x="decision", y="success_rate", ax=ax)
            render_and_download(fig, "success_rate.png", "Success Rate by Decision")

            # Boxplot
            fig, ax = plt.subplots()
            sns.boxplot(data=results, x="decision", y="value", ax=ax)
            render_and_download(fig, "boxplot.png", "Boxplot of Decision Values")

            # Histogram
            fig, ax = plt.subplots()
            sns.histplot(data=results, x="value", hue="decision", element="step", bins=30, ax=ax)
            render_and_download(fig, "histogram.png", "Histogram of Values")

            # Scatter
            fig, ax = plt.subplots()
            ax.scatter(summary["expected_value"], summary["success_rate"])
            for i, row in summary.iterrows():
                ax.text(row["expected_value"], row["success_rate"], row["decision"])
            ax.set_xlabel("Expected Value")
            ax.set_ylabel("Success Rate")
            render_and_download(fig, "scatter.png", "Scatter Plot: EV vs Success Rate")

            # Reports
            st.subheader("📥 Reports")
            pdf_buffer = generate_pdf_report(summary, lang)
            excel_buffer = generate_excel_report(summary)

            st.download_button("⬇️ Download PDF Report", pdf_buffer, file_name="decision_report.pdf")
            st.download_button("⬇️ Download Excel Report", excel_buffer, file_name="decision_report.xlsx")
            st.download_button("⬇️ Download CSV Summary", summary.to_csv(index=False).encode("utf-8"), file_name="decision_summary.csv", mime="text/csv")
