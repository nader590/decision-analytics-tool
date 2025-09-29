import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
from scipy.stats import norm, uniform, triang, beta, expon, lognorm, poisson, gamma, chi2, binom
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import openpyxl

# ---------------------------
# 1. Validation Function
# ---------------------------
def validate_data(df):
    errors = []
    required_cols = ["decision", "distribution", "params", "success_rate"]

    for col in required_cols:
        if col not in df.columns:
            errors.append(f"Missing column: {col}")

    for i, row in df.iterrows():
        if pd.isnull(row["decision"]) or pd.isnull(row["distribution"]):
            errors.append(f"Row {i}: Missing decision or distribution")

        # success_rate بين 0 و 1
        try:
            sr = float(row["success_rate"])
            if sr < 0 or sr > 1:
                errors.append(f"Row {i}: success_rate out of range [0,1]")
        except:
            errors.append(f"Row {i}: success_rate not numeric")

        # params لازم JSON
        try:
            json.loads(row["params"].replace("'", '"'))
        except:
            errors.append(f"Row {i}: Invalid params format")

    return (len(errors) == 0, errors)


# ---------------------------
# 2. Distribution Sampling
# ---------------------------
def sample_distribution(dist_name, params, n):
    if dist_name.lower() == "normal":
        return np.random.normal(params["mu"], params["sigma"], n)
    elif dist_name.lower() == "uniform":
        return np.random.uniform(params["low"], params["high"], n)
    elif dist_name.lower() == "triangular":
        return np.random.triangular(params["left"], params["mode"], params["right"], n)
    elif dist_name.lower() == "beta":
        return np.random.beta(params["a"], params["b"], n)
    elif dist_name.lower() == "exponential":
        return np.random.exponential(params["scale"], n)
    elif dist_name.lower() == "lognormal":
        return np.random.lognormal(params["mean"], params["sigma"], n)
    elif dist_name.lower() == "poisson":
        return np.random.poisson(params["lam"], n)
    elif dist_name.lower() == "gamma":
        return np.random.gamma(params["shape"], params["scale"], n)
    elif dist_name.lower() == "chi-square":
        return np.random.chisquare(params["df"], n)
    elif dist_name.lower() == "binomial":
        return np.random.binomial(params["n"], params["p"], n)
    else:
        raise ValueError(f"Unsupported distribution: {dist_name}")


# ---------------------------
# 3. Simulation Function
# ---------------------------
def run_simulation(df, n_simulations=1000):
    results = {}
    summary = []

    for _, row in df.iterrows():
        params = json.loads(row["params"].replace("'", '"'))
        samples = sample_distribution(row["distribution"], params, n_simulations)

        # success rate application
        mask = np.random.rand(n_simulations) < float(row["success_rate"])
        samples = np.where(mask, samples, 0)

        results[row["decision"]] = samples
        summary.append({
            "decision": row["decision"],
            "expected_value": np.mean(samples),
            "std_dev": np.std(samples),
            "success_rate": row["success_rate"]
        })

    return results, pd.DataFrame(summary)


# ---------------------------
# 4. Visualization Functions
# ---------------------------
def generate_visualizations(results, prefix="scenario1"):
    os.makedirs(f"{prefix}_charts", exist_ok=True)

    for decision, data in results.items():
        plt.figure()
        sns.histplot(data, kde=True)
        plt.title(f"Histogram - {decision}")
        plt.savefig(f"{prefix}_charts/{decision}_hist.png")
        plt.close()

        plt.figure()
        sns.boxplot(x=data)
        plt.title(f"Boxplot - {decision}")
        plt.savefig(f"{prefix}_charts/{decision}_box.png")
        plt.close()

    # Pie chart (expected values share)
    means = {d: np.mean(v) for d, v in results.items()}
    plt.figure()
    plt.pie(means.values(), labels=means.keys(), autopct="%1.1f%%")
    plt.title("Expected Value Share")
    plt.savefig(f"{prefix}_charts/pie.png")
    plt.close()

    # Scatter plot (expected vs std_dev)
    plt.figure()
    exp_vals = [np.mean(v) for v in results.values()]
    stds = [np.std(v) for v in results.values()]
    plt.scatter(exp_vals, stds)
    for i, d in enumerate(results.keys()):
        plt.text(exp_vals[i], stds[i], d)
    plt.xlabel("Expected Value")
    plt.ylabel("Std Dev")
    plt.title("Scatter: Expected Value vs Std Dev")
    plt.savefig(f"{prefix}_charts/scatter.png")
    plt.close()

    # Tornado chart
    summary = pd.DataFrame({"Decision": list(results.keys()),
                            "Mean": exp_vals,
                            "StdDev": stds})
    summary_sorted = summary.sort_values("Mean", ascending=False)
    plt.figure()
    plt.barh(summary_sorted["Decision"], summary_sorted["Mean"])
    plt.xlabel("Expected Value")
    plt.title("Tornado Chart")
    plt.savefig(f"{prefix}_charts/tornado.png")
    plt.close()


# ---------------------------
# 5. Reports (PDF + Excel)
# ---------------------------
def generate_reports(results, summary_df, lang="en", prefix="scenario1"):
    # Excel Report
    excel_file = f"{prefix}_summary.xlsx"
    with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
        summary_df.to_excel(writer, index=False, sheet_name="Summary")
        for decision, data in results.items():
            pd.DataFrame(data, columns=[decision]).to_excel(writer, index=False, sheet_name=decision)

    # PDF Report
    pdf_file = f"{prefix}_report.pdf"
    doc = SimpleDocTemplate(pdf_file, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    title = "Simulation Report" if lang == "en" else "تقرير المحاكاة"
    elements.append(Paragraph(title, styles["Title"]))
    elements.append(Spacer(1, 12))

    # Summary table
    table_data = [summary_df.columns.tolist()] + summary_df.values.tolist()
    table = Table(table_data)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                               ("GRID", (0, 0), (-1, -1), 1, colors.black)]))
    elements.append(table)
    elements.append(Spacer(1, 12))

    # Insert images
    chart_dir = f"{prefix}_charts"
    for img_file in ["pie.png", "scatter.png", "tornado.png"]:
        if os.path.exists(f"{chart_dir}/{img_file}"):
            elements.append(RLImage(f"{chart_dir}/{img_file}", width=400, height=300))
            elements.append(Spacer(1, 12))

    doc.build(elements)

    return excel_file, pdf_file
