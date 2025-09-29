📊 Decision Analytics Simulator
🚀 Overview

Decision Analytics Simulator is a tool designed for scientific researchers and analysts to perform Monte Carlo simulations on decision-making problems using various probability distributions.
It generates summaries, visualizations, and reports (PDF + Excel + CSV) in both English and Arabic.

🛠 Features

Supports 10 probability distributions:

Normal, Uniform, Triangular, Beta, Exponential, Lognormal, Poisson, Gamma, Chi-square, Binomial

Data validation (ensures all required columns and parameters are valid).

Configurable number of simulations (default = 1000).

Results summary including:

Expected value

Success rate

Average cost

Visualizations:

KDE plot

Bar chart

Histogram

Boxplot

Pie chart

Scatter plot

Tornado chart

Reports:

PDF (Arabic or English)

Excel (with raw data + summary)

CSV (summary only)

📂 Project Structure
.
├── decision_analytics.py    # Main code
├── requirements.txt         # Dependencies
├── data/
│   └── example.csv          # Example dataset
└── README.md                # This file

📦 Installation

Clone or download the project:

git clone https://github.com/<your-org>/decision-analytics-tool.git
cd decision-analytics-tool


Install required dependencies:

pip install -r requirements.txt

📊 Example Input (CSV)

data/example.csv

decision,distribution,params,success_prob
Option A,normal,"{'mean': 50, 'std': 10}",0.7
Option B,uniform,"{'low': 20, 'high': 80}",0.6
Option C,triangular,"{'left': 10, 'mode': 30, 'right': 50}",0.8
Option D,beta,"{'a': 2, 'b': 5, 'scale': 100}",0.5
Option E,poisson,"{'lam': 5}",0.4
Option F,exponential,"{'scale': 10}",0.5
Option G,lognormal,"{'mean': 0, 'sigma': 0.25}",0.6
Option H,gamma,"{'shape': 2, 'scale': 2}",0.5
Option I,chisquare,"{'df': 3}",0.6
Option J,binomial,"{'n': 10, 'p': 0.5}",0.7

▶️ Usage
Run Simulation
python decision_analytics.py --input data/example.csv --runs 5000 --lang en --outdir results

Arguments

--input : Path to input CSV file (required).

--runs : Number of simulations (default = 1000).

--lang : Report language ar (Arabic) or en (English).

--outdir : Output folder for results (default = results).

📑 Output

After running, the tool will generate in results/:

decision_summary.csv → Summary table

decision_report.pdf → PDF report (Arabic/English)

decision_report.xlsx → Excel report

Visualizations (PNG):

kde_plot.png

success_bar.png

histogram.png

boxplot.png

pie_chart.png

scatter_plot.png

tornado_chart.png

👨‍💻 Example Workflow
# Quick test
python decision_analytics.py --input data/example.csv --runs 2000 --lang ar --outdir output_test


This will generate:

Arabic PDF report

Excel report

CSV summary

Visualization charts

📚 Requirements

Listed in requirements.txt:

pandas
numpy
matplotlib
seaborn
reportlab
openpyxl

📝 Notes

The params column must be written in JSON-like format (single quotes are allowed, e.g. {'mean': 50, 'std': 10}).

success_prob must always be between 0 and 1.

You can add any number of decisions or supported distributions.
