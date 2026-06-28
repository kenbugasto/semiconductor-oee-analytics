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

````md
## 🐍 Production Python ETL Design

The OEE pipeline uses Python as the main ETL and analytics layer for integrating handler event logs and production test records.

The script is designed around defensive data engineering principles because manufacturing data can contain missing fields, inconsistent timestamps, duplicate records, malformed files, and unmatched production lots.

Key Python ETL responsibilities include:

* CSV handler log ingestion
* TXT production file parsing
* Timestamp normalization
* Numeric field cleaning
* Event categorization
* Lot matching between independent data sources
* Hourly production aggregation
* OEE KPI calculation
* Rolling 7-day trend generation
* Automated HTML and CSV report export

---

## Example: 24-Hour OEE Calculation Logic

```python
def calc_oee_metrics(output_pivot, efficiency_pct):
    availability_pct = (
        float(efficiency_pct["UP_TIME"].mean())
        if "UP_TIME" in efficiency_pct.columns
        else 0.0
    )

    total_units = float(output_pivot["TOTAL"].sum())
    pass_units = float(output_pivot["PASS"].sum())

    quality_pct = (
        pass_units / total_units * 100
        if total_units > 0
        else 0.0
    )

    if "TARGET_UPH_ACTIVE_SITES" in output_pivot.columns:
        actual_units = output_pivot["TOTAL"].sum()
        target_units = output_pivot["TARGET_UPH_ACTIVE_SITES"].sum()

        performance_pct = (
            actual_units / target_units * 100
            if target_units > 0
            else 0.0
        )
    else:
        performance_pct = 0.0

    performance_pct = min(performance_pct, 100.0)

    oee_pct = (
        availability_pct / 100
        * performance_pct / 100
        * quality_pct / 100
        * 100
    )

    return {
        "OEE": oee_pct,
        "Utilization": availability_pct,
        "Output Attainment": performance_pct,
        "Yield": quality_pct,
    }
```

### Why This Matters

This calculation converts hourly production and equipment event data into manufacturing KPIs used by the 24-hour OEE report.

The function uses defensive checks to avoid invalid calculations when expected columns are missing or when production volume is zero. This prevents divide-by-zero errors and keeps the report stable even when a handler has incomplete data.

### Engineering Highlights

* Uses pandas aggregation outputs as analytical inputs.
* Handles missing KPI columns defensively.
* Prevents divide-by-zero issues.
* Caps output attainment at 100%.
* Produces business-ready OEE, utilization, output attainment, and yield metrics.

---

## Example: Rolling 7-Day OEE Logic

```python
def build_daily_metrics(p_prod, h_events, all_days):
    rows = []
    event_pivot_days = []

    for report_day in all_days:
        day_start = pd.Timestamp(report_day).normalize()
        day_end = day_start + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

        day_hours = pd.date_range(
            day_start,
            day_start + pd.Timedelta(hours=23),
            freq="h"
        )

        p_day = p_prod[
            (p_prod["test_datetime"] >= day_start) &
            (p_prod["test_datetime"] <= day_end)
        ].copy()

        h_day = h_events[
            (h_events["event_time"] >= day_start) &
            (h_events["event_time"] <= day_end)
        ].copy()

        output_hourly = (
            p_day
            .dropna(subset=["test_hour"])
            .groupby(["test_hour", "pf_status"])
            .agg(units=("serial_no", "count"))
            .reset_index()
        )

        output_pivot = (
            output_hourly
            .pivot_table(
                index="test_hour",
                columns="pf_status",
                values="units",
                aggfunc="sum",
                fill_value=0
            )
            .reindex(day_hours, fill_value=0)
        )

        for col in ["PASS", "FAIL"]:
            if col not in output_pivot.columns:
                output_pivot[col] = 0

        output_pivot["TOTAL"] = output_pivot["PASS"] + output_pivot["FAIL"]

        event_hourly = (
            h_day
            .dropna(subset=["event_hour"])
            .groupby(["event_hour", "event_category"])
            .agg(duration_sec=("duration_sec", "sum"))
            .reset_index()
        )

        event_pivot_sec = (
            event_hourly
            .pivot_table(
                index="event_hour",
                columns="event_category",
                values="duration_sec",
                aggfunc="sum",
                fill_value=0
            )
            .reindex(day_hours, fill_value=0)
        )

        raw_total_event_sec = event_pivot_sec.sum(axis=1)

        scale_factor = pd.Series(
            np.where(
                raw_total_event_sec > 3600,
                3600 / raw_total_event_sec,
                1
            ),
            index=event_pivot_sec.index
        )

        event_pivot_sec_scaled = event_pivot_sec.mul(scale_factor, axis=0)

        total_event_sec = event_pivot_sec_scaled.sum(axis=1).clip(upper=3600)
        uptime_sec = (3600 - total_event_sec).clip(lower=0)

        has_output = output_pivot["TOTAL"] > 0

        utilization_pct = (
            uptime_sec / 3600 * 100
        ).where(has_output, 0).mean()

        total_units = output_pivot["TOTAL"].sum()
        pass_units = output_pivot["PASS"].sum()

        yield_pct = (
            pass_units / total_units * 100
            if total_units > 0
            else 0
        )

        target_units = TARGET_UPH * len(day_hours)

        output_attainment_pct = (
            total_units / target_units * 100
            if target_units > 0
            else 0
        )

        output_attainment_pct = min(output_attainment_pct, 100)

        oee_pct = (
            utilization_pct / 100
            * output_attainment_pct / 100
            * yield_pct / 100
            * 100
        )

        rows.append({
            "report_day": report_day,
            "OEE": oee_pct,
            "Utilization": utilization_pct,
            "Output Attainment": output_attainment_pct,
            "Yield": yield_pct,
        })

        event_pivot_sec_scaled["report_day"] = report_day
        event_pivot_days.append(event_pivot_sec_scaled)

    metrics_daily = pd.DataFrame(rows).set_index("report_day")

    event_pivot_sec_scaled_daily = (
        pd.concat(event_pivot_days)
        .groupby("report_day")
        .sum()
        .reindex(all_days, fill_value=0)
    )

    return metrics_daily, event_pivot_sec_scaled_daily
```

### Why This Matters

The rolling 7-day report reuses the same 24-hour logic for each production day. This ensures that the latest day in the rolling report matches the standalone 24-hour handler report.

The logic evaluates each day at hourly grain before rolling it into daily KPI values. This avoids mismatches caused by calculating OEE directly at daily grain.

### Defensive ETL Pattern

* Reindexes all 24 hourly buckets to prevent missing-hour gaps.
* Adds missing `PASS` and `FAIL` columns when no units exist for a status.
* Clips downtime at the maximum available hour to avoid impossible downtime percentages.
* Uses `np.where()` to safely scale excessive downtime values.
* Prevents divide-by-zero errors when output or target quantity is zero.
* Preserves daily downtime summaries for rolling loss analysis.

---

## ETL and Analytics Grain

The project separates 24-hour and rolling 7-day processing grains to avoid incorrect KPI calculations.

### 24-Hour Report Grain

```text
Handler
+ Report Day
+ Hour
```

Used for:

* Hourly production output
* Hourly downtime
* 24-hour OEE
* Per-handler daily report

### Rolling 7-Day Report Grain

```text
Handler
+ Production Day
+ Hour
```

Used for:

* Daily OEE trend
* Daily utilization trend
* Daily output attainment trend
* Daily yield trend
* Rolling downtime analysis

This design ensures that each rolling daily value is calculated from the same hourly logic used in the 24-hour report.

````


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
