# 📊 Semiconductor OEE Analytics

Automated semiconductor final-test analytics pipeline built with **Python, Pandas, NumPy, and Plotly**. Integrates equipment-event CSV files and production-test TXT records into hourly KPI datasets, interactive HTML dashboards, and CSV reports.

> Public portfolio data and manufacturing identifiers are anonymized. No proprietary manufacturing or customer-sensitive information is included.

## 🎯 Problem and Engineering Value

Equipment events and production results arrive in separate systems, making downtime and production-loss investigations dependent on manual correlation.

This pipeline matches production lots, standardizes equipment-event categories, and generates unified reports for investigating utilization, throughput, yield, and recurring downtime.

| Area | Previous Workflow | Analytics Platform |
|---|---|---|
| Data correlation | Separate equipment and production files | Lot-matched datasets |
| Downtime investigation | Manual review of individual alarm codes | Standardized event groups and loss summaries |
| Performance monitoring | Daily production reports | Hourly equipment KPIs and seven-day trends |
| Report distribution | Manual consolidation | Automated HTML reports and CSV exports |

## 🚀 Interactive Demos

| Dashboard | Focus | Demo |
|---|---|---|
| Rolling 7-Day Report | OEE, utilization, output attainment, yield, and downtime trends | [Open](https://kenbugasto.github.io/semiconductor-oee-analytics/demo/oee_rolling_7day_report.html) |
| Handler HDLR02 | Previous-day hourly KPIs and equipment losses | [Open](https://kenbugasto.github.io/semiconductor-oee-analytics/demo/oee_per_handler_report_HDLR02.html) |
| Handler HDLR07 | Previous-day hourly KPIs and equipment losses | [Open](https://kenbugasto.github.io/semiconductor-oee-analytics/demo/oee_per_handler_report_HDLR07.html) |

### View the Demos

Open any dashboard link in a web browser. Use Plotly hover tooltips, zoom, and pan to inspect the charts. Standalone HTML reports can also be opened locally without Python or a database connection.

## ⚙️ Automated Workflow

1. Retrieve handler-event CSV files and production-test TXT records from FTP.
2. Validate required columns, normalize timestamps, and clean numeric and missing values.
3. Match production lots and categorize equipment events.
4. Aggregate equipment activity and production results at hourly grain.
5. Calculate KPIs and export interactive HTML dashboards and CSV datasets.

The operational pipeline runs daily at **03:00 through Windows Task Scheduler**, using `config.ini` for configuration. Execution logs and generated reports are reviewed before distribution.

This describes the operational implementation. The browser demos do not require access to the production FTP environment.

## 🧩 Analytical Dataset Design

| Dataset | Contents and Purpose |
|---|---|
| Handler events | Equipment alarms, downtime, machine status, and lot movement from CSV sources |
| Production tests | Unit results, PASS/FAIL status, test times, flows, and sites from TXT sources |
| Standardized and matched data | Normalized timestamps, categorized events, and records scoped to matching production lots |
| Hourly KPI outputs | Equipment-level utilization, throughput, yield, and operational OEE metrics |
| Report outputs | Previous-day handler analysis and rolling seven-day summaries, exported as HTML and CSV |

Hourly datasets preserve visibility into temporary downtime, throughput fluctuations, and yield variation before daily and historical reporting.

## 📈 KPI Definitions

This implementation uses the following operational OEE model:

**OEE = Utilization × Output Attainment × Yield**

Multiply the three factors as fractions; express the result as a percentage.

- **Utilization:** Productive operating time after accounting for equipment downtime.
- **Output attainment:** Actual throughput relative to target manufacturing capacity, capped at 100%.
- **Yield:** PASS units divided by total tested units.

These are the implementation’s metric definitions. Interpretation depends on the configured time basis, capacity targets, and test-record counting rules.

## 🛠️ Engineering Decisions

- **File-based batch processing:** Pandas processes CSV/TXT sources directly without a separate database service.
- **Lot matching:** Connects equipment events and production records for combined analysis.
- **Hourly aggregation:** Retains detail needed to investigate temporary manufacturing losses.
- **Defensive validation:** Includes schema checks, timestamp normalization, missing-value handling, and divide-by-zero protection.
- **Standalone reporting:** Plotly HTML provides interactive charts without a dashboard server.

## 💻 Technology Stack

**Python · Pandas · NumPy · Plotly · HTML · ConfigParser · FTP · Windows Task Scheduler**

## 🛣️ Potential Future Improvements

Engineering filtering: Add equipment, date, and downtime-category filters to help engineers narrow investigations.

SPC integration: Link process-capability results with equipment losses and yield trends to help investigate potential relationships between process variation and manufacturing performance.
