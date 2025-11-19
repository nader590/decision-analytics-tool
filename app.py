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

sns.set_style("whitegrid")

# =========================================
#       Template CSV Helper
# =========================================
def get_template_df():
    """
    يبني قالب CSV جاهز يقدر المستخدم يحمله ويعدّل عليه.
    """
    data = [
        {
            "decision": "Option A",
            "distribution": "normal",
            "params": '{"mean": 100, "std": 20}',
            "success_prob": 0.7,
        },
        {
            "decision": "Option B",
            "distribution": "uniform",
            "params": '{"low": 50, "high": 150}',
            "success_prob": 0.6,
        },
        {
            "decision": "Option C",
            "distribution": "triangular",
            "params": '{"left": 40, "mode": 90, "right": 160}',
            "success_prob": 0.8,
        },
    ]
    return pd.DataFrame(data)

# =========================================
#           Helper: Parse Params
# =========================================
def parse_params(raw, decision, ui_lang="en"):
    """
    يحاول قراءة عمود params كـ JSON مع معالجة أبسط للأخطاء.
    """
    if pd.isna(raw):
        if ui_lang == "ar":
            raise ValueError(f"❌ المعاملات (params) مفقودة في القرار '{decision}'")
        else:
            raise ValueError(f"❌ Missing params for decision '{decision}'")

    s = str(raw).strip()
    # محاولة أولى: JSON طبيعي
    try:
        return json.loads(s)
    except Exception:
        # محاولة ثانية: استبدال ' بـ "
        try:
            return json.loads(s.replace("'", '"'))
        except Exception as e:
            if ui_lang == "ar":
                raise ValueError(
                    f"❌ المعاملات (params) ليست JSON صالح للقرار {decision}: {e}"
                )
            else:
                raise ValueError(
                    f"❌ Params not valid JSON for decision {decision}: {e}"
                )

# =========================================
#           Data Validation
# =========================================
def validate_data(df, ui_lang="en"):
    required_cols = ["decision", "distribution", "params", "success_prob"]
    errors = []

    # التحقق من الأعمدة المطلوبة
    for col in required_cols:
        if col not in df.columns:
            if ui_lang == "ar":
                errors.append(f"❌ العمود المطلوب مفقود: {col}")
            else:
                errors.append(f"❌ Missing required column: {col}")

    if errors:
        for e in errors:
            st.error(e)
        return False

    # التحقق من صفوف البيانات
    for _, row in df.iterrows():
        decision = row.get("decision", "UNKNOWN" if ui_lang == "en" else "غير معروف")

        # التحقق من success_prob (رقم بين 0 و 1)
        try:
            p = float(row["success_prob"])
            if not (0 <= p <= 1):
                if ui_lang == "ar":
                    errors.append(
                        f"❌ قيمة success_prob في القرار '{decision}' يجب أن تكون بين 0 و 1"
                    )
                else:
                    errors.append(
                        f"❌ success_prob in decision '{decision}' must be between 0 and 1"
                    )
        except Exception:
            if ui_lang == "ar":
                errors.append(
                    f"❌ لا يمكن تحويل success_prob إلى رقم في القرار '{decision}'"
                )
            else:
                errors.append(
                    f"❌ Cannot convert success_prob to number in decision '{decision}'"
                )

        # التحقق من params
        try:
            parse_params(row["params"], decision, ui_lang=ui_lang)
        except Exception as e:
            errors.append(str(e))

    if errors:
        for e in errors:
            st.error(e)
        return False

    return True

