# Data Engineering Challenge
## Wearable Health Data Pipeline

A Python implementation of a **Medallion Architecture (Bronze → Silver → Gold)** for processing wearable health data into analysis-ready Parquet tables.

The pipeline processes data from **50 participants** over a 28-day window (2026-01-08 → 2026-02-04).

---

## Project structure

```text
data_engineering_project_loka/
├── data/
│   ├── health_summaries/
│   ├── participants/
│   └── wearable_events/
│
├── src/
│   ├── bronze_step.py
│   ├── silver_step.py
│   └── gold_step.py
│
├── output/
│   ├── bronze/
│   ├── silver/
│   └── gold/
│
├── data_dictionary.md
├── requirements.txt
└── README.md
```

---

## Data

The raw data is not included in this repository. It can be downloaded from the public Amazon S3 bucket provided in the challenge. Before running the pipeline, make sure the AWS Command Line Interface (AWS CLI) is installed on your computer.
Follow the official AWS installation guide for your operating system: [AWS CLI Installation Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

Use the provided S3 location to download the project data to your local machine.

```bash
aws s3 cp s3://de-tech-assessment-396587179375-us-east-1-an/data/ . --recursive --no-sign-request

```

After downloading the data, create a folder named data in the root of the project. The downloaded source tables should be placed inside the data/ folder, preserving their original folder structure. The data/ directory contains the raw input data used to build the Bronze layer.

## Architecture

The pipeline follows a three-layer Medallion Architecture.

### Bronze — Faithful landing layer

A faithful copy of the raw source data.

- Original values are preserved
- Nested `sleep.json` files are flattened
- Adds `_source_file` and `_ingested_at` audit columns

### Silver — Data quality and validation layer

Implemented data quality corrections include:

- Duplicate detection and removal across all tables
- Participant ID validation
- Chronotype validation (`silver_participants`)
- Recovery of missing `firmware_version` values from `device_label` (`silver_device_metadata`)
- Validation of wellness survey score ranges (`silver_wellness_survey`)
- Detection of sleep sessions longer than 12 hours and recomputation of `sleep_end` from sleep stage durations (`silver_sleep_sessions`)
- Validation of sleep stage categories (`silver_sleep_stages`)
- Recalculation of `duration_min` from `start_time` and `end_time`, with correction flags (`silver_sleep_stages`)
- Step unit correction (steps/hour → steps/minute) (`silver_steps_events`)
- Detection of multi-hour data gaps (`silver_steps_events`)
- Identification of physically impossible step values (`silver_steps_events`)
- First-day timestamp correction (`silver_steps_events`)
- UTC timestamp normalization to local naive time (`silver_heart_rate_events`)
- Detection of out-of-range heart rate values (40–200 bpm) (`silver_heart_rate_events`)
- Detection of prolonged heart-rate flatlines (`silver_heart_rate_events`)
- Nullification of invalid and flatline heart-rate values

All corrections are recorded using audit and flag columns, and a `silver_data_quality_report.txt` is generated.


### Data quality assumptions

Some corrections required implementation assumptions that were not explicitly defined in the challenge.

| Assumption | Implementation |
|------------|----------------|
| `sleep_end` recalculation | Sum of `duration_min` across all sleep stages, including `awake` |
| Multi-hour gap | Gap greater than 2 hours between consecutive step records |
| Step unit error | Values > 120 interpreted as steps/hour and divided by 60 |
| Heart-rate flatline | 60 or more consecutive identical readings treated as sensor artifacts |

### Gold — Denormalized analytical layer

| Table | Description |
|--------|-------------|
| `gold_daily_activity` | Daily participant activity, sleep, and wellness metrics |
| `gold_participant_profile` | Overall profile of each participant |
| `gold_cohort_comparison` | Morning vs. evening chronotype cohort comparison |

---
## How to run

Install the required packages:

```bash
pip install -r requirements.txt
```

Run the pipeline from the `src` folder:

```bash
cd src

python bronze_step.py
python silver_step.py
python gold_step.py
```

The generated Parquet tables will be written to:

```text
output/
├── bronze/
├── silver/
└── gold/
```

---

## Cohort comparison by chronotype

The following example queries compare the morning and evening chronotype cohorts using the Gold layer.

### Option 1 — Query the pre-aggregated `gold_cohort_comparison` table

```sql
SELECT
    chronotype,
    chronotype_label,
    n_participants,
    avg_daily_steps,
    avg_total_sleep_min,
    avg_sleep_efficiency_pct,
    avg_deep_sleep_pct,
    avg_heart_rate_bpm,
    avg_wellness_composite
FROM gold_cohort_comparison
ORDER BY chronotype;
```

### Option 2 — Aggregate results from `gold_participant_profile`

```sql
SELECT
    chronotype,
    chronotype_label,
    COUNT(participant_id) AS n_participants,
    ROUND(AVG(avg_daily_steps), 2) AS avg_daily_steps,
    ROUND(AVG(avg_total_sleep_min), 2) AS avg_total_sleep_min,
    ROUND(AVG(avg_sleep_efficiency_pct), 2) AS avg_sleep_efficiency_pct,
    ROUND(AVG(avg_deep_sleep_pct), 2) AS avg_deep_sleep_pct,
    ROUND(AVG(avg_heart_rate_bpm), 2) AS avg_heart_rate_bpm,
    ROUND(AVG(avg_wellness_composite), 2) AS avg_wellness_composite
FROM gold_participant_profile
GROUP BY chronotype, chronotype_label
ORDER BY chronotype;
```


## AI usage disclosure

ChatGPT and GitHub Copilot were used as **AI-assisted development tools** for debugging, discussing implementation approaches, and reviewing code structure.

The pipeline design, data-quality logic, assumptions, and final implementation were independently developed, validated, and tested by me. All transformations and corrections were manually reviewed before inclusion.