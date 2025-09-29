import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
import seaborn as sns
import os
import argparse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
import io
from openpyxl import Workbook


# ============== Data Validation ==============
def validate_data(df):
    required_cols = ["decision", "distribution", "params", "success_prob"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"❌ Missing required column: {col}")

    for _, row in df.iterrows():
        if not (0 <= row["success_prob"] <= 1):
            raise ValueError(f"❌ Invalid success_prob in decision {row['decision']}")

        try:
            params = json.loads(row["params"].replace("'", '"'))
        except Exception as e:
            raise ValueError(f"❌ Params not valid JSON for {row['decision']}: {e}")

    return True


# ============== Simulation Engine ==============
def run_simulation(data, n_simulations=1000):
    results = []

    for _, row in data.iterrows():
        decision = str(row['decision'])
        dist = str(row['distribution']).lower()
        params = json.loads(row['params'].replace("'", '"'))
        p_success = float(row['success_prob'])

        # distributions
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


# ============== Visualizations ==============
def generate_visualizations(results, summary, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    # KDE Plot
    plt.figure()
    sns.kdeplot(data=results, x="value", hue="decision", fill=True)
    plt.title("Value Distribution per Decision")
    plt.savefig(f"{output_dir}/kde_plot.png")
    plt.close()

    # Bar Plot Success Rate
    plt.figure()
    sns.barplot(data=summary, x="decision", y="success_rate")
    plt.title("Success Rate by Decision")
    plt.savefig(f"{output_dir}/success_rate.png")
    plt.close()

    # Boxplot
    plt.figure()
    sns.boxplot(data=results, x="decision", y="value")
    plt.title("Boxplot of Decision Values")
    plt.savefig(f"{output_dir}/boxplot.png")
    plt.close()

    # Histogram
    plt.figure()
    sns.histplot(data=results, x="value", hue="decision", element="step", bins=30)
    plt.title("Histogram of Values")
    plt.savefig(f"{output_dir}/histogram.png")
    plt.close()

    # Pie chart success rate
    plt.figure()
    plt.pie(summary["success_rate"], labels=summary["decision"], autopct='%1.1f%%')
    plt.title("Success Rate Distribution")
    plt.savefig(f"{output_dir}/pie_chart.png")
    plt.close()

    # Scatter plot (expected value vs success rate)
    plt.figure()
    plt.scatter(summary["expected_value"], summary["success_rate"])
    for i, row in summary.iterrows():
        plt.text(row["expected_value"], row["success_rate"], row["decision"])
    plt.xlabel("Expected Value")
    plt.ylabel("Success Rate")
    plt.title("Scatter Plot: EV vs Success Rate")
    plt.savefig(f"{output_dir}/scatter.png")
    plt.close()


# ============== PDF Report ==============
def generate_pdf_report(summary_df, output_path, lang="en"):
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
    with open(output_path, "wb") as f:
        f.write(buffer.getvalue())


# ============== Excel Report ==============
def generate_excel_report(summary_df, output_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"

    ws.append(summary_df.columns.tolist())
    for _, row in summary_df.iterrows():
        ws.append(row.tolist())

    wb.save(output_path)


# ============== Main CLI ==============
def main():
    parser = argparse.ArgumentParser(description="Decision Analytics Simulator")
    parser.add_argument("--input", required=True, help="Path to CSV file with decisions")
    parser.add_argument("--runs", type=int, default=1000, help="Number of simulations")
    parser.add_argument("--lang", choices=["en", "ar"], default="en", help="Report language")
    parser.add_argument("--outdir", default="output", help="Output directory")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    print("📂 Loading data...")
    df = pd.read_csv(args.input)

    print("✅ Validating data...")
    validate_data(df)

    print("🎲 Running simulations...")
    results = run_simulation(df, args.runs)

    print("📊 Summarizing results...")
    summary = results.groupby("decision").agg(
        expected_value=("value", "mean"),
        success_rate=("success", "mean"),
        avg_cost=("value", "median")
    ).reset_index()

    print("📈 Generating visualizations...")
    generate_visualizations(results, summary, args.outdir)

    print("📝 Generating reports...")
    generate_pdf_report(summary, f"{args.outdir}/decision_report.pdf", args.lang)
    generate_excel_report(summary, f"{args.outdir}/decision_report.xlsx")

    summary.to_csv(f"{args.outdir}/decision_summary.csv", index=False)

    print(f"🎉 Done! Reports saved in {args.outdir}/")


if __name__ == "__main__":
    main()