# =========================================
#           Simulation Engine
# =========================================
def run_simulation(data, n_simulations=1000, ui_lang="en"):
    results = []
    for _, row in data.iterrows():
        decision = str(row['decision'])
        dist = str(row['distribution']).strip().lower()
        params = parse_params(row["params"], decision, ui_lang=ui_lang)
        p_success = float(row["success_prob"])

        if dist == "normal":
            values = np.random.normal(params['mean'], params['std'], n_simulations)
        elif dist == "uniform":
            values = np.random.uniform(params['low'], params['high'], n_simulations)
        elif dist == "triangular":
            values = np.random.triangular(
                params['left'], params['mode'], params['right'], n_simulations
            )
        elif dist == "beta":
            values = np.random.beta(
                params['a'], params['b'], n_simulations
            ) * params.get('scale', 1)
        elif dist == "exponential":
            values = np.random.exponential(params['scale'], n_simulations)
        elif dist == "lognormal":
            values = np.random.lognormal(params['mean'], params['sigma'], n_simulations)
        elif dist == "poisson":
            values = np.random.poisson(params['lam'], n_simulations)
        elif dist == "gamma":
            values = np.random.gamma(params['shape'], params['scale'], n_simulations)
        elif dist in ["chi-square", "chisquare", "chi2"]:
            values = np.random.chisquare(params['df'], n_simulations)
        elif dist == "binomial":
            values = np.random.binomial(params['n'], params['p'], n_simulations)
        else:
            if ui_lang == "ar":
                raise ValueError(f"❌ نوع التوزيع غير مدعوم: {dist}")
            else:
                raise ValueError(f"❌ Unsupported distribution: {dist}")

        # محاكاة النجاح/الفشل
        success = np.random.binomial(1, p_success, n_simulations)

        results.append(pd.DataFrame({
            "decision": decision,
            "value": values,
            "success": success
        }))

    return pd.concat(results, ignore_index=True)

# =========================================
#           Visualization Helper
# =========================================
def render_and_download(fig, filename, caption, ui_lang="en"):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    st.image(buf, caption=caption)
    label = f"⬇️ Download {filename}" if ui_lang == "en" else f"⬇️ تحميل {filename}"
    st.download_button(
        label=label,
        data=buf,
        file_name=filename,
        mime="image/png"
    )
    plt.close(fig)

# =========================================
#           Reports
# =========================================
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
            txt = (
                f"الخيار: {row['decision']} - "
                f"القيمة المتوقعة: {row['expected_value']:.2f} - "
                f"معدل النجاح: {row['success_rate']:.2f} - "
                f"الانحراف المعياري: {row['std_value']:.2f}"
            )
        else:
            txt = (
                f"Decision: {row['decision']} - "
                f"Expected Value: {row['expected_value']:.2f} - "
                f"Success Rate: {row['success_rate']:.2f} - "
                f"Std Dev: {row['std_value']:.2f}"
            )
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

