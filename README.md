````md
# 📊 Semiconductor OEE Analytics

Automated **Overall Equipment Effectiveness (OEE)** analytics platform built with **Python**, integrating **handler event logs** and **production test data** to generate interactive HTML reports, manufacturing KPIs, and equipment performance analytics.

---

# 🚀 Project Overview

This project was developed to automate semiconductor manufacturing performance analysis by combining two independent data sources:

- 📄 Handler event logs (CSV)
- 📄 Production test result files (TXT)

The application parses, cleans, matches, and aggregates manufacturing data to calculate equipment utilization, output attainment, yield, downtime, and Overall Equipment Effectiveness (OEE).

The final output consists of interactive HTML dashboards and CSV summary reports that enable engineers to quickly identify productivity losses and equipment performance trends.

---

# ✨ Key Features

✅ Multi-source manufacturing data integration

✅ Automated CSV and TXT parsing

✅ Handler event categorization

✅ Production lot matching

✅ OEE calculation

✅ Utilization analysis

✅ Output Attainment tracking

✅ Yield monitoring

✅ Downtime event analysis

✅ Rolling 7-Day KPI trending

✅ Interactive Plotly HTML reports

✅ CSV summary exports

---

# 🏗️ Project Workflow

```text
Handler CSV Logs
        │
        ▼
Production TXT Files
        │
        ▼
Data Cleaning & Standardization
        │
        ▼
Lot Matching
        │
        ▼
Hourly Aggregation
        │
        ▼
OEE KPI Calculation
        │
        ▼
Downtime Analysis
        │
        ▼
Rolling Trend Analysis
        │
        ▼
Interactive HTML Reports
```

---

# 📈 OEE Calculation

Overall Equipment Effectiveness (OEE) is calculated using:

```text
OEE = Utilization × Output Attainment × Yield
```

### 🟢 Utilization

Represents productive operating time after equipment downtime.

```text
Utilization =
Available Production Time
────────────────────────
Total Scheduled Time
```

---

### 🔵 Output Attainment

Measures actual production output relative to the calculated target throughput.

```text
Output Attainment =
Actual Output
──────────────
Target Output
```

---

### 🟣 Yield

Measures manufacturing quality.

```text
Yield =
PASS Units
────────────
Total Units
```

---

# 📊 Generated Reports

The application automatically generates:

## 📅 24-Hour Overall OEE Report

- KPI Gauges
- Hourly Output
- Efficiency Breakdown
- Downtime Summary

---

## 🔧 Per Handler Report

Generated for every handler.

Includes:

- Handler KPI Dashboard
- Hourly Production
- Downtime Events
- Loss Analysis

---

## 📈 Rolling 7-Day Report

Historical trend analysis including:

- Daily OEE
- Output Attainment
- Utilization
- Yield
- Top Downtime Events
- Trend Comparison

---

# 📁 Repository Structure

```text
semiconductor-oee-analytics/

│
├── demo/
│   ├── overall_report.html
│   ├── handler_report.html
│   └── rolling_7day_report.html
│
├── screenshots/
│
├── src/
│   ├── OEE_analysis_script.py
│   └── oee_config_template.ini
│
├── README.md
├── requirements.txt
└── .gitignore
```

---

# 📷 Screenshots

## 📊 Overall Dashboard

*(Insert screenshot here)*

---

## 🔧 Handler Dashboard

*(Insert screenshot here)*

---

## 📈 Rolling 7-Day Dashboard

*(Insert screenshot here)*

---

# 🛠️ Technologies Used

| Technology | Purpose |
|------------|---------|
| Python | Data Processing |
| Pandas | ETL & Data Transformation |
| NumPy | Numerical Calculations |
| Plotly | Interactive HTML Visualizations |
| ConfigParser | Configuration Management |
| FTP | Automated Manufacturing Data Retrieval |

---

# 📦 Outputs

Generated outputs include:

- 📄 HTML dashboards
- 📄 Production summaries
- 📄 Hourly equipment reports
- 📄 Downtime summaries
- 📄 Lot summaries
- 📄 Site summaries
- 📄 Handler event analytics

---

# 🎯 Future Improvements

Planned enhancements include:

- 🚀 Apache Spark implementation for large-scale manufacturing datasets
- 🏅 Medallion Architecture (Bronze / Silver / Gold)
- 🗄️ Delta Lake / DuckDB historical storage
- 📡 Live Streamlit monitoring dashboard
- 📉 SPC metrics (Cp, Cpk, Cpu, Cpl)
- 🤖 Predictive equipment downtime using Machine Learning
- 📧 Automated scheduled report distribution

---

# 👨‍💻 Author

This project was developed as part of a manufacturing analytics and data engineering portfolio, demonstrating end-to-end ETL development, manufacturing KPI computation, automated reporting, and production data visualization using Python.
````
