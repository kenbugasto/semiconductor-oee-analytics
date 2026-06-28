````md
# 📊 Semiconductor OEE Analytics

> **Note:** All data, device names, handler names, production lots, stations, event categories, and identifiers shown in this repository have been fully anonymized for public portfolio usage. No proprietary manufacturing or customer-sensitive information is included.

Production-style semiconductor manufacturing analytics platform built using **Python**, **Pandas**, **NumPy**, and **Plotly**.

---

# 🔎 Overview

This project is an end-to-end semiconductor manufacturing analytics solution that automates the integration of equipment event logs and production test records into engineering-ready OEE reports and manufacturing KPI dashboards.

The solution demonstrates a complete local analytics pipeline built using modern data engineering principles, including:

* Automated multi-source file ingestion
* ETL transformation
* Data validation and standardization
* Production lot matching
* Manufacturing KPI calculation
* Interactive HTML report generation
* Automated CSV analytics exports

The analytics workflow was designed around semiconductor final-test operations, supporting engineering investigations such as equipment utilization, production throughput, downtime analysis, yield monitoring, and Overall Equipment Effectiveness (OEE).

---

# 🚀 Interactive HTML Report Demo

This project generates standalone interactive HTML reports that allow engineers and stakeholders to review manufacturing performance without requiring Python, databases, or BI software.

The sample reports below are generated using fully anonymized manufacturing data.

## 📊 Overall 24-Hour OEE Report

Daily manufacturing dashboard featuring:

* OEE KPI gauges
* Hourly production output
* Equipment utilization
* Output attainment
* Yield monitoring
* Downtime loss analysis

**🌐 Launch Interactive Demo**

```
demo/oee_overall_report.html
```

---

## 🔧 Per Handler OEE Report

Equipment-level performance report including:

* Handler KPI dashboard
* Hourly production analysis
* Equipment downtime
* Downtime event distribution
* Handler-specific loss analysis

**🌐 Launch Interactive Demo**

```
demo/oee_per_handler_report.html
```

---

## 📈 Rolling 7-Day OEE Report

Historical manufacturing performance dashboard including:

* Daily OEE trend
* Output Attainment trend
* Utilization trend
* Yield trend
* Top downtime events
* Performance comparison across seven production days

**🌐 Launch Interactive Demo**

```
demo/oee_rolling_7day_report.html
```

---

# 🗂️ Data Sources

The analytics platform integrates two independent manufacturing data sources.

### Handler Event Logs

* CSV event logs
* Equipment alarms
* Downtime events
* Machine status
* Lot movement information

---

### Production Test Logs

* TXT production files
* Unit-level test results
* PASS / FAIL status
* Test time
* Flow information
* Site information

The ETL pipeline combines both datasets into a unified manufacturing analytics model used for KPI calculation and reporting.

---

# ⭐ Core Features

## ETL / Data Engineering

* Automated multi-source file ingestion
* CSV and TXT parsing
* Manufacturing data standardization
* Production lot matching
* Configuration-driven architecture
* Automated HTML report generation
* CSV analytics exports

---

## Manufacturing Analytics

* Overall Equipment Effectiveness (OEE)
* Equipment Utilization
* Output Attainment
* Yield monitoring
* Downtime categorization
* Handler performance analysis
* Hourly production monitoring
* Lot-level production analysis

---

## Long-Term Manufacturing Trend Analytics

Includes:

* Rolling 7-Day OEE monitoring
* Daily KPI trend analysis
* Historical downtime comparison
* Equipment performance trend monitoring
* Manufacturing productivity analysis

---

# 🛠️ Technology Stack

| Category | Technology |
|-----------|------------|
| Language | Python |
| Data Processing | Pandas |
| Numerical Computing | NumPy |
| Visualization | Plotly |
| Reporting | HTML |
| Configuration | ConfigParser |
| Data Transfer | FTP |
| Scheduling | Windows Task Scheduler |

---

# 🏗️ Architecture & Technology Decisions

## Why Python