# =========================================
#           Main Streamlit App
# =========================================
def main():
    st.set_page_config(page_title="Decision Analytics", layout="wide")

    ui_lang = st.radio(
        "UI Language / لغة الواجهة",
        ["en", "ar"],
        index=0,
        horizontal=True,
        format_func=lambda x: "English" if x == "en" else "العربية"
    )

    # نصوص حسب لغة الواجهة
    if ui_lang == "en":
        st.title("📈 Decision Analytics Tool")
        upload_label = "Upload your CSV"
        runs_label = "Number of simulations per decision"
        pdf_lang_label = "PDF report language"
        preview_label = "Preview:"
        run_button_label = "🚀 Run Analysis"
        spinner_text = "Running simulations and generating results..."
        summary_title = "📑 Summary"
        charts_title = "📊 Visualizations"
        select_decisions_title = "🎯 Select decisions to display"
        select_decisions_label = "Choose decisions for plots:"
        no_data_warning = "⚠ No data for the selected decisions."
        reports_title = "📥 Reports"
        pdf_button_label = "⬇️ Download PDF report"
        excel_button_label = "⬇️ Download Excel report"
        csv_button_label = "⬇️ Download CSV summary"
        template_title = "📥 Download CSV Template"
        template_button = "⬇️ Download sample CSV template"
    else:
        st.title("📈 أداة تحليل القرارات")
        upload_label = "📤 ارفع ملف CSV الخاص بك"
        runs_label = "🔁 عدد المحاكاة لكل قرار"
        pdf_lang_label = "📝 لغة تقرير الـ PDF"
        preview_label = "👀 معاينة أولية للبيانات:"
        run_button_label = "🚀 تشغيل التحليل"
        spinner_text = "⏳ يتم الآن تشغيل المحاكاة وتحليل النتائج..."
        summary_title = "📑 ملخص القرارات"
        charts_title = "📊 الرسوم البيانية"
        select_decisions_title = "🎯 اختر القرارات للعرض"
        select_decisions_label = "اختر القرارات التي تريد عرضها في الرسوم:"
        no_data_warning = "⚠ لا توجد بيانات للقرارات المختارة."
        reports_title = "📥 تحميل التقارير"
        pdf_button_label = "⬇️ تحميل تقرير PDF"
        excel_button_label = "⬇️ تحميل تقرير Excel"
        csv_button_label = "⬇️ تحميل ملخص CSV"
        template_title = "📥 تحميل قالب CSV جاهز"
        template_button = "⬇️ تحميل قالب CSV تجريبي"

    # === زر تحميل قالب CSV ===
    st.markdown(f"### {template_title}")
    template_df = get_template_df()
    st.download_button(
        template_button,
        template_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="decision_template.csv",
        mime="text/csv"
    )

    uploaded_file = st.file_uploader(upload_label, type="csv")
    runs = st.slider(runs_label, 100, 5000, 1000, step=100)

    pdf_lang = st.radio(
        pdf_lang_label,
        ["en", "ar"],
        index=0,
        horizontal=True,
        format_func=lambda x: "English" if x == "en" else "العربية"
    )

    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"Error reading CSV: {e}")
            return

        st.write(preview_label, df.head())

        if validate_data(df, ui_lang=ui_lang):
            if st.button(run_button_label):
                with st.spinner(spinner_text):
                    try:
                        results = run_simulation(df, runs, ui_lang=ui_lang)
                    except Exception as e:
                        st.error(str(e))
                        return

                    summary = results.groupby("decision").agg(
                        expected_value=("value", "mean"),
                        success_rate=("success", "mean"),
                        avg_cost=("value", "median"),
                        std_value=("value", "std"),
                        min_value=("value", "min"),
                        max_value=("value", "max"),
                        n_obs=("value", "count")
                    ).reset_index()

                st.subheader(summary_title)
                st.dataframe(summary)

                # اختيار القرارات للعرض
                st.subheader(select_decisions_title)
                decisions = summary["decision"].unique().tolist()

                selected_decisions = st.multiselect(
                    select_decisions_label,
                    options=decisions,
                    default=decisions
                )

                filtered_results = results[results["decision"].isin(selected_decisions)]
                filtered_summary = summary[summary["decision"].isin(selected_decisions)]

                if filtered_results.empty:
                    st.warning(no_data_warning)
                    return

                st.subheader(charts_title)

                # ========== ECDF ==========
                fig, ax = plt.subplots()
                sns.ecdfplot(data=filtered_results, x="value", hue="decision", ax=ax)
                if ui_lang == "en":
                    ax.set_title("ECDF - Cumulative distribution of values")
                    ax.set_xlabel("Value")
                    ax.set_ylabel("Cumulative probability")
                    caption = "ECDF of values per decision"
                else:
                    ax.set_title("التوزيع التراكمي للقيم (ECDF)")
                    ax.set_xlabel("القيمة")
                    ax.set_ylabel("الاحتمال التراكمي")
                    caption = "التوزيع التراكمي للقيم لكل قرار (ECDF)"
                render_and_download(fig, "ecdf_plot.png", caption, ui_lang=ui_lang)

                # ========== KDE ==========
                fig, ax = plt.subplots()
                sns.kdeplot(data=filtered_results, x="value", hue="decision", fill=True, ax=ax)
                if ui_lang == "en":
                    ax.set_title("KDE - Value distribution per decision")
                    ax.set_xlabel("Value")
                    ax.set_ylabel("Density")
                    caption = "KDE plot of values per decision"
                else:
                    ax.set_title("توزيع القيم لكل قرار (KDE)")
                    ax.set_xlabel("القيمة")
                    ax.set_ylabel("الكثافة")
                    caption = "توزيع القيم لكل قرار (KDE)"
                render_and_download(fig, "kde_plot.png", caption, ui_lang=ui_lang)

                # ========== Histogram ==========
                fig, ax = plt.subplots()
                sns.histplot(
                    data=filtered_results,
                    x="value",
                    hue="decision",
                    element="step",
                    bins=30,
                    ax=ax
                )
                if ui_lang == "en":
                    ax.set_title("Histogram of values")
                    ax.set_xlabel("Value")
                    ax.set_ylabel("Frequency")
                    caption = "Histogram of values per decision"
                else:
                    ax.set_title("الهيستوجرام للقيم")
                    ax.set_xlabel("القيمة")
                    ax.set_ylabel("التكرار")
                    caption = "Histogram للقيم لكل قرار"
                render_and_download(fig, "histogram.png", caption, ui_lang=ui_lang)

                # ========== Boxplot ==========
                fig, ax = plt.subplots()
                sns.boxplot(data=filtered_results, x="decision", y="value", ax=ax)
                if ui_lang == "en":
                    ax.set_title("Boxplot of values per decision")
                    ax.set_xlabel("Decision")
                    ax.set_ylabel("Value")
                    caption = "Boxplot of values per decision"
                else:
                    ax.set_title("صندوق القيم حسب القرار")
                    ax.set_xlabel("القرار")
                    ax.set_ylabel("القيمة")
                    caption = "Boxplot للقيم لكل قرار"
                render_and_download(fig, "boxplot.png", caption, ui_lang=ui_lang)

                # ========== Violin Plot ==========
                fig, ax = plt.subplots()
                sns.violinplot(data=filtered_results, x="decision", y="value", ax=ax, inner="quartile")
                if ui_lang == "en":
                    ax.set_title("Violin plot of value distribution per decision")
                    ax.set_xlabel("Decision")
                    ax.set_ylabel("Value")
                    caption = "Violin plot of values per decision"
                else:
                    ax.set_title("Violin Plot لتوزيع القيم لكل قرار")
                    ax.set_xlabel("القرار")
                    ax.set_ylabel("القيمة")
                    caption = "Violin Plot لتوزيع القيم لكل قرار"
                render_and_download(fig, "violin.png", caption, ui_lang=ui_lang)

                # ========== Barplot (Success Rate) ==========
                fig, ax = plt.subplots()
                sns.barplot(data=filtered_summary, x="decision", y="success_rate", ax=ax)
                if ui_lang == "en":
                    ax.set_title("Success rate by decision")
                    ax.set_xlabel("Decision")
                    ax.set_ylabel("Success rate")
                    caption = "Success rate per decision"
                else:
                    ax.set_title("معدل النجاح حسب القرار")
                    ax.set_xlabel("القرار")
                    ax.set_ylabel("معدل النجاح")
                    caption = "معدل النجاح لكل قرار"
                render_and_download(fig, "success_rate.png", caption, ui_lang=ui_lang)

                # ========== Scatter EV vs Success ==========
                fig, ax = plt.subplots()
                ax.scatter(filtered_summary["expected_value"], filtered_summary["success_rate"])
                for _, row in filtered_summary.iterrows():
                    ax.text(
                        row["expected_value"],
                        row["success_rate"],
                        str(row["decision"])
                    )
                if ui_lang == "en":
                    ax.set_xlabel("Expected value")
                    ax.set_ylabel("Success rate")
                    ax.set_title("Expected value vs Success rate")
                    caption = "Scatter: EV vs Success rate"
                else:
                    ax.set_xlabel("القيمة المتوقعة")
                    ax.set_ylabel("معدل النجاح")
                    ax.set_title("العلاقة بين القيمة المتوقعة ومعدل النجاح")
                    caption = "Scatter: القيمة المتوقعة مقابل معدل النجاح"
                render_and_download(fig, "scatter.png", caption, ui_lang=ui_lang)

                # ========== Reports ==========
                st.subheader(reports_title)
                pdf_buffer = generate_pdf_report(summary, lang=pdf_lang)
                excel_buffer = generate_excel_report(summary)

                st.download_button(
                    pdf_button_label,
                    pdf_buffer,
                    file_name="decision_report.pdf"
                )
                st.download_button(
                    excel_button_label,
                    excel_buffer,
                    file_name="decision_report.xlsx"
                )
                st.download_button(
                    csv_button_label,
                    summary.to_csv(index=False).encode("utf-8"),
                    file_name="decision_summary.csv",
                    mime="text/csv"
                )

if __name__ == "__main__":
    main()