Python was selected because it provides a complete ecosystem for ETL development, manufacturing analytics, numerical computation, and automated reporting within a lightweight deployment model.

Benefits include:

* Mature data processing ecosystem
* Excellent ETL capabilities
* Strong numerical computing libraries
* Interactive visualization
* Easy automation
* Minimal deployment requirements

---

## Why Plotly HTML Reports

Interactive Plotly HTML reports were selected because they allow engineers to explore manufacturing KPIs directly within a web browser without requiring dashboard servers or commercial BI platforms.

Benefits include:

* Standalone deployment
* Interactive charts
* Zooming and filtering
* Browser-based sharing
* Lightweight reporting

---

# 🔄 ETL Workflow

Although implemented locally using Python rather than distributed data platforms, the solution follows a structured ETL workflow.

```
Handler CSV Logs
        │
        ▼
Production TXT Files
        │
        ▼
Data Cleaning
        │
        ▼
Standardization
        │
        ▼
Production Lot Matching
        │
        ▼
Hourly Aggregation
        │
        ▼
KPI Calculation
        │
        ▼
OEE Analytics
        │
        ▼
HTML Reports + CSV Exports
```

*(Workflow diagram to be added.)*

---

# 📈 OEE Calculation

The application calculates Overall Equipment Effectiveness using three manufacturing KPIs.

```
OEE

=

Utilization

×

Output Attainment

×

Yield
```

### Utilization

Represents productive operating time after accounting for equipment downtime.

### Output Attainment

Measures actual production throughput relative to calculated target capacity.

### Yield

Measures manufacturing quality using PASS versus total tested units.

---

# 🐍 Production Python ETL Design

The ETL pipeline was designed using defensive programming principles suitable for production manufacturing environments.

Key capabilities include:

* Automated FTP data retrieval
* Multi-format file parsing
* Timestamp normalization
* Equipment event categorization
* Production lot matching
* Hourly KPI aggregation
* Automated report generation
* CSV export automation

The pipeline performs extensive validation before generating engineering-ready analytical datasets.

---

# 📊 Engineering Highlights

The project demonstrates several production-oriented data engineering concepts.

### Data Engineering

* Multi-source ETL
* Configuration-driven architecture
* Defensive ETL design
* Data validation
* Automated reporting
* Manufacturing data integration

### Manufacturing Analytics

* Overall Equipment Effectiveness (OEE)
* Equipment utilization
* Production throughput analysis
* Downtime analysis
* Rolling KPI monitoring
* Yield analytics

### Software Engineering

* Modular Python architecture
* Reusable helper functions
* Separation of concerns
* Automated report generation
* Configurable deployment

---

# 🖼️ Report Screenshots

The following screenshots demonstrate the analytical outputs generated by the ETL pipeline.

## 📊 Overall OEE Dashboard

*(Insert screenshot)*

---

## 🔧 Per Handler Dashboard

*(Insert screenshot)*

---

## 📈 Rolling 7-Day Dashboard

*(Insert screenshot)*

---

# 🛣️ Project Roadmap

## Current Features

* Automated CSV/TXT ingestion
* Equipment event analytics
* Production lot matching
* OEE calculation
* Rolling KPI analysis
* HTML report generation
* CSV export automation

---

# 🎯 Key Engineering Concepts Demonstrated

### Data Engineering

* Multi-source ETL pipelines
* Manufacturing data integration
* Defensive ETL design
* Configuration-driven architecture
* Automated reporting

### Analytics Engineering

* Manufacturing KPI modeling
* OEE calculation
* Time-series trend analysis
* Equipment performance analytics
* Downtime analytics

### Software Engineering

* Modular Python design
* Reusable ETL components
* Automated HTML reporting
* Separation of concerns
* Maintainable project architecture

---

## 👤 Author

This repository was developed as a portfolio project demonstrating production-oriented data engineering techniques applied to semiconductor manufacturing analytics.

The implementation emphasizes practical ETL design, manufacturing KPI modeling, automated reporting, and equipment performance analytics using Python.
````
